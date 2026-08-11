# TrendRadar 项目源码结构分析文档

> 分析日期：2026-07-27 | 项目版本：v6.10.0 | MCP 版本：v4.1.0

---

## 一、项目概述

**TrendRadar** 是一个**热点新闻聚合与分析工具**，基于 Python 3.12+ 开发。核心能力包括：

- 从多平台热榜（今日头条、百度、微博、知乎等）定时抓取新闻
- 通过关键词 / 正则表达式进行新闻过滤
- 可选接入 AI 大模型（基于 LiteLLM，支持 100+ 提供商）进行深度分析、翻译和智能筛选
- 通过飞书、钉钉、企业微信、Telegram、邮件等 9 个渠道推送报告
- 生成可视化 HTML 报告
- 提供独立的 MCP Server，供外部 AI 客户端（如 Claude Desktop、Cherry Studio）集成

---

## 二、完整目录树

```
TrendRadar/
├── .codebuddy/                          # AI 助手数据目录
│   ├── memory/                          # 跨会话记忆（MEMORY.md + 每日日志）
│   └── project_analysis.md              # 本文档
├── .github/                             # GitHub Actions CI/CD
│   ├── ISSUE_TEMPLATE/                  # Issue 模板（bug / feature / config）
│   └── workflows/
│       ├── crawler.yml                  # 定时爬虫调度
│       ├── clean-crawler.yml            # 工作流清理
│       ├── docker.yml                   # Docker 镜像构建与推送
│       └── issue-guard.yml              # Issue 自动管理（过期关单）
├── config/                              # 用户配置目录
│   ├── config.yaml                      # 主配置文件（应用 / 爬虫 / 通知 / AI / 存储）
│   ├── config.en.yaml                   # 英文版配置
│   ├── timeline.yaml                    # 时间线调度配置
│   ├── timeline.en.yaml                 # 英文版时间线
│   ├── frequency_words.txt              # 中文关键词过滤规则
│   ├── frequency_words.en.txt           # 英文关键词过滤规则
│   ├── ai_interests.txt                 # AI 兴趣描述（自然语言）
│   ├── ai_analysis_prompt.txt           # AI 分析提示词模板
│   ├── ai_translation_prompt.txt        # AI 翻译提示词模板
│   ├── ai_filter/                       # AI 筛选子配置
│   │   ├── prompt.txt                   # 标签分类提示词
│   │   ├── extract_prompt.txt           # 标签提取提示词
│   │   └── update_tags_prompt.txt       # 标签更新提示词
│   └── custom/                          # 用户自定义配置（关键字 / AI）
│       ├── keyword/.gitkeep
│       └── ai/.gitkeep
├── docker/                              # Docker 部署
│   ├── .env                             # 环境变量模板
│   ├── Dockerfile                       # 主程序镜像
│   ├── Dockerfile.mcp                   # MCP Server 镜像
│   ├── docker-compose.yml               # 编排文件（主程序 + MCP Server）
│   ├── docker-compose-build.yml         # 构建编排
│   ├── entrypoint.sh                    # 容器入口脚本（cron / once 模式）
│   └── manage.py                        # 容器内管理工具
├── docs/                                # Web 可视化配置编辑器
│   ├── index.html                       # 配置编辑器主页
│   └── assets/
│       ├── i18n.js                      # 国际化
│       ├── script.js                    # 编辑器核心逻辑
│       ├── style.css                    # 样式
│       └── weixin.webp                  # 微信图片
├── mcp_server/                          # MCP Server 独立子项目
│   ├── __init__.py                      # 包入口，版本 4.1.0
│   ├── server.py                        # FastMCP 2.0 主程序（~1150 行）
│   ├── tools/                           # MCP 工具集
│   │   ├── __init__.py
│   │   ├── data_query.py                # 数据查询工具
│   │   ├── analytics.py                 # 分析工具（~2600 行，最大模块）
│   │   ├── search_tools.py              # 搜索工具
│   │   ├── config_mgmt.py               # 配置管理工具
│   │   ├── system.py                    # 系统管理工具
│   │   ├── storage_sync.py              # 存储同步工具
│   │   ├── article_reader.py            # 文章阅读工具
│   │   └── notification.py              # 通知工具
│   ├── services/                        # 服务层
│   │   ├── __init__.py
│   │   ├── cache_service.py             # 缓存管理
│   │   ├── data_service.py              # 统一数据访问
│   │   └── parser_service.py            # 数据解析转换
│   └── utils/                           # 工具层
│       ├── __init__.py
│       ├── date_parser.py               # 自然语言日期解析
│       ├── errors.py                    # 统一错误类型
│       └── validators.py                # 参数校验
├── trendradar/                          # 核心主程序模块
│   ├── __init__.py                      # 包入口，导出 AppContext
│   ├── __main__.py                      # 主程序入口（~1716 行），NewsAnalyzer 类
│   ├── context.py                       # 应用上下文 AppContext
│   ├── core/                            # 核心模块
│   │   ├── __init__.py
│   │   ├── loader.py                    # 配置加载器（~607 行）
│   │   ├── config.py                    # 配置工具（多账号解析等）
│   │   ├── frequency.py                 # 关键词匹配引擎（~310 行）
│   │   ├── analyzer.py                  # 统计分析（~780 行）
│   │   ├── data.py                      # 数据读取（~219 行）
│   │   ├── scheduler.py                 # 时间线调度器（~432 行）
│   │   └── cdn.py                       # CDN 回退（版本检查用）
│   ├── crawler/                         # 爬虫模块
│   │   ├── __init__.py
│   │   ├── fetcher.py                   # 热榜数据获取（newsnow API）
│   │   └── rss/                         # RSS 抓取子模块
│   │       ├── __init__.py
│   │       ├── fetcher.py               # RSS 抓取器
│   │       └── parser.py                # RSS 解析器
│   ├── ai/                              # AI 集成模块
│   │   ├── __init__.py
│   │   ├── client.py                    # LiteLLM 统一客户端
│   │   ├── analyzer.py                  # AI 深度分析
│   │   ├── translator.py                # AI 翻译
│   │   ├── filter.py                    # AI 智能筛选（标签分类）
│   │   ├── filter_pipeline.py           # AI 筛选流水线
│   │   ├── formatter.py                 # 分析结果格式化
│   │   └── prompt_loader.py             # 提示词加载器
│   ├── notification/                    # 通知推送模块
│   │   ├── __init__.py
│   │   ├── formatters.py                # 格式转换工具
│   │   ├── batch.py                     # 批次处理工具
│   │   ├── renderer.py                  # 平台内容渲染
│   │   ├── splitter.py                  # 消息拆分（~2100 行）
│   │   ├── senders.py                   # 渠道发送器（~1300 行）
│   │   └── dispatcher.py                # 通知调度器（~920 行）
│   ├── report/                          # 报告生成模块
│   │   ├── __init__.py
│   │   ├── helpers.py                   # 辅助函数
│   │   ├── formatter.py                 # 标题格式化
│   │   ├── html.py                      # HTML 报告渲染（~3400 行，最大文件）
│   │   ├── rss_html.py                  # RSS 报告渲染
│   │   └── generator.py                 # 报告生成入口
│   ├── storage/                         # 数据存储模块
│   │   ├── __init__.py
│   │   ├── base.py                      # 数据模型定义
│   │   ├── local.py                     # 本地 SQLite 后端
│   │   ├── remote.py                    # 远程 S3 兼容后端
│   │   ├── manager.py                   # 存储管理器（统一接口）
│   │   ├── sqlite_mixin.py              # SQLite 公共逻辑（~1800 行）
│   │   ├── schema.sql                   # 热榜数据建表
│   │   ├── rss_schema.sql               # RSS 数据建表
│   │   └── ai_filter_schema.sql         # AI 筛选标签建表
│   ├── utils/                           # 通用工具
│   │   ├── __init__.py
│   │   ├── time.py                      # 时间处理
│   │   └── url.py                       # URL 规范化
│   └── commands/                        # CLI 子命令
│       ├── __init__.py
│       ├── doctor.py                    # 一键诊断
│       ├── test_notification.py         # 通知测试
│       ├── status.py                    # 调度状态
│       └── version.py                   # 版本检查
├── output/                              # 运行时输出（SQLite 数据库等）
├── _image/                              # README 图片资源
├── index.html                           # 新闻报告展示页面（模版）
├── pyproject.toml                       # 项目配置与依赖声明
├── uv.lock                              # uv 依赖锁定文件
├── version                              # 主程序版本号文件
├── version_configs                      # 配置文件版本号文件
├── version_mcp                          # MCP 版本号文件
├── README.md                            # 中文项目说明（156KB）
├── README-EN.md                         # 英文项目说明
├── README-Cherry-Studio.md              # Cherry Studio 集成指南
├── README-MCP-FAQ.md                    # MCP 常见问题（中文）
├── README-MCP-FAQ-EN.md                 # MCP 常见问题（英文）
├── LICENSE                              # 许可证
├── setup-mac.sh                         # Mac 一键安装
├── setup-windows.bat                    # Windows 一键安装（中文）
├── setup-windows-en.bat                 # Windows 一键安装（英文）
├── start-http.bat                       # HTTP 服务启动（Windows）
└── start-http.sh                        # HTTP 服务启动（Linux/Mac）
```

