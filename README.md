# CQU Notice Hub

重庆大学校务索引台。项目聚合校务通知和国内新闻，生成离线可用的 HTML 页面，并通过两个轻量本地服务提供刷新与页面切换。

## 功能

- 聚合重庆大学、土木工程学院、学工部、研究生院等通知来源。
- 生成 `index.html` 与 `news.html`，支持中文、拼音、首字母、多关键词搜索，以及来源、分类和状态组合筛选。
- 收藏、已读、新通知状态保存在浏览器 `localStorage`，不需要后端数据库。
- 本地服务 `notice_server.py` 提供 `/refresh` 接口，页面按钮可触发重新抓取。
- 抓取结果采用原子替换；所有来源都失败时保留上一版页面，不会写入空页面。
- HTTP 服务只暴露生成页面与图标，不会公开仓库源码；`/healthz` 可用于健康检查。
- Windows 任一桌面入口都会启动通知与新闻两项服务，页内切换不会落到未启动端口。

## 搜索

通知页与新闻页共用一套搜索引擎（`search_widget.py` 在生成页面时注入），支持：

- **多关键词 AND**：空格分隔多个词，全部命中才显示，词序无关。如 `奖学金 研究生`。
- **拼音全拼**：`jiangxuejin` 命中「奖学金」；常见多音字按词修正（重庆→`chongqing`、银行→`yinhang`）。
- **拼音首字母**：`jxj` 命中「奖学金」，`yjsy` 命中「研究生院」。
- **来源与日期**：直接输入来源名（或其拼音）、日期前缀（如 `2026-07`）。
- **命中高亮**：标题（新闻页含摘要）中的命中部分高亮显示。
- 快捷键：`/` 聚焦搜索框，`Esc` 清空；无结果时提供「清空搜索与筛选」。

拼音在**生成页面时**预计算（`data-py` 属性），浏览器端零依赖。生成端优先使用
拼音搜索使用内置的 `pinyin_table.py`，覆盖常用字与高频多音词，不需要额外词库依赖。

## 目录说明

```text
cqu_crawler.py          # 通知抓取编排与 CLI
notice_sources.py       # 通知来源配置与解析器
notice_renderer.py      # 通知页面生成器
news_crawler.py         # 国内新闻抓取编排与 CLI
news_renderer.py        # 新闻页面生成器
frontend_shell.py       # 两页共享设计系统、页头、错误/空状态与脚本
notice_server.py        # 本地通知页面服务，支持 /refresh
site_server.py          # 通知页与新闻页共用的受限 HTTP 服务
crawler_utils.py        # 响应解码、安全 URL 与原子文件写入
browser_fetch.py        # HTTP 412 时的受控 Chromium 会话
index.html              # 生成后的通知聚合页面
search_widget.py        # 共享搜索组件（拼音预计算 + 前端搜索引擎）
pinyin_table.py         # 内置拼音字表与高频多音词
open_notice_site.vbs    # Windows 启动入口
diagnose_sources.py     # 来源、解析器与浏览器回退诊断
diagnose.bat            # Windows 诊断入口
refresh_and_open.bat    # 抓取一次并打开通知页
requirements.txt        # Python 依赖
DEPLOY_CN.md            # 服务器部署说明
tests/                  # 测试用例
```

`news_crawler.py`、`news_server.py` 和 `news.html` 提供独立的国内新闻聚合页，默认端口为 `8766`。

## 本地运行

安装依赖：

```bash
python -m pip install -r requirements.txt
```

生成通知页面：

```bash
python cqu_crawler.py
```

启动两项本地服务（分别在两个终端运行）：

```bash
python notice_server.py
python news_server.py
```

访问：

```text
http://127.0.0.1:8765/
http://127.0.0.1:8766/
```

在本地服务打开的页面中点击“刷新”，会调用 `/refresh`，重新运行爬虫并刷新页面。不要直接双击 `index.html` 使用刷新功能；浏览器安全限制会阻止静态文件执行本地 Python。

服务接口：

```text
GET  /healthz    健康检查
POST /refresh    重新抓取；并发请求返回 409，连续请求受 30 秒冷却限制
```

服务不会公开 `README.md`、Python 源码、`.git` 等项目文件。抓取全部失败时 `/refresh` 返回错误，磁盘上的上一版页面保持不变。

### 412 WAF 回退

土木工程学院、学工部和研究生院等站点可能对普通 HTTP 客户端返回 `412 Precondition Failed`。
爬虫检测到该状态后会按需启动 Selenium/Chrome 执行站点 JavaScript 挑战，再把渲染后的 HTML 交给原有解析器；
其他 HTTP 状态不会启动浏览器。部署时安装 Chromium 与对应 WebDriver，并按需设置：

```bash
export CQU_BROWSER_BINARY=/usr/bin/chromium
export CQU_WEBDRIVER=/usr/bin/chromedriver
export CQU_BROWSER_USER_DATA_DIR=/var/lib/cqu-notice/chrome-profile
```

