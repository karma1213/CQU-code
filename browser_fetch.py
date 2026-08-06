#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controlled Chromium fallback for CQU sources protected by a WAF.

The normal crawler remains requests-based. A :class:`BrowserSession` is only
created for URLs that returned HTTP 412. The session owns every process it
starts and releases the Selenium service before terminating its Chrome tree.
"""

from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


class BrowserFetchError(RuntimeError):
    """Raised when the browser fallback cannot return usable HTML."""


_DEFAULT = object()
_SESSION_LOCK = threading.Lock()
_ACTIVE_SESSION = None


def enabled() -> bool:
    """Return whether the HTTP 412 browser fallback is enabled."""
    return os.environ.get("CQU_BROWSER_FETCH", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _find_binary() -> str:
    configured = os.environ.get("CQU_BROWSER_BINARY", "").strip()
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path)
        raise BrowserFetchError(f"CQU_BROWSER_BINARY 不存在: {configured}")

    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES", ""))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", ""))
                / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", ""))
                / "Microsoft/Edge/Application/msedge.exe",
                Path(os.environ.get("PROGRAMFILES", ""))
                / "Microsoft/Edge/Application/msedge.exe",
            ]
        )
    else:
        for command in (
            "google-chrome",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
        ):
            found = shutil.which(command)
            if found:
                candidates.append(Path(found))

    for path in candidates:
        if path and path.is_file():
            return str(path)
    raise BrowserFetchError(
        "未找到 Chrome/Chromium。请安装浏览器，或设置 CQU_BROWSER_BINARY。"
    )


def _debug_port() -> int | None:
    raw = os.environ.get("CQU_BROWSER_DEBUG_PORT", "9223").strip()
    if raw.lower() in {"", "0", "off", "no", "false"}:
        return None
    try:
        port = int(raw)
    except ValueError as exc:
        raise BrowserFetchError(f"CQU_BROWSER_DEBUG_PORT 不是有效端口: {raw}") from exc
    if not 1 <= port <= 65535:
        raise BrowserFetchError(f"CQU_BROWSER_DEBUG_PORT 超出有效范围: {port}")
    return port


def _attach_profile() -> Path | None:
    configured = os.environ.get("CQU_BROWSER_USER_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            return Path(local) / "CQU-notice-hub" / "chrome-profile-v2"
    return None


def _port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _probe_debug_port(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/version", timeout=1
        ) as response:
            return response.status == 200
    except Exception:
        return False


def _launch_chrome(
    port: int, profile: Path, identity_url: str = "about:blank"
) -> subprocess.Popen:
    command = [
        _find_binary(),
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        f"--user-data-dir={profile}",
        identity_url,
    ]
    creationflags = 0
    kwargs = {}
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
            **kwargs,
        )
    except Exception as exc:
        raise BrowserFetchError(f"Chrome 启动失败: {exc}") from exc


def _wait_for_process_exit(process: subprocess.Popen, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if process.poll() is not None:
                return True
        except Exception as exc:
            raise BrowserFetchError(
                f"无法确认受管进程 {getattr(process, 'pid', '?')} 状态: {exc}"
            ) from exc
        time.sleep(0.1)
    try:
        return process.poll() is not None
    except Exception as exc:
        raise BrowserFetchError(
            f"无法确认受管进程 {getattr(process, 'pid', '?')} 状态: {exc}"
        ) from exc


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Terminate only the process tree rooted at the saved process PID."""
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if _wait_for_process_exit(process, 5):
            return
        return_code = getattr(result, "returncode", "unavailable")
        raise BrowserFetchError(
            f"受管进程树 {process.pid} 无法终止，taskkill exit={return_code}"
        )

    try:
        process_group = os.getpgid(process.pid)
    except OSError as exc:
        if _wait_for_process_exit(process, 0.2):
            return
        raise BrowserFetchError(f"无法读取受管进程组 {process.pid}: {exc}") from exc
    try:
        os.killpg(process_group, signal.SIGTERM)
    except OSError:
        pass
    if _wait_for_process_exit(process, 5):
        return
    try:
        os.killpg(process_group, signal.SIGKILL)
    except OSError:
        pass
    if _wait_for_process_exit(process, 5):
        return
    raise BrowserFetchError(f"受管进程组 {process_group} 无法终止")


