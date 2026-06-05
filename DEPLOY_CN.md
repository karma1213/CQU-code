# 重庆大学通知公告聚合页部署说明

## 目标

部署后访问：

```text
http://服务器公网IP:8765/
```

页面内“刷新”按钮会调用服务端 `/refresh`，重新运行 `cqu_crawler.py` 并更新页面。

## 服务器要求

- 国内云服务器一台，例如阿里云、腾讯云、华为云轻量服务器。
- 系统建议 Ubuntu 22.04 / Debian 12 / CentOS Stream。
- 已放行安全组 TCP `8765` 端口。
- 已安装 Python 3.9+。

## 上传和运行

将 `cqu_notice_deploy.zip` 上传到服务器后执行：

```bash
sudo mkdir -p /opt/cqu-notice
sudo unzip -o cqu_notice_deploy.zip -d /opt/cqu-notice
cd /opt/cqu-notice
python3 -m pip install -r requirements.txt
HOST=0.0.0.0 PORT=8765 python3 notice_server.py
```

然后访问：

```text
http://服务器公网IP:8765/
```

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
