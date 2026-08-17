-- ============================================================
-- TrendRadar 新闻抓取数据库表（MySQL 版）
-- 用途：将抓取的新闻（热榜 + RSS 订阅）统一存入 MySQL
-- 数据库：MySQL
-- ============================================================
-- 设计说明：
--   1. 热榜与 RSS 统一为一张条目表 news_feeds
--   2. 不记录排名变化 / 标题变更历史（仅保存最新状态）
--   3. 来源表 news_platforms 承载热榜平台与 RSS 订阅源，自增主键 + source_key 业务标识
--   4. 去重：热榜与 RSS 统一按 (url_hash, platform_id)，url 为空时 url_hash 为 NULL
--   5. 不做外键约束，引用完整性由应用层（代码）保证
-- ============================================================


-- ============================================================
-- 1. 来源信息表
-- 粒度：每个抓取来源一条记录（热榜平台 / RSS 订阅源）
-- 核心：id 不变，name 可变
-- ============================================================
CREATE TABLE IF NOT EXISTS `news_platforms` (
    `id`            BIGINT UNSIGNED AUTO_INCREMENT COMMENT '主键',
    `source_key`    VARCHAR(64)   NOT NULL COMMENT '来源唯一标识（如 "weibo"、"hacker-news"）',
    `name`          VARCHAR(255)  NOT NULL COMMENT '来源显示名称',
    `feed_url`      VARCHAR(1024) DEFAULT '' COMMENT 'RSS/Atom 订阅地址（rss 类型才有，热榜为空）',
    `is_active`     TINYINT(1)    DEFAULT 1 COMMENT '是否启用：1=启用, 0=停用',
    `gmt_create`    DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `gmt_modified`  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_source_key` (`source_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='抓取来源信息表（热榜平台 + RSS 订阅源）';


-- ============================================================
-- 2. 新闻条目表
-- 粒度：每条新闻 / 每个 RSS 条目一条记录
-- 去重：统一按 (url_hash, platform_id)
-- ============================================================
CREATE TABLE IF NOT EXISTS `news_feeds` (
    `id`                BIGINT UNSIGNED AUTO_INCREMENT COMMENT '主键',
    `platform_id`       BIGINT UNSIGNED NOT NULL COMMENT '所属来源 ID，关联 news_platforms.id',

    -- 文章信息字段
    `title`             VARCHAR(512)   NOT NULL COMMENT '标题',
    `url`               VARCHAR(1024)  DEFAULT '' COMMENT '文章/原文链接',
    `mobile_url`        VARCHAR(1024)  DEFAULT '' COMMENT '移动端链接（仅热榜有效）',
    `cover_url`         VARCHAR(1024)  DEFAULT '' COMMENT '封面图 URL',
    `author`            VARCHAR(255)   DEFAULT '' COMMENT '作者',
    `published_at`      DATETIME       DEFAULT NULL COMMENT '发布时间（RSS 的 pubDate，热榜为空）',
    `summary`           TEXT           COMMENT '摘要/描述',
    `content`           MEDIUMTEXT     COMMENT '内容详情（完整正文）',

    -- 榜单字段
    `rank`              INT            DEFAULT 0 COMMENT '榜单排名（仅热榜有效，rss 恒为 0）',

    -- 抓取追踪字段
    `url_hash`          CHAR(64)       DEFAULT NULL COMMENT 'url 的 SHA-256 十六进制摘要，用于精确去重（url 为空时为 NULL）',
    `first_crawl_time`  DATETIME       NOT NULL COMMENT '首次抓取时间',
    `last_crawl_time`   DATETIME       NOT NULL COMMENT '最后抓取时间',
    `crawl_count`       INT            DEFAULT 1 COMMENT '累计抓取次数',

    `gmt_create`        DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `gmt_modified`      DATETIME       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',

    PRIMARY KEY (`id`),
    INDEX `idx_platform_id`   (`platform_id`),
    INDEX `idx_last_crawl`    (`last_crawl_time`),
    INDEX `idx_published`     (`published_at`),
    INDEX `idx_title`         (`title`(255)),
    UNIQUE KEY `uk_url_platform` (`url_hash`, `platform_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='新闻条目表（热榜 + RSS 统一存储）';


-- ============================================================
-- 3. 抓取记录表
-- 粒度：每次抓取一条记录
-- ============================================================
CREATE TABLE IF NOT EXISTS `news_crawl_records` (
    `id`            BIGINT UNSIGNED AUTO_INCREMENT COMMENT '主键',
    `crawl_time`    DATETIME      NOT NULL COMMENT '抓取时间',
    `total_items`   INT           DEFAULT 0 COMMENT '本次抓取条目总数',
    `gmt_create`    DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_crawl_time` (`crawl_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='抓取记录表';


-- ============================================================
-- 4. 抓取来源状态表
-- 粒度：每次抓取每个来源的成功/失败状态
-- ============================================================
CREATE TABLE IF NOT EXISTS `news_crawl_source_status` (
    `id`                BIGINT UNSIGNED AUTO_INCREMENT COMMENT '主键',
    `crawl_record_id`   BIGINT UNSIGNED NOT NULL COMMENT '关联 news_crawl_records.id',
    `platform_id`       BIGINT UNSIGNED NOT NULL COMMENT '来源 ID，关联 news_platforms.id',
    `status`            ENUM('success','failed') NOT NULL COMMENT '抓取状态：success / failed',
    `error_message`     TEXT            COMMENT '失败时的错误信息',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_record_platform` (`crawl_record_id`, `platform_id`),
    INDEX `idx_platform_id` (`platform_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='抓取来源状态表';