def _stop_service(service) -> None:
    if service is None:
        return
    stop_error = None
    try:
        service.stop()
    except Exception as exc:
        stop_error = exc

    process = getattr(service, "process", None)
    if process is not None:
        try:
            running = process.poll() is None
        except Exception:
            running = True
        if running:
            termination_error = None
            try:
                _terminate_process_tree(process)
            except BrowserFetchError as exc:
                termination_error = exc
            try:
                running = process.poll() is None
            except Exception:
                running = True
            if running and termination_error is not None:
                raise BrowserFetchError(
                    f"ChromeDriver service 无法停止: {termination_error}"
                ) from termination_error
        if not running:
            return

    if stop_error is not None:
        raise BrowserFetchError(
            f"ChromeDriver service 无法停止: {stop_error}"
        ) from stop_error
    if process is not None:
        raise BrowserFetchError("ChromeDriver service 无法确认已退出")


def _force_stop_service_tree(service) -> None:
    """Stop a WebDriver service tree before its root can orphan Chrome."""
    process = getattr(service, "process", None)
    if process is not None:
        try:
            running = process.poll() is None
        except Exception:
            running = True
        if running:
            _terminate_process_tree(process)
    _stop_service(service)


def _stop_driver_service(driver) -> None:
    _stop_service(getattr(driver, "service", None))


def _create_webdriver_service(service_class):
    configured = os.environ.get("CQU_WEBDRIVER", "").strip()
    kwargs = {}
    if os.name != "nt":
        kwargs["popen_kw"] = {"start_new_session": True}
    if configured:
        return service_class(configured, **kwargs)
    return service_class(**kwargs)


def _probe_owned_debug_port(port: int, identity_url: str) -> bool:
    """Confirm that the DevTools endpoint exposes this session's marker tab."""
    if not _probe_debug_port(port):
        return False
    try:
        return any(
            _normalized_url(target.get("url", "")) == _normalized_url(identity_url)
            for target in _debug_targets(port)
        )
    except BrowserFetchError:
        return False