---

## 三、根目录文件说明

### 3.1 入口与版本文件

| 文件 | 职责 |
|---|---|
| `pyproject.toml` | 项目元数据、Python 版本要求（≥3.12）、uv 包管理器配置、全部依赖声明 |
| `uv.lock` | uv 生成的精确依赖版本锁定，确保可复现构建 |
| `version` | 主程序版本号（当前 `6.10.0`） |
| `version_configs` | 配置文件版本号 |
| `version_mcp` | MCP Server 版本号（当前 `4.1.0`） |
| `index.html` | 离线 HTML 新闻报告展示页面，作为 `report/html.py` 生成的报告的渲染模版 |

### 3.2 安装与启动脚本

| 文件 | 职责 |
|---|---|
| `setup-mac.sh` | Mac 环境一键安装（安装 uv、同步依赖、初始化配置） |
| `setup-windows.bat` | Windows 环境一键安装（中文界面） |
| `setup-windows-en.bat` | Windows 环境一键安装（英文界面） |
| `start-http.bat` | 启动 HTTP Web 服务器，用于浏览本地 HTML 报告 |
| `start-http.sh` | Linux/Mac 版 HTTP 服务启动脚本 |

### 3.3 文档

| 文件 | 职责 |
|---|---|
| `README.md` | 完整中文项目文档（156KB），覆盖功能介绍、部署指南、配置说明 |
| `README-EN.md` | 英文版 README |
| `README-Cherry-Studio.md` | 如何在 Cherry Studio 中配置 TrendRadar MCP Server 的详细指南 |
| `README-MCP-FAQ.md` | MCP 功能常见问题解答（中文） |
| `README-MCP-FAQ-EN.md` | MCP 功能常见问题解答（英文） |

