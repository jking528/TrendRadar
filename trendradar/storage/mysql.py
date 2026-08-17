# coding=utf-8
"""
MySQL 同步后端

作为 SQLite 主存储之外的"附加同步器"，将热榜与 RSS 数据同步写入 MySQL。
- 独立开关控制，默认关闭，不影响原有 SQLite 存储逻辑。
- 仅首次入库：按 (url_hash, platform_id) 去重，已存在的条目跳过。
- 表结构见 trendradar/storage/mysql_schema.sql。
"""

import hashlib
from typing import Dict, Optional

from trendradar.storage.base import NewsData, RSSData
from trendradar.utils.url import normalize_url


def _sha256(text: str) -> Optional[str]:
    """计算字符串的 SHA-256 十六进制摘要（64 位），空字符串返回 None"""
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MySQLSyncBackend:
    """
    MySQL 同步后端

    仅负责"写入"热榜与 RSS 数据，不参与读取/报告生成等主存储逻辑。
    用法：
        backend = MySQLSyncBackend(host, port, user, password, database)
        backend.sync_news_data(news_data)
        backend.sync_rss_data(rss_data)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "",
        timezone: str = "Asia/Shanghai",
    ):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.database = database
        self.timezone = timezone

        self._conn = None
        self._cursor = None
        self._pymysql = None
        # source_key -> 自增 id 的内存缓存，避免每次重复查询
        self._platform_cache: Dict[str, int] = {}

    # ========================================
    # 连接管理
    # ========================================

    def _connect(self) -> bool:
        """建立 MySQL 连接，成功返回 True"""
        if self._conn is not None:
            return True

        try:
            import pymysql
            self._pymysql = pymysql
        except ImportError:
            print("[MySQL] 缺少 PyMySQL 依赖，请执行: pip install PyMySQL")
            return False

        try:
            self._conn = self._pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset="utf8mb4",
                autocommit=False,
            )
            self._cursor = self._conn.cursor()
            print(f"[MySQL] 连接成功: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            print(f"[MySQL] 连接失败: {e}")
            self._conn = None
            self._cursor = None
            return False

    def _ensure_tables(self) -> bool:
        """确保表结构存在（读取 mysql_schema.sql 执行）"""
        from pathlib import Path

        schema_path = Path(__file__).parent / "mysql_schema.sql"
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # 逐条执行（去除注释与空行，按分号切分）
            for statement in schema_sql.split(";"):
                clean = statement.strip()
                # 跳过纯注释块
                clean = "\n".join(
                    line for line in clean.splitlines()
                    if not line.strip().startswith("--")
                ).strip()
                if clean:
                    self._cursor.execute(clean)
            self._conn.commit()
            return True
        except Exception as e:
            print(f"[MySQL] 初始化表结构失败: {e}")
            return False

    def _ensure_platform(self, source_key: str, name: str, feed_url: str = "") -> Optional[int]:
        """
        获取（或创建）来源在 news_platforms 表中的自增 id。

        Args:
            source_key: 业务标识（热榜平台 id / RSS 源 id）
            name: 显示名称
            feed_url: RSS 订阅地址（热榜为空）

        Returns:
            news_platforms.id，失败返回 None
        """
        if not source_key:
            return None

        if source_key in self._platform_cache:
            return self._platform_cache[source_key]

        try:
            # 查询已存在的来源
            self._cursor.execute(
                "SELECT id FROM news_platforms WHERE source_key = %s",
                (source_key,),
            )
            row = self._cursor.fetchone()
            if row:
                pid = int(row[0])
                # 名称可能变化，更新一次；feed_url 仅在入参非空时回填，避免覆盖已有值
                if feed_url:
                    self._cursor.execute(
                        "UPDATE news_platforms SET name = %s, feed_url = %s WHERE id = %s",
                        (name, feed_url, pid),
                    )
                else:
                    self._cursor.execute(
                        "UPDATE news_platforms SET name = %s WHERE id = %s",
                        (name, pid),
                    )
            else:
                self._cursor.execute(
                    "INSERT INTO news_platforms (source_key, name, feed_url, is_active) "
                    "VALUES (%s, %s, %s, 1)",
                    (source_key, name, feed_url),
                )
                pid = int(self._cursor.lastrowid)

            self._platform_cache[source_key] = pid
            return pid
        except Exception as e:
            print(f"[MySQL] 处理来源 {source_key} 失败: {e}")
            return None

    # ========================================
    # 热榜数据同步
    # ========================================

    def sync_news_data(self, data: NewsData) -> bool:
        """
        同步热榜数据到 MySQL（仅首次入库）

        写入内容：
        - news_feeds：热榜条目（按 url_hash + platform_id 去重，仅新增）
        - news_crawl_records：本次抓取记录（crawl_time 唯一）
        - news_crawl_source_status：每个来源的 success/failed 状态

        Args:
            data: 热榜数据

        Returns:
            是否成功
        """
        if not self._connect():
            return False
        if not self._ensure_tables():
            return False

        new_count = 0
        try:
            for source_id, news_list in data.items.items():
                source_name = data.id_to_name.get(source_id, source_id)
                platform_id = self._ensure_platform(source_id, source_name)
                if platform_id is None:
                    continue

                for item in news_list:
                    try:
                        # 与 SQLite 一致的 URL 标准化
                        normalized_url = normalize_url(item.url, source_id) if item.url else ""
                        url_hash = _sha256(normalized_url)

                        # 若 url 为空，跳过（无法去重，且表以 url_hash 去重）
                        if not url_hash:
                            continue

                        # 去重检查：url_hash + platform_id
                        self._cursor.execute(
                            "SELECT id FROM news_feeds WHERE url_hash = %s AND platform_id = %s",
                            (url_hash, platform_id),
                        )
                        if self._cursor.fetchone():
                            continue  # 已存在，跳过

                        self._cursor.execute(
                            """
                            INSERT INTO news_feeds
                            (platform_id, title, url, mobile_url, cover_url, author,
                             published_at, summary, content, `rank`,
                             url_hash, first_crawl_time, last_crawl_time, crawl_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                            """,
                            (
                                platform_id,
                                item.title,
                                normalized_url,
                                item.mobile_url or "",
                                "",
                                "",
                                None,
                                "",
                                "",
                                item.rank,
                                url_hash,
                                self._full_crawl_time(data.date, data.crawl_time),
                                self._full_crawl_time(data.date, data.crawl_time),
                            ),
                        )
                        new_count += 1
                    except Exception as e:
                        print(f"[MySQL] 保存热榜条目失败 [{item.title[:30]}...]: {e}")

            # 写入抓取记录 + 来源状态
            self._save_crawl_records(data, data.items.keys(), new_count)

            self._conn.commit()
            print(f"[MySQL] 热榜同步完成：新增 {new_count} 条")
            return True
        except Exception as e:
            print(f"[MySQL] 热榜同步失败: {e}")
            return False

    # ========================================
    # RSS 数据同步
    # ========================================

    def sync_rss_data(self, data: RSSData) -> bool:
        """
        同步 RSS 数据到 MySQL（仅首次入库）

        写入内容：
        - news_feeds：RSS 条目（按 url_hash + platform_id 去重，仅新增）
        - news_crawl_records：本次抓取记录（crawl_time 唯一）
        - news_crawl_source_status：每个来源的 success/failed 状态

        Args:
            data: RSS 数据

        Returns:
            是否成功
        """
        if not self._connect():
            return False
        if not self._ensure_tables():
            return False

        new_count = 0
        # 按平台统计本次同步情况（用于打印明细日志）
        feed_stats: Dict[str, Dict[str, int]] = {}
        try:
            for feed_id, rss_list in data.items.items():
                feed_name = data.id_to_name.get(feed_id, feed_id)
                # RSS 源的订阅地址从 id_to_url 映射中获取
                feed_url = data.id_to_url.get(feed_id, "")
                platform_id = self._ensure_platform(feed_id, feed_name, feed_url)
                if platform_id is None:
                    continue

                if feed_id not in feed_stats:
                    feed_stats[feed_id] = {"total": 0, "new": 0, "duplicate": 0, "skipped": 0}

                for item in rss_list:
                    feed_stats[feed_id]["total"] += 1
                    try:
                        normalized_url = item.url or ""
                        url_hash = _sha256(normalized_url)

                        # url 为空时跳过（表以 url_hash 去重）
                        if not url_hash:
                            feed_stats[feed_id]["skipped"] += 1
                            continue

                        self._cursor.execute(
                            "SELECT id FROM news_feeds WHERE url_hash = %s AND platform_id = %s",
                            (url_hash, platform_id),
                        )
                        if self._cursor.fetchone():
                            feed_stats[feed_id]["duplicate"] += 1
                            continue

                        # published_at 转 datetime（可为空）
                        published_at = self._to_datetime(item.published_at)

                        self._cursor.execute(
                            """
                            INSERT INTO news_feeds
                            (platform_id, title, url, mobile_url, cover_url, author,
                             published_at, summary, content, `rank`,
                             url_hash, first_crawl_time, last_crawl_time, crawl_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, 1)
                            """,
                            (
                                platform_id,
                                item.title,
                                normalized_url,
                                "",
                                "",
                                item.author or "",
                                published_at,
                                item.summary or "",
                                "",
                                url_hash,
                                self._full_crawl_time(data.date, data.crawl_time),
                                self._full_crawl_time(data.date, data.crawl_time),
                            ),
                        )
                        new_count += 1
                        feed_stats[feed_id]["new"] += 1
                    except Exception as e:
                        print(f"[MySQL] 保存 RSS 条目失败 [{item.title[:30]}...]: {e}")

            # 打印按平台统计的同步明细日志
            self._print_rss_feed_stats(feed_stats, data.id_to_name)

            # 写入抓取记录 + 来源状态
            self._save_crawl_records(data, data.items.keys(), new_count)

            self._conn.commit()
            print(f"[MySQL] RSS 同步完成：新增 {new_count} 条")
            return True
        except Exception as e:
            print(f"[MySQL] RSS 同步失败: {e}")
            return False

    # ========================================
    # 抓取记录 + 来源状态
    # ========================================

    def _print_rss_feed_stats(self, feed_stats: Dict[str, Dict[str, int]], id_to_name: Dict[str, str]) -> None:
        """
        打印按平台统计的本次 MySQL 同步明细日志

        每个平台输出一行：总数 / 新增 / 重复 / 跳过
        - 总数：本次同步的条目数（去重前）
        - 新增：首次写入 MySQL 的条目数
        - 重复：url_hash 已存在（跨天累积去重命中）、被跳过的条目数
        - 跳过：url 为空、无法去重入库的条目数

        Args:
            feed_stats: {feed_id: {total, new, duplicate, skipped}}
            id_to_name: feed_id 到显示名称的映射
        """
        if not feed_stats:
            return

        total_all = sum(s["total"] for s in feed_stats.values())
        new_all = sum(s["new"] for s in feed_stats.values())
        dup_all = sum(s["duplicate"] for s in feed_stats.values())
        skip_all = sum(s["skipped"] for s in feed_stats.values())

        print("[MySQL] RSS 同步明细（按平台）：")
        for feed_id, s in feed_stats.items():
            name = id_to_name.get(feed_id, feed_id)
            skip_str = f"，跳过 {s['skipped']} 条" if s["skipped"] else ""
            print(f"  - {name}: 共计 {s['total']} 条，新增 {s['new']} 条，重复 {s['duplicate']} 条{skip_str}")

        summary_parts = [f"合计 {total_all} 条", f"新增 {new_all} 条", f"重复 {dup_all} 条"]
        if skip_all:
            summary_parts.append(f"跳过 {skip_all} 条")
        print(f"[MySQL] RSS 同步明细汇总：{'，'.join(summary_parts)}")

    def _save_crawl_records(self, data, success_ids, total_items: int) -> None:
        """
        写入抓取记录与来源状态

        与 SQLite 侧语义一致：
        - news_crawl_records：以 crawl_time 唯一，记录本次抓取条目数
        - news_crawl_source_status：成功来源写 success，失败来源（failed_ids）写 failed

        Args:
            data: NewsData 或 RSSData（需含 date/crawl_time/failed_ids/id_to_name）
            success_ids: 成功来源的 id 可迭代对象（items.keys()）
            total_items: 本次新增条目数
        """
        crawl_time_full = self._full_crawl_time(data.date, data.crawl_time)

        # 1. 写入/更新抓取记录（crawl_time 唯一）
        self._cursor.execute(
            """
            INSERT INTO news_crawl_records (crawl_time, total_items)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE total_items = VALUES(total_items)
            """,
            (crawl_time_full, total_items),
        )
        crawl_record_id = self._cursor.lastrowid
        if not crawl_record_id:
            # 更新场景下 lastrowid 为 0，需重新查询
            self._cursor.execute(
                "SELECT id FROM news_crawl_records WHERE crawl_time = %s",
                (crawl_time_full,),
            )
            row = self._cursor.fetchone()
            crawl_record_id = row[0] if row else None

        if crawl_record_id is None:
            print("[MySQL] 无法获取抓取记录 id，跳过来源状态写入")
            return

        # RSS 数据才有订阅地址映射，热榜（NewsData）无此字段
        id_to_url = getattr(data, "id_to_url", {})

        # 2. 写入成功来源状态
        success_set = set(success_ids)
        for source_id in success_set:
            platform_id = self._ensure_platform(
                source_id,
                data.id_to_name.get(source_id, source_id),
                id_to_url.get(source_id, ""),
            )
            if platform_id is None:
                continue
            self._upsert_source_status(crawl_record_id, platform_id, "success", "")

        # 3. 写入失败来源状态
        for failed_id in data.failed_ids:
            platform_id = self._ensure_platform(
                failed_id,
                data.id_to_name.get(failed_id, failed_id),
                id_to_url.get(failed_id, ""),
            )
            if platform_id is None:
                continue
            self._upsert_source_status(crawl_record_id, platform_id, "failed", "抓取失败")

    def _upsert_source_status(self, crawl_record_id, platform_id, status: str, error_message: str) -> None:
        """写入（或更新）单个来源的抓取状态"""
        self._cursor.execute(
            """
            INSERT INTO news_crawl_source_status
            (crawl_record_id, platform_id, status, error_message)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status), error_message = VALUES(error_message)
            """,
            (crawl_record_id, platform_id, status, error_message),
        )

    # ========================================
    # 工具方法
    # ========================================

    @staticmethod
    def _full_crawl_time(date: str, crawl_time: str) -> str:
        """将日期 + 抓取时间（HH:MM）拼接为完整 datetime 字符串"""
        # crawl_time 形如 "09:30" 或 "09:30:00"
        if not crawl_time:
            return f"{date or '1970-01-01'} 00:00:00"
        if " " in crawl_time:
            return crawl_time
        parts = crawl_time.split(":")
        hh = parts[0] if len(parts) > 0 else "00"
        mm = parts[1] if len(parts) > 1 else "00"
        ss = parts[2] if len(parts) > 2 else "00"
        return f"{date or '1970-01-01'} {hh}:{mm}:{ss}"

    @staticmethod
    def _to_datetime(value: str):
        """将 RSS 发布时间字符串转为 datetime 对象（或 None）"""
        if not value:
            return None
        try:
            from datetime import datetime
            # 尝试多种格式
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value[:19], fmt)
                except ValueError:
                    continue
            # 兜底：直接用字符串交给 MySQL 解析，失败返回 None
            return None
        except Exception:
            return None

    def cleanup(self) -> None:
        """关闭连接"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._cursor = None
            self._platform_cache.clear()