def _attach_driver(port: int, register_resource=None):
    """Attach a driver and stop its service if any initialization step fails."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError as exc:
        raise BrowserFetchError(
            "缺少 selenium 依赖，请运行 python -m pip install -r requirements.txt"
        ) from exc

    options = Options()
    options.debugger_address = f"127.0.0.1:{port}"
    service = _create_webdriver_service(Service)
    if register_resource is not None:
        register_resource(None, service, True)
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        if register_resource is not None:
            register_resource(driver, service, True)
        driver.set_page_load_timeout(
            float(os.environ.get("CQU_BROWSER_TIMEOUT", "35"))
        )
        return driver
    except Exception as exc:
        try:
            if driver is not None:
                _stop_driver_service(driver)
            else:
                _stop_service(service)
        except BrowserFetchError as cleanup_error:
            raise BrowserFetchError(
                f"常驻 Chrome attach 失败且 service 清理失败: {exc}; {cleanup_error}"
            ) from exc
        if register_resource is not None:
            register_resource(None, None, False)
        raise BrowserFetchError(f"常驻 Chrome attach 失败: {exc}") from exc


def _start_webdriver(profile: Path, register_resource=None):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError as exc:
        raise BrowserFetchError(
            "缺少 selenium 依赖，请运行 python -m pip install -r requirements.txt"
        ) from exc

    options = Options()
    options.binary_location = _find_binary()
    if os.environ.get("CQU_BROWSER_HEADLESS", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }:
        options.add_argument("--headless=new")
    for argument in (
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--window-size=1440,1200",
        f"--user-data-dir={profile}",
    ):
        options.add_argument(argument)

    service = _create_webdriver_service(Service)
    if register_resource is not None:
        register_resource(None, service, False)
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        if register_resource is not None:
            register_resource(driver, service, False)
        driver.set_page_load_timeout(
            float(os.environ.get("CQU_BROWSER_TIMEOUT", "35"))
        )
        return driver
    except Exception as exc:
        try:
            if driver is not None:
                quit_error = None
                try:
                    driver.quit()
                except Exception as quit_exc:
                    quit_error = quit_exc
                if quit_error is None:
                    _stop_driver_service(driver)
                else:
                    _force_stop_service_tree(service)
            else:
                _stop_service(service)
        except BrowserFetchError as cleanup_error:
            raise BrowserFetchError(
                f"Chrome 启动失败且 service 清理失败: {exc}; {cleanup_error}"
            ) from exc
        if register_resource is not None:
            register_resource(None, None, False)
        raise BrowserFetchError(f"Chrome 启动失败: {exc}") from exc


def _debug_targets(port: int) -> list[dict]:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/list", timeout=2
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise BrowserFetchError(f"无法读取 Chrome 标签列表: {exc}") from exc
    return [item for item in payload if item.get("type") == "page"]


def _open_debug_tab(port: int, url: str) -> None:
    encoded = urllib.parse.quote(url, safe=":/")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{encoded}", method="PUT"
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            if response.status != 200:
                raise BrowserFetchError(
                    f"Chrome 创建预热标签失败，HTTP {response.status}: {url}"
                )
    except BrowserFetchError:
        raise
    except Exception as exc:
        raise BrowserFetchError(f"Chrome 创建预热标签失败: {url}: {exc}") from exc


def _normalized_url(url: str) -> str:
    return url.rstrip("/")


def _challenge_title(title: str) -> bool:
    lowered = title.strip().lower()
    return not lowered or any(
        marker in lowered
        for marker in (
            "412",
            "precondition failed",
            "请稍候",
            "安全验证",
            "访问验证",
            "river security",
        )
    )


def _wait_for_target_stable(port: int, url: str) -> None:
    timeout = float(os.environ.get("CQU_BROWSER_WARMUP_TIMEOUT", "22"))
    required = max(1, int(os.environ.get("CQU_BROWSER_STABLE_POLLS", "3")))
    deadline = time.monotonic() + timeout
    previous = None
    stable_polls = 0
    while time.monotonic() < deadline:
        for target in _debug_targets(port):
            target_url = target.get("url", "")
            if _normalized_url(target_url) != _normalized_url(url):
                continue
            title = target.get("title", "")
            signature = (target_url, title)
            if signature == previous and not _challenge_title(title):
                stable_polls += 1
            else:
                stable_polls = 1 if not _challenge_title(title) else 0
            previous = signature
            if stable_polls >= required:
                return
        time.sleep(0.5)
    raise BrowserFetchError(f"Chrome 预热标签未在 {timeout:g} 秒内稳定: {url}")


def _body_text(html: str) -> str:
    body_match = re.search(r"<body\b[^>]*>(.*?)</body>", html, re.I | re.S)
    body = body_match.group(1) if body_match else ""
    body = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        "",
        body,
        flags=re.I | re.S,
    )
    return re.sub(r"<[^>]+>", "", body).strip()


def _usable_html(html: str) -> bool:
    text = _body_text(html)
    if len(text) < 4:
        return False
    lowered = text.lower()
    return not any(
        marker in lowered
        for marker in (
            "412 precondition failed",
            "river security",
            "正在进行安全验证",
            "请稍候，正在验证",
        )
    )


class BrowserSession:
    """Own one Chrome process and one Selenium driver for a WAF batch."""

    def __init__(self, warmup_urls, *, port=_DEFAULT, profile=None):
        self.warmup_urls = list(dict.fromkeys(warmup_urls or []))
        self.port = _debug_port() if port is _DEFAULT else port
        self.profile = Path(profile).expanduser() if profile is not None else None
        self.owns_profile = False
        self.chrome_process = None
        self.owns_chrome = False
        self.driver = None
        self.driver_service = None
        self.attached = False
        self.retry_count = 0
        self.warmup_errors = {}
        self._lock_acquired = False
        self._entered = False
        self._state_lock = threading.RLock()
        marker = f"cqu-browser-session-{uuid.uuid4().hex}"
        self._identity_url = f"data:text/html,<title>{marker}</title>"

    def __enter__(self):
        global _ACTIVE_SESSION
        if not enabled():
            raise BrowserFetchError("浏览器回退已通过 CQU_BROWSER_FETCH=0 禁用")
        if not _SESSION_LOCK.acquire(blocking=False):
            raise BrowserFetchError("已有浏览器会话正在运行")
        self._lock_acquired = True
        _ACTIVE_SESSION = self
        try:
            self._ensure_profile()
            if self.port is None:
                _start_webdriver(self.profile, self._register_driver_resource)
            else:
                if _port_in_use(self.port):
                    raise BrowserFetchError(
                        f"调试端口 {self.port} 已被外部进程占用，未启动或终止任何 Chrome"
                    )
                self._start_browser()
                self._prewarm(self.warmup_urls)
                self._attach()
            self._entered = True
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def _ensure_profile(self) -> None:
        if self.profile is None:
            self.profile = _attach_profile()
        if self.profile is None:
            self.profile = Path(tempfile.mkdtemp(prefix="cqu-browser-session-"))
            self.owns_profile = True
        else:
            self.profile.mkdir(parents=True, exist_ok=True)

    def _start_browser(self) -> None:
        if self.port is None:
            raise BrowserFetchError("未配置 Chrome 调试端口")
        if _port_in_use(self.port):
            raise BrowserFetchError(f"调试端口 {self.port} 已被外部进程占用")
        process = _launch_chrome(self.port, self.profile, self._identity_url)
        self.chrome_process = process
        self.owns_chrome = True
        deadline = time.monotonic() + float(
            os.environ.get("CQU_BROWSER_START_TIMEOUT", "25")
        )
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise BrowserFetchError(
                    f"Chrome 在调试端口 {self.port} 就绪前退出，exit={process.poll()}"
                )
            if _probe_owned_debug_port(self.port, self._identity_url):
                return
            time.sleep(0.25)
        raise BrowserFetchError(f"Chrome 调试端口 {self.port} 25 秒内未就绪")

    def _prewarm(self, urls) -> None:
        self.warmup_errors = {}
        for url in urls:
            try:
                _open_debug_tab(self.port, url)
                _wait_for_target_stable(self.port, url)
            except BrowserFetchError as exc:
                self.warmup_errors[url] = str(exc)

    def _attach(self) -> None:
        _attach_driver(self.port, self._register_driver_resource)

    def _register_driver_resource(self, driver, service, attached: bool) -> None:
        self.driver = driver
        self.driver_service = service
        self.attached = attached

    def _dispose_driver(self) -> None:
        driver = self.driver
        service = self.driver_service
        if service is None and driver is not None:
            service = getattr(driver, "service", None)
        attached = self.attached
        if driver is None and service is None:
            return
        if attached:
            _stop_service(service)
        else:
            if driver is not None:
                quit_error = None
                try:
                    driver.quit()
                except Exception as exc:
                    quit_error = exc
                if quit_error is not None:
                    _force_stop_service_tree(service)
                else:
                    _stop_service(service)
            else:
                _stop_service(service)
        self._register_driver_resource(None, None, False)

    def _stop_owned_chrome(self) -> None:
        process = self.chrome_process
        owned = self.owns_chrome
        if owned and process is not None:
            try:
                _terminate_process_tree(process)
                stopped = process.poll() is not None
            except BrowserFetchError as exc:
                raise BrowserFetchError(f"受管 Chrome 无法停止: {exc}") from exc
            except Exception as exc:
                raise BrowserFetchError(f"无法确认受管 Chrome 已停止: {exc}") from exc
            if not stopped:
                raise BrowserFetchError("受管 Chrome 无法确认已停止")

    def _release_owned_chrome(self) -> None:
        self.chrome_process = None
        self.owns_chrome = False

    def _wait_until_port_released(self) -> None:
        if self.port is None:
            return
        deadline = time.monotonic() + float(
            os.environ.get("CQU_BROWSER_STOP_TIMEOUT", "10")
        )
        while time.monotonic() < deadline:
            if not _port_in_use(self.port):
                return
            time.sleep(0.2)
        raise BrowserFetchError(f"调试端口 {self.port} 未释放")

    def _restart_for(self, url: str) -> None:
        self._dispose_driver()
        self._stop_owned_chrome()
        self._wait_until_port_released()
        self._release_owned_chrome()
        if self.port is None:
            _start_webdriver(self.profile, self._register_driver_resource)
            return
        self._start_browser()
        self._prewarm([url])
        self._attach()

    def _fetch_once(self, url: str) -> str:
        driver = self.driver
        if driver is None:
            raise BrowserFetchError("Selenium driver 不可用")
        try:
            driver.current_url
        except Exception as exc:
            raise BrowserFetchError(f"Selenium driver 已失效: {exc}") from exc

        try:
            if self.attached:
                for handle in list(driver.window_handles):
                    try:
                        driver.switch_to.window(handle)
                        if _normalized_url(driver.current_url) != _normalized_url(url):
                            continue
                        html = driver.page_source or ""
                        if _usable_html(html):
                            return html
                    except Exception:
                        continue
            driver.get(url)
            deadline = time.monotonic() + float(
                os.environ.get("CQU_BROWSER_READ_TIMEOUT", "12")
            )
            while time.monotonic() < deadline:
                html = driver.page_source or ""
                if _usable_html(html):
                    return html
                time.sleep(0.25)
        except BrowserFetchError:
            raise
        except Exception as exc:
            raise BrowserFetchError(f"浏览器抓取失败: {exc}") from exc
        raise BrowserFetchError(f"浏览器未通过 WAF 挑战，页面为空或仍被拦截: {url}")

    def fetch(self, url: str) -> str:
        with self._state_lock:
            if not self._entered:
                raise BrowserFetchError("BrowserSession 必须在 with 语句中使用")
            try:
                if url in self.warmup_errors:
                    raise BrowserFetchError(self.warmup_errors[url])
                return self._fetch_once(url)
            except BrowserFetchError as first_error:
                self.retry_count += 1
                try:
                    self._restart_for(url)
                    return self._fetch_once(url)
                except BrowserFetchError as retry_error:
                    raise BrowserFetchError(
                        f"浏览器抓取失败，单来源 retry 仍未恢复: {url}: {retry_error}"
                    ) from first_error

    def close(self) -> None:
        global _ACTIVE_SESSION
        with self._state_lock:
            self._entered = False
            had_owned_chrome = self.owns_chrome and self.chrome_process is not None
            dispose_error = None
            try:
                self._dispose_driver()
            except BrowserFetchError as exc:
                dispose_error = exc
            chrome_error = None
            if had_owned_chrome:
                try:
                    self._stop_owned_chrome()
                except BrowserFetchError as exc:
                    chrome_error = exc
            port_error = None
            if self.port is not None and had_owned_chrome and chrome_error is None:
                try:
                    self._wait_until_port_released()
                except BrowserFetchError as exc:
                    port_error = exc
            if had_owned_chrome and chrome_error is None and port_error is None:
                self._release_owned_chrome()
            cleanup_error = dispose_error or chrome_error or port_error
            if cleanup_error is not None:
                raise cleanup_error
            if self.owns_profile and self.profile is not None:
                shutil.rmtree(self.profile, ignore_errors=True)
                self.owns_profile = False
            if _ACTIVE_SESSION is self:
                _ACTIVE_SESSION = None
            if self._lock_acquired:
                self._lock_acquired = False
                _SESSION_LOCK.release()


def prepare(urls) -> None:
    """Legacy compatibility hook; managed sessions now perform their own warmup."""
    if not enabled():
        raise BrowserFetchError("浏览器回退已通过 CQU_BROWSER_FETCH=0 禁用")


def fetch_html(url: str, warmup_urls=None) -> str:
    """Compatibility wrapper around a fully managed one-shot session."""
    urls = list(warmup_urls) if warmup_urls is not None else [url]
    with BrowserSession(urls) as session:
        return session.fetch(url)


def _close_active_session() -> None:
    session = _ACTIVE_SESSION
    if session is not None:
        session.close()


atexit.register(_close_active_session)