---

## 四、`trendradar/` 核心模块详解

### 4.1 入口层

#### `__init__.py` — 包入口
- 导出 `AppContext`（应用上下文）
- 暴露当前版本号 `6.10.0`

#### `__main__.py` — 主程序入口（~1716 行）
- 包含 `NewsAnalyzer` 类，为整个采集-分析-通知流程的核心编排者
- 包含 `main()` 函数，提供 CLI 入口：`python -m trendradar [OPTIONS] [COMMAND]`
- 支持 `--run-now`（立即运行一次）、`--config`（指定配置文件）等参数
- 支持子命令：`doctor`、`test-notification`、`status`、`version`

#### `context.py` — 应用上下文
- 定义 `AppContext` 类，封装所有操作依赖（时间、存储、通知等）
- **消除全局状态**，所有核心操作通过上下文对象协调
- 是依赖注入模式的实现

### 4.2 `core/` — 核心模块

| 文件 | 职责 |
|---|---|
| `loader.py` | **配置加载器**（~607 行）。从 `config.yaml` 加载全部配置，并与环境变量合并。覆盖：应用设置、爬虫参数、通知渠道、AI 模型、存储后端、调度策略、RSS 订阅源、Webhook 等 |
| `config.py` | **配置工具**。多账号解析（`parse_multi_account_config`）、配对配置验证（`validate_paired_configs`）、账号数量限制 |
| `frequency.py` | **关键词匹配引擎**（~310 行）。解析 `frequency_words.txt`，支持：必须词（`+`）、过滤词（`!`）、正则（`/.../`）、别名（`=>`）、组别名（`[...]`）、条数限制（`@`）、全局过滤词 |
| `analyzer.py` | **统计分析**（~780 行）。新闻权重计算（`calculate_news_weight`）、词频统计（`count_word_frequency`）、RSS 词频统计、关键词统计转换为平台统计 |
| `data.py` | **数据读取**。从存储后端读取当天标题（`read_all_today_titles`）、检测新增标题（`detect_latest_new_titles`） |
| `scheduler.py` | **时间线调度器**（~432 行）。基于 `timeline.yaml` 的时间段调度，支持 `periods` + `day_plans` + `week_map` 三级模型，跨日时间段、once 去重、重叠冲突检测 |
| `cdn.py` | **CDN 回退**。版本检查时的多 CDN 源回退（GitHub → jsdelivr），记住可用源索引 |