`CQU_BROWSER_USER_DATA_DIR` 应是已通过站点挑战的专用 profile，运行爬虫时不要让另一个 Chrome 进程占用它。
没有浏览器时可设置 `CQU_BROWSER_FETCH=0`；此时 `412` 会作为明确的来源错误显示，不会被静默吞掉。

默认调试端口为 `9223`。每次 `BrowserSession` 只保存并终止自己启动的 Chrome PID；不会扫描或强杀其他 Chrome。若外部进程占用 `9223`，刷新会明确失败，可先关闭占用者或通过 `CQU_BROWSER_DEBUG_PORT` 指定项目专用端口。

诊断来源、编码、解析器以及生产 WAF 链路：

```bash
python diagnose_sources.py --browser
```

诊断原始页面和报告写入已忽略的 `diag/` 目录。

## Windows 桌面入口

双击仓库根目录下的：

```text
open_notice_site.vbs      # 通知页 -> http://127.0.0.1:8765/
open_news_site.vbs        # 新闻页 -> http://127.0.0.1:8766/
stop_sites.bat             # 关闭通知与新闻后台服务
```

关闭浏览器窗口只会关闭页面；需要停止后台服务时双击 `stop_sites.bat`。该脚本只终止命令行明确包含 `notice_server.py` 或 `news_server.py` 的服务进程树，不会结束其他 Python 程序。

两个脚本都会后台启动 `notice_server.py` 与 `news_server.py`，再打开各自页面。**所有路径都取自脚本自身所在目录**，
仓库整体挪到任何位置都不用改脚本；Python 解释器优先用项目内的 `.venv`，其次系统 Python。

若只想浏览、搜索而不需要「刷新」按钮，直接双击 `index.html` 即可（静态页无法调用本地 Python）。

其它辅助脚本同样是自定位的：

```text
_env.bat                # 公共环境解析（被下面两个 bat 调用）
refresh_and_open.bat    # 抓取一次并打开页面
run_crawler.bat         # 只抓取，供定时任务调用
setup_schedule.ps1      # 注册每天 08:30 的 Windows 计划任务（需管理员）
```

### 编写 Windows 脚本的约定

Windows 的脚本宿主对文件编码很敏感，仓库通过 `tests/test_repo_hygiene.py` 强制以下规则：

| 类型 | 规则 | 原因 |
| --- | --- | --- |
| `.vbs` | **纯 ASCII**，CRLF | WSH 按系统 ANSI 码页解析，无 BOM 的 UTF-8 中文会直接语法报错 |
| `.bat` | **纯 ASCII**、无 BOM，CRLF | 避免 cmd 当前代码页与脚本字节编码冲突 |
| `.ps1` | 含中文时须带 **UTF-8 BOM**，CRLF | Windows PowerShell 5.1 无 BOM 时按 ANSI 解码 |

同一份测试还会扫描全仓库，禁止出现写死的用户目录、安装目录等机器相关路径。

## 本轮架构更新

新闻抓取层参考了开源校园聚合项目的通用做法，将流程保持为“抓取 → 解析 → 规范化 → 去重 → 均衡截取 → 渲染”：

- [HCMUS-Scraper](https://github.com/linhnph05/HCMUS-Scraper)：多校内站点抓取，并按静态页面与 Selenium 动态页面分流。
- [unimi-news-scraper](https://github.com/liggiorgio/unimi-news-scraper)：抓取学校新闻后统一输出订阅格式。
- [VITB-NEXIS](https://github.com/akkiyolo/VITB-NEXIS)：来源、分类、收藏和推荐功能分层组织。

当前实现不引入新运行时依赖：同一刷新批次复用 `requests.Session`，独立新闻来源默认使用最多 4 个并发工作线程；可通过 `CQU_NEWS_WORKERS` 调整为 1–6。RSS 解析同时兼容 RSS `item` 和 Atom `entry`，页面抓取会过滤明显的导航、资源和非文章链接。

## 测试

编译检查：

```bash
python -m py_compile cqu_crawler.py notice_sources.py notice_renderer.py news_crawler.py news_renderer.py frontend_shell.py crawler_utils.py browser_fetch.py search_widget.py pinyin_table.py site_server.py notice_server.py news_server.py diagnose_sources.py
```

运行测试：

```bash
python -W error::ResourceWarning -m unittest discover -s tests -v
```

## 部署

服务器部署见 [DEPLOY_CN.md](DEPLOY_CN.md)。

最小部署方式是运行：

```bash
HOST=0.0.0.0 PORT=8765 python3 notice_server.py
```

并放行 TCP `8765` 端口。

## 注意

- 本项目只抓取公开网页信息，数据来源为重庆大学各官方网站。
- 页面内容以源站为准，聚合结果仅用于个人查看和提醒。
- `.venv/`、`tools/`、`diag/`、日志、缓存和 zip 产物已通过 `.gitignore` 排除，不应提交到仓库。
