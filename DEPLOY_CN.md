# 重庆大学通知公告聚合页部署说明

## 目标

部署后访问：

```text
http://服务器公网IP:8765/
```

页面内“刷新”按钮会调用服务端 `/refresh`，重新运行 `cqu_crawler.py` 并更新页面。
服务只公开生成页面和图标，仓库中的源码、Git 元数据与部署文件无法通过 HTTP 访问。

## 服务器要求

- 国内云服务器一台，例如阿里云、腾讯云、华为云轻量服务器。
- 系统建议 Ubuntu 22.04 / Debian 12 / CentOS Stream。
- 已放行安全组 TCP `8765` 端口；如同时公开新闻页，再放行 `8766`。
- 已安装 Python 3.9+。

## 上传和运行

推荐直接克隆仓库（`zip` 产物已被 `.gitignore` 排除，不再随仓库分发）：

```bash
sudo git clone https://github.com/karma1213/CQU-code.git /opt/cqu-notice
cd /opt/cqu-notice
python3 -m pip install -r requirements.txt
HOST=0.0.0.0 PORT=8765 python3 notice_server.py
```

新闻页使用独立进程和端口：

```bash
HOST=0.0.0.0 NEWS_PORT=8766 python3 news_server.py
```

通知页也可用仓库自带的一键脚本（会装依赖、抓一次、再启动通知服务）：

```bash
cd /opt/cqu-notice
HOST=0.0.0.0 PORT=8765 ./start_server.sh
```

`start_server.sh`、`notice_server.py`、`news_server.py` 都以自身所在目录为工作目录，
放在哪个路径都能跑；下面的 systemd 单元用 `/opt/cqu-notice` 只是约定，改路径时同步修改
`WorkingDirectory` 与 `ExecStart` 即可。

然后访问：

```text
http://服务器公网IP:8765/
```

健康检查：

```bash
curl -fsS http://127.0.0.1:8765/healthz
```

`POST /refresh` 同一时刻只执行一个抓取任务，并有 30 秒冷却时间。所有来源都失败时接口返回错误并保留上一版页面。

## 后台常驻

```bash
sudo cp /opt/cqu-notice/cqu-notice.service /etc/systemd/system/cqu-notice.service
sudo systemctl daemon-reload
sudo systemctl enable --now cqu-notice
sudo systemctl status cqu-notice
```

## 常见问题

- 如果服务器能运行但外网打不开，检查云厂商安全组和系统防火墙是否放行 `8765`。
- 如果要使用域名，国内大陆服务器通常需要域名完成 ICP 备案后才能长期稳定访问。
- 如果不需要页面内刷新功能，可以只上传 `index.html` 到静态托管；但那样不能重新抓取数据。
- `/refresh` 会产生对上游站点的网络请求，请不要在反向代理层取消服务自带的并发与频率限制。

## HTTP 412 与浏览器回退

部分校内站点会对无浏览器会话的请求返回 `412 Precondition Failed`，并要求执行 JavaScript 挑战。
爬虫只在收到 `412` 时启动 Selenium/Chromium，正常来源仍使用轻量的 `requests`，不会让所有来源依赖浏览器。

Linux 服务器需要额外安装 Chromium 和对应驱动，例如：

```bash
sudo apt-get update
sudo apt-get install -y chromium chromium-driver
export CQU_BROWSER_BINARY=/usr/bin/chromium
export CQU_WEBDRIVER=/usr/bin/chromedriver
```

如果服务器上的浏览器已经通过过站点挑战，可指定一个专用的 Chrome profile：

```bash
export CQU_BROWSER_USER_DATA_DIR=/var/lib/cqu-notice/chrome-profile
```

不要在爬虫运行时同时打开这个 profile。Windows 可设置同名环境变量，路径使用绝对路径；
也可用 `CQU_BROWSER_FETCH=0` 显式关闭浏览器回退。浏览器启动失败或挑战仍未通过时，程序会保留上一版页面并在错误区显示原因。

默认调试端口是 `9223`。程序只终止当前会话保存的 Chrome PID；若该端口已被外部 Chrome 或其他程序占用，会拒绝启动并保留旧页面。可为本项目设置独立端口：

```bash
export CQU_BROWSER_DEBUG_PORT=9223
```

诊断完整 HTTP、解析器和浏览器回退链路：

```bash
python3 diagnose_sources.py --browser
```