### 4.3 `crawler/` — 爬虫模块

| 文件 | 职责 |
|---|---|
| `fetcher.py` | **热榜数据获取器**。调用 newsnow API (`https://newsnow.busiyi.world/api/s`) 批量抓取各平台热榜，支持重试、代理、域名安全校验 |
| `rss/fetcher.py` | **RSS 抓取器**。支持 RSS 2.0 / Atom / JSON Feed 格式，新鲜度过滤，超时控制，代理支持 |
| `rss/parser.py` | **RSS 解析器**。解析多种 feed 格式为统一数据结构 |

### 4.4 `ai/` — AI 集成模块

| 文件 | 职责 |
|---|---|
| `client.py` | **AI 客户端**（~122 行）。基于 LiteLLM 的统一接口，`chat()` 方法封装 completion 调用，支持 100+ AI 提供商，严格的配置验证 |
| `analyzer.py` | **AI 分析器**（~650 行）。调用大模型深度分析热点，输出 5 个板块：核心热点、舆论风向、异动信号、RSS 洞察、策略建议 |
| `translator.py` | **AI 翻译器**（~280 行）。批量翻译新闻内容（热榜 / RSS / 独立展示区） |
| `filter.py` | **AI 智能筛选器**（~560 行）。阶段 A 提取结构化标签，阶段 B 对新闻按标签批量分类 |
| `filter_pipeline.py` | **AI 筛选流水线**（~760 行）。编排完整流程：标签提取 → 新闻收集 → 批量分类 → 结果存储 → 报告转换 |
| `formatter.py` | **分析结果格式化**（~370 行）。将 AI 分析结果渲染为 Markdown / 飞书 / 钉钉 / HTML / 纯文本 |
| `prompt_loader.py` | **提示词加载器**。从 config 目录加载 `[system]` / `[user]` 格式的提示词文件 |

### 4.5 `notification/` — 通知模块

