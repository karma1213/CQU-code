# CQU Notice Hub

重庆大学通知公告聚合工具。项目会抓取多个重庆大学官方站点的通知公告，生成本地 HTML 页面，并提供一个轻量本地服务，让页面内的“刷新”按钮可以重新抓取数据。

## 功能

- 聚合重庆大学、土木工程学院、学工部、研究生院等通知来源。
- 生成静态页面 `index.html`，支持搜索、来源筛选、收藏、已读/未读、新通知标记。
- 收藏、已读、新通知状态保存在浏览器 `localStorage`，不需要后端数据库。
- 本地服务 `notice_server.py` 提供 `/refresh` 接口，页面按钮可触发重新抓取。
- Windows 桌面入口 `open_notice_site.vbs` 会启动本地服务并打开 `http://127.0.0.1:8765/`。

## 目录说明

```text
cqu_crawler.py          # 重庆大学通知公告爬虫与页面生成器
notice_server.py        # 本地通知页面服务，支持 /refresh
index.html              # 生成后的通知聚合页面
open_notice_site.vbs    # Windows 启动入口
refresh_and_open.bat    # 旧版刷新并打开脚本
requirements.txt        # Python 依赖
DEPLOY_CN.md            # 服务器部署说明
tests/                  # 测试用例
```

项目中还包含 `news_*` 文件，用于另一个新闻聚合页面。

## 本地运行

安装依赖：

```bash
python -m pip install -r requirements.txt
```

生成通知页面：

```bash
python cqu_crawler.py
```

启动本地服务：

```bash
python notice_server.py
```

访问：

```text
http://127.0.0.1:8765/
```

在本地服务打开的页面中点击“刷新”，会调用 `/refresh`，重新运行爬虫并刷新页面。不要直接双击 `index.html` 使用刷新功能；浏览器安全限制会阻止静态文件执行本地 Python。

## Windows 桌面入口

运行或创建快捷方式指向：

```text
D:\Program Files\cherry\DS Agent\open_notice_site.vbs
```

该脚本会后台启动 `notice_server.py`，然后打开：

```text
http://127.0.0.1:8765/
```

## 测试

编译检查：

```bash
python -m py_compile *.py
```

运行测试：

```bash
python -m unittest discover -s tests -v
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
- `tools/`、日志、缓存和 zip 产物已通过 `.gitignore` 排除，不应提交到仓库。