| 文件 | 职责 |
|---|---|
| `formatters.py` | **格式转换**。Markdown → 纯文本、Markdown → Slack mrkdwn |
| `batch.py` | **批次处理**。批次头生成、按字节截断 |
| `renderer.py` | **内容渲染**。飞书、钉钉消息内容渲染 |
| `splitter.py` | **消息拆分**（~2100 行，最复杂的通知模块）。将超长消息按各平台字节限制智能拆分 |
| `senders.py` | **渠道发送器**（~1300 行）。实现 9 个渠道：飞书、钉钉、企业微信、Telegram、邮件、ntfy、Bark、Slack、通用 Webhook |
| `dispatcher.py` | **通知调度器**（~920 行）。多账号轮询、翻译集成、HTML 报告生成、统一分发入口 |

### 4.6 `report/` — 报告模块

| 文件 | 职责 |
|---|---|
| `helpers.py` | **辅助函数**。标题清理、HTML 转义、排名格式化 |
| `formatter.py` | **标题格式化**。按平台格式化新闻标题列表 |
| `html.py` | **HTML 报告渲染**（~3400 行，项目最大文件）。生成完整的离线 HTML 新闻报告，包含热榜展示、RSS 内容、AI 分析等 |
| `rss_html.py` | **RSS 报告渲染**。独立的 RSS HTML 报告生成 |
| `generator.py` | **报告生成入口**。`prepare_report_data` 准备数据、`generate_html_report` 生成最终报告 |

### 4.7 `storage/` — 存储模块

| 文件 | 职责 |
|---|---|
| `base.py` | **数据模型定义**。`NewsItem` / `NewsData` / `RSSItem` / `RSSData` 核心数据结构 |
| `local.py` | **本地 SQLite 后端**。本地数据库的读写操作 |
| `remote.py` | **远程 S3 兼容后端**。支持 R2 / OSS / COS / S3 等 S3 兼容存储 |
| `manager.py` | **存储管理器**。自动选择后端（本地/远程）、统一读写接口、数据过期清理 |
| `sqlite_mixin.py` | **SQLite 公共逻辑**（~1800 行）。数据库初始化、建表、CRUD、调度记录、AI 筛选结果存储 |
| `schema.sql` | 热榜数据 SQL 建表脚本 |
| `rss_schema.sql` | RSS 数据 SQL 建表脚本 |
| `ai_filter_schema.sql` | AI 筛选标签数据 SQL 建表脚本 |
| `output/` | 运行时输出目录，存放生成的 SQLite 数据库文件 |

### 4.8 `utils/` — 工具模块

| 文件 | 职责 |
|---|---|
| `time.py` | **时间处理**（~230 行）。时区转换、格式化、ISO 时间友好显示、天数计算 |
| `url.py` | **URL 规范化**。统一 URL 格式，去除追踪参数等 |

### 4.9 `commands/` — CLI 命令

| 文件 | 职责 |
|---|---|
| `doctor.py` | **一键诊断**（~280 行）。检查 Python 环境、配置完整性、依赖版本、网络连通性 |
| `test_notification.py` | **通知测试**（~140 行）。向已配置的通知渠道发送测试消息，验证推送可用性 |
| `status.py` | **调度状态**。显示当前调度状态和各时间段信息 |
| `version.py` | **版本检查**。对比本地版本与远程最新版本，提示更新 |

---

## 五、`mcp_server/` MCP Server 详解

MCP Server 是一个独立子项目，基于 **FastMCP 2.0** 框架实现 **Model Context Protocol** 服务，使外部 AI 客户端可以通过标准 MCP 协议访问 TrendRadar 的数据和能力。

### 5.1 入口

| 文件 | 职责 |
|---|---|
| `__init__.py` | 包入口，版本 `4.1.0` |
| `server.py` | **MCP Server 主程序**（~1150 行）。基于 FastMCP 2.0，注册 8 组工具和 2 个 Resource，支持 stdio 和 HTTP 两种传输模式 |

### 5.2 工具层 (`tools/`)

| 文件 | 职责 |
|---|---|
| `data_query.py` | **数据查询工具**。查询热榜新闻、RSS 条目、今日/历史数据、新增内容 |
| `analytics.py` | **分析工具**（~2600 行，MCP 最大模块）。热榜趋势分析、排名变化追踪、关键词统计、RSS 分析 |
| `search_tools.py` | **搜索工具**（~940 行）。关键词搜索、全文检索、跨平台搜索 |
| `config_mgmt.py` | **配置管理工具**。查看当前配置、平台列表 |
| `system.py` | **系统管理工具**。健康检查、运行状态、调度信息 |
| `storage_sync.py` | **存储同步工具**。远程数据拉取、本地数据同步 |
| `article_reader.py` | **文章阅读工具**。根据 URL 抓取文章全文内容 |
| `notification.py` | **通知工具**（~1400 行）。测试通知、手动推送、渠道状态查询 |

### 5.3 服务层 (`services/`)

| 文件 | 职责 |
|---|---|
| `cache_service.py` | **缓存服务**。数据缓存管理，减少重复计算 |
| `data_service.py` | **数据服务**（~780 行）。统一数据访问层，封装对 trendradar 核心模块的调用 |
| `parser_service.py` | **解析服务**。数据解析和格式转换 |

### 5.4 工具层 (`utils/`)

| 文件 | 职责 |
|---|---|
| `date_parser.py` | **日期解析器**（~490 行）。自然语言日期解析（"今天"、"昨天"、"3天前"等） |
| `errors.py` | **错误处理**。统一错误类型定义和错误响应格式 |
| `validators.py` | **参数验证器**（~540 行）。MCP 工具调用时的输入参数校验 |

---

## 六、`config/` 配置目录详解

| 文件 | 版本 | 职责 |
|---|---|---|
| `config.yaml` | v2.4.0 | **主配置文件**。涵盖：应用设置、调度预设、热榜平台列表、RSS 订阅源、AI 模型配置、通知渠道（9种）、存储后端、显示控制、筛选策略（keyword / ai） |
| `config.en.yaml` | — | 英文版主配置 |
| `timeline.yaml` | v1.2.0 | **时间线调度**。预设模式（always_on / morning_evening / office_hours / night_owl）+ 自定义 periods / day_plans / week_map |
| `timeline.en.yaml` | — | 英文版时间线调度 |
| `frequency_words.txt` | v1.1.0 | **关键词过滤规则**。必须词（`+`）、过滤词（`!`）、正则（`/.../`）、别名（`=>`）、组别名（`[...]`）、条数限制（`@`）、全局过滤词 |
| `frequency_words.en.txt` | — | 英文版关键词规则 |
| `ai_interests.txt` | v1.1.0 | **AI 兴趣描述**。用自然语言描述关注话题，AI 将自动提取标签并分类新闻 |
| `ai_analysis_prompt.txt` | v2.0.0 | **AI 分析提示词**。定义分析师的思维模型（见微知著、交叉验证、反直觉、MECE）和输出格式 |
| `ai_translation_prompt.txt` | v1.2.0 | **AI 翻译提示词**。翻译规则和风格要求 |
| `ai_filter/` | — | AI 筛选子配置目录，含标签提取和分类的提示词 |
| `custom/` | — | 用户自定义配置目录，可放置额外的关键字和 AI 配置文件 |

---

## 七、`docker/` 部署目录详解

| 文件 | 职责 |
|---|---|
| `Dockerfile` | **主程序镜像**。基于 Python 3.12-slim，安装 supercronic 定时调度器，通过 uv 安装依赖 |
| `Dockerfile.mcp` | **MCP Server 镜像**。仅包含 mcp_server + trendradar 模块，通过 HTTP 暴露 3333 端口 |
| `docker-compose.yml` | **编排文件**。同时启动 trendradar（cron 定时 + Web 服务器）和 trendradar-mcp 两个服务 |
| `docker-compose-build.yml` | **构建编排**。用于本地构建 Docker 镜像 |
| `.env` | **环境变量模板**。CRON_SCHEDULE、通知渠道密钥、AI API Key、存储配置等 |
| `entrypoint.sh` | **容器入口脚本**。支持 `once`（单次执行）和 `cron`（定时执行）两种模式，启动 Web 服务器和 supercronic |
| `manage.py` | **容器管理工具**。Web 服务器管理（启停）、手动执行收集、cron 表达式解析、日志查看 |

---

## 八、`.github/workflows/` CI/CD 详解

| 文件 | 职责 |
|---|---|
| `crawler.yml` | **定时爬虫工作流**。通过 GitHub Actions 定时触发新闻采集和分析，是主要的生产运行方式之一 |
| `clean-crawler.yml` | **清理工作流**。清理过期的工作流运行记录和产物 |
| `docker.yml` | **Docker 构建推送**。构建并推送多架构 Docker 镜像到镜像仓库 |
| `issue-guard.yml` | **Issue 自动管理**。自动关闭过期未响应的 Issue，保持仓库整洁 |
| `ISSUE_TEMPLATE/` | Issue 模板目录，提供 bug 报告、功能请求、配置问题的标准化表单 |

---

## 九、架构设计总结

### 9.1 核心数据流

```
定时触发 (GitHub Actions cron / Docker supercronic)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  __main__.py: main() → NewsAnalyzer.run()               │
│                                                         │
│  1. 加载配置     → core/loader.py (config.yaml + env)   │
│  2. 创建上下文   → context.py (AppContext)               │
│  3. 爬取热榜     → crawler/fetcher.py (newsnow API)     │
│  4. 爬取 RSS     → crawler/rss/ (RSS/Atom/JSON Feed)    │
│  5. 调度决策     → core/scheduler.py (timeline.yaml)    │
│  6. 关键词匹配   → core/frequency.py                    │
│  7. AI 处理 [可选] → ai/ (分析/翻译/筛选)                │
│  8. HTML 报告    → report/ (html.py 渲染)               │
│  9. 多渠道推送   → notification/ (9 种渠道)             │
│  10. 数据持久化  → storage/ (SQLite / S3)               │
└─────────────────────────────────────────────────────────┘
```

### 9.2 三种报告模式

| 模式 | 说明 |
|---|---|
| `incremental`（增量） | 只推送本次采集发现的新增新闻 |
| `current`（当前榜单） | 推送当前在榜新闻 + 新增高亮区域 |
| `daily`（全天汇总） | 汇总全天所有匹配新闻，通常在日终推送 |

### 9.3 两种筛选策略

| 策略 | 说明 |
|---|---|
| `keyword`（默认） | 基于 `frequency_words.txt` 的关键词 + 正则表达式匹配 |
| `ai` | 基于 `ai_interests.txt` 的自然语言描述，由 AI 进行智能标签分类和筛选 |

### 9.4 关键设计特点

1. **AppContext 模式**：消除全局状态，所有操作通过上下文对象协调，提升可测试性和模块解耦
2. **存储抽象层**：支持 local（SQLite）和 remote（S3 兼容）双后端，通过 `manager.py` 自动切换
3. **时间线调度**：灵活的 periods + day_plans + week_map 三级调度模型，支持跨日时间段
4. **多账号多渠道**：每个通知渠道支持配置多个账号，自动轮询推送
5. **MCP 协议集成**：独立的 MCP Server 子项目，使外部 AI 客户端（Claude Desktop、Cherry Studio）可以通过标准 MCP 协议直接查询 TrendRadar 数据
6. **AI 深度集成**：分析、翻译、筛选三种 AI 功能共享同一个 LiteLLM 客户端，支持 100+ AI 提供商
7. **消息智能拆分**：`notification/splitter.py` 是项目中最复杂的模块（~2100 行），按各平台字节限制智能拆分超长消息，确保推送成功率
