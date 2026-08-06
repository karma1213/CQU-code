import os
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

import browser_fetch


class _FakeService:
    def __init__(self, stop_error=None, process=None):
        self.stop_calls = 0
        self.stop_error = stop_error
        self.process = process

    def stop(self):
        self.stop_calls += 1
        if self.stop_error is not None:
            raise self.stop_error


class _FakeSwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        self.driver.active_handle = handle


class _FakeDriver:
    def __init__(self, html="<html><body><main>loaded</main></body></html>"):
        self.service = _FakeService()
        self.current_url = "about:blank"
        self.page_source = html
        self.window_handles = ["main"]
        self.switch_to = _FakeSwitchTo(self)
        self.quit_calls = 0
        self.timeout = None

    def get(self, url):
        self.current_url = url

    def set_page_load_timeout(self, timeout):
        self.timeout = timeout

    def quit(self):
        self.quit_calls += 1


class _FakeProcess:
    def __init__(self, pid=4321):
        self.pid = pid
        self.returncode = None
        self.poll_calls = 0
        self.kill_calls = 0

    def poll(self):
        self.poll_calls += 1
        return self.returncode

    def kill(self):
        self.kill_calls += 1


class _FakeOptions:
    def __init__(self):
        self.debugger_address = None
        self.binary_location = None
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)


def _fake_selenium_modules(driver, service):
    selenium = types.ModuleType("selenium")
    webdriver = types.ModuleType("selenium.webdriver")
    chrome = types.ModuleType("selenium.webdriver.chrome")
    options = types.ModuleType("selenium.webdriver.chrome.options")
    service_module = types.ModuleType("selenium.webdriver.chrome.service")
    webdriver.Chrome = mock.Mock(return_value=driver)
    options.Options = _FakeOptions
    service_module.Service = mock.Mock(return_value=service)
    selenium.webdriver = webdriver
    webdriver.chrome = chrome
    chrome.options = options
    chrome.service = service_module
    return {
        "selenium": selenium,
        "selenium.webdriver": webdriver,
        "selenium.webdriver.chrome": chrome,
        "selenium.webdriver.chrome.options": options,
        "selenium.webdriver.chrome.service": service_module,
    }, webdriver.Chrome


class BrowserFetchTest(unittest.TestCase):
    def setUp(self):
        lock_patcher = mock.patch.object(
            browser_fetch, "_SESSION_LOCK", threading.Lock(), create=True
        )
        lock_patcher.start()
        self.addCleanup(lock_patcher.stop)

    def test_disabled_by_environment(self):
        with mock.patch.dict(os.environ, {"CQU_BROWSER_FETCH": "0"}):
            self.assertFalse(browser_fetch.enabled())

    def test_attach_configuration_failure_stops_service(self):
        driver = _FakeDriver()
        driver.set_page_load_timeout = mock.Mock(side_effect=RuntimeError("timeout setup failed"))
        with mock.patch("selenium.webdriver.Chrome", return_value=driver):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "attach"):
                browser_fetch._attach_driver(9223)
        self.assertEqual(driver.service.stop_calls, 1)

    def test_attach_uses_configured_driver_in_an_isolated_posix_session(self):
        driver = _FakeDriver()
        service = driver.service
        selenium_modules, _ = _fake_selenium_modules(driver, service)
        service_constructor = selenium_modules[
            "selenium.webdriver.chrome.service"
        ].Service

        with (
            mock.patch.dict(sys.modules, selenium_modules),
            mock.patch.dict(
                os.environ,
                {"CQU_WEBDRIVER": "/opt/cqu/chromedriver"},
                clear=False,
            ),
            mock.patch.object(browser_fetch.os, "name", "posix"),
        ):
            self.assertIs(browser_fetch._attach_driver(9223), driver)

        service_constructor.assert_called_once_with(
            "/opt/cqu/chromedriver",
            popen_kw={"start_new_session": True},
        )

    def test_direct_driver_quit_failure_terminates_service_tree_before_stop(self):
        process = _FakeProcess(pid=1008)
        service = _FakeService(process=process)
        service.stop = mock.Mock(side_effect=lambda: setattr(process, "returncode", 0))
        driver = _FakeDriver()
        driver.service = service
        driver.quit = mock.Mock(side_effect=RuntimeError("driver quit failed"))
        session = browser_fetch.BrowserSession([], port=None)
        session.driver = driver
        session.driver_service = service
        session.attached = False

        with mock.patch.object(
            browser_fetch,
            "_terminate_process_tree",
            side_effect=lambda owned: setattr(owned, "returncode", 0),
        ) as terminate:
            session._dispose_driver()

        terminate.assert_called_once_with(process)
        self.assertIsNone(session.driver)
        self.assertIsNone(session.driver_service)

    def test_direct_driver_setup_and_quit_failures_preserve_setup_error(self):
        process = _FakeProcess(pid=1010)
        service = _FakeService(process=process)
        driver = _FakeDriver()
        driver.service = service
        driver.set_page_load_timeout = mock.Mock(
            side_effect=RuntimeError("timeout setup failed")
        )
        driver.quit = mock.Mock(side_effect=RuntimeError("driver quit failed"))
        selenium_modules, _ = _fake_selenium_modules(driver, service)

        with (
            mock.patch.dict(sys.modules, selenium_modules),
            mock.patch.object(
                browser_fetch,
                "_terminate_process_tree",
                side_effect=lambda owned: setattr(owned, "returncode", 0),
            ),
        ):
            with self.assertRaisesRegex(
                browser_fetch.BrowserFetchError, "timeout setup failed"
            ):
                browser_fetch._start_webdriver(Path("profile"))

    def test_close_is_idempotent_and_stops_owned_resources_once(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        driver = _FakeDriver()
        process = _FakeProcess()
        session.driver = driver
        session.attached = True
        session.chrome_process = process
        session.owns_chrome = True

        with mock.patch.object(
            browser_fetch,
            "_terminate_process_tree",
            side_effect=lambda owned: setattr(owned, "returncode", 0),
        ) as terminate:
            session.close()
            session.close()

        self.assertEqual(driver.service.stop_calls, 1)
        self.assertEqual(driver.quit_calls, 0)
        terminate.assert_called_once_with(process)
        self.assertIsNone(session.driver)
        self.assertIsNone(session.chrome_process)

    def test_external_debug_port_is_rejected_without_termination(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        with (
            mock.patch.object(browser_fetch, "_port_in_use", return_value=True),
            mock.patch.object(browser_fetch, "_terminate_process_tree") as terminate,
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "9223.*占用"):
                session.__enter__()
        terminate.assert_not_called()

    def test_retry_order_disposes_driver_before_restarting_single_url(self):
        session = browser_fetch.BrowserSession(["https://one.test", "https://two.test"], port=9223)
        events = []
        with (
            mock.patch.object(session, "_dispose_driver", side_effect=lambda: events.append("dispose")),
            mock.patch.object(session, "_stop_owned_chrome", side_effect=lambda: events.append("stop")),
            mock.patch.object(
                session,
                "_wait_until_port_released",
                side_effect=lambda: events.append("wait"),
            ),
            mock.patch.object(session, "_start_browser", side_effect=lambda: events.append("start")),
            mock.patch.object(
                session,
                "_prewarm",
                side_effect=lambda urls: events.append(("prewarm", list(urls))),
            ),
            mock.patch.object(session, "_attach", side_effect=lambda: events.append("attach")),
        ):
            session._restart_for("https://two.test")

        self.assertEqual(
            events,
            [
                "dispose",
                "stop",
                "wait",
                "start",
                ("prewarm", ["https://two.test"]),
                "attach",
            ],
        )

    def test_retry_does_not_relaunch_when_port_stays_occupied(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        with (
            mock.patch.object(session, "_dispose_driver"),
            mock.patch.object(session, "_stop_owned_chrome"),
            mock.patch.object(
                session,
                "_wait_until_port_released",
                side_effect=browser_fetch.BrowserFetchError("端口 9223 未释放"),
            ),
            mock.patch.object(session, "_start_browser") as start,
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "未释放"):
                session._restart_for("https://example.test")
        start.assert_not_called()

    def test_retry_stops_stale_driver_service(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        driver = _FakeDriver()
        session.driver = driver
        session.attached = True
        session.chrome_process = _FakeProcess()
        session.owns_chrome = True
        session._entered = True

        with (
            mock.patch.object(
                session,
                "_fetch_once",
                side_effect=[browser_fetch.BrowserFetchError("stale driver"), "<html>ok</html>"],
            ),
            mock.patch.object(session, "_stop_owned_chrome"),
            mock.patch.object(session, "_wait_until_port_released"),
            mock.patch.object(session, "_start_browser"),
            mock.patch.object(session, "_prewarm"),
            mock.patch.object(session, "_attach"),
        ):
            self.assertEqual(session.fetch("https://example.test"), "<html>ok</html>")

        self.assertEqual(driver.service.stop_calls, 1)
        self.assertEqual(session.retry_count, 1)

    def test_retry_does_not_relaunch_when_driver_service_cannot_stop(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        driver = _FakeDriver()
        driver.service = _FakeService(RuntimeError("service still running"))
        session.driver = driver
        session.attached = True

        with (
            mock.patch.object(session, "_start_browser") as start,
            mock.patch.object(session, "_prewarm"),
            mock.patch.object(session, "_attach"),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "ChromeDriver"):
                session._restart_for("https://example.test")

        start.assert_not_called()
        self.assertIs(session.driver, driver)

    def test_retry_terminates_and_rechecks_service_that_survives_clean_stop(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        service_process = _FakeProcess()
        driver = _FakeDriver()
        driver.service = _FakeService(process=service_process)
        session.driver = driver
        session.attached = True

        with (
            mock.patch.object(browser_fetch, "_terminate_process_tree") as terminate,
            mock.patch.object(session, "_start_browser") as start,
            mock.patch.object(session, "_prewarm"),
            mock.patch.object(session, "_attach"),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "ChromeDriver"):
                session._restart_for("https://example.test")

        terminate.assert_called_once_with(service_process)
        self.assertGreaterEqual(service_process.poll_calls, 2)
        start.assert_not_called()
        self.assertIs(session.driver, driver)

    def test_attach_configuration_failure_keeps_cleanup_handle_and_session_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            first = browser_fetch.BrowserSession(
                ["https://example.test"], port=9223, profile=directory
            )
            second = browser_fetch.BrowserSession(
                ["https://other.test"], port=9224, profile=directory
            )
            chrome_process = _FakeProcess(pid=1001)
            service_process = _FakeProcess(pid=1002)
            service = _FakeService(process=service_process)
            driver = _FakeDriver()
            driver.service = service
            driver.set_page_load_timeout = mock.Mock(
                side_effect=RuntimeError("timeout setup failed")
            )
            selenium_modules, chrome_constructor = _fake_selenium_modules(driver, service)

            with (
                mock.patch.dict(sys.modules, selenium_modules),
                mock.patch.object(browser_fetch, "_port_in_use", return_value=False),
                mock.patch.object(browser_fetch, "_launch_chrome", return_value=chrome_process) as launch,
                mock.patch.object(browser_fetch, "_probe_owned_debug_port", return_value=True),
                mock.patch.object(
                    browser_fetch,
                    "_terminate_process_tree",
                    side_effect=lambda owned: (
                        setattr(owned, "returncode", 0)
                        if owned is chrome_process
                        else None
                    ),
                ),
                mock.patch.object(first, "_prewarm"),
            ):
                with self.assertRaises(browser_fetch.BrowserFetchError):
                    first.__enter__()

                self.assertTrue(browser_fetch._SESSION_LOCK.locked())
                poll_calls_before_retry = service_process.poll_calls
                with self.assertRaises(browser_fetch.BrowserFetchError):
                    second.__enter__()
                launch.assert_called_once()
                self.assertEqual(chrome_constructor.call_count, 1)

                service_process.returncode = 0
                first.close()

            self.assertGreater(service_process.poll_calls, poll_calls_before_retry)
            self.assertFalse(browser_fetch._SESSION_LOCK.locked())

    def test_webdriver_constructor_failure_keeps_service_handle_and_session_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            session = browser_fetch.BrowserSession(
                ["https://example.test"], port=None, profile=directory
            )
            service_process = _FakeProcess(pid=1003)
            service = _FakeService(process=service_process)
            driver = _FakeDriver()
            selenium_modules, chrome_constructor = _fake_selenium_modules(driver, service)
            chrome_constructor.side_effect = RuntimeError("constructor failed")

            with (
                mock.patch.dict(sys.modules, selenium_modules),
                mock.patch.object(browser_fetch, "_find_binary", return_value="chrome"),
                mock.patch.object(browser_fetch, "_terminate_process_tree"),
            ):
                with self.assertRaises(browser_fetch.BrowserFetchError):
                    session.__enter__()

                self.assertTrue(browser_fetch._SESSION_LOCK.locked())
                self.assertEqual(chrome_constructor.call_count, 1)

                service_process.returncode = 0
                session.close()

            self.assertFalse(browser_fetch._SESSION_LOCK.locked())

    def test_close_keeps_session_lock_when_driver_service_cannot_stop(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        driver = _FakeDriver()
        driver.service = _FakeService(RuntimeError("service still running"))
        session.driver = driver
        session.attached = True
        browser_fetch._SESSION_LOCK.acquire()
        session._lock_acquired = True

        with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "ChromeDriver"):
            session.close()

        self.assertTrue(browser_fetch._SESSION_LOCK.locked())
        self.assertTrue(session._lock_acquired)
        driver.service.stop_error = None
        session.close()

    def test_close_keeps_chrome_ownership_when_termination_is_unconfirmed(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        process = _FakeProcess(pid=1004)
        session.chrome_process = process
        session.owns_chrome = True
        browser_fetch._SESSION_LOCK.acquire()
        session._lock_acquired = True

        with (
            mock.patch.object(browser_fetch, "_terminate_process_tree") as terminate,
            mock.patch.object(session, "_wait_until_port_released"),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "Chrome"):
                session.close()

            self.assertIs(session.chrome_process, process)
            self.assertTrue(session.owns_chrome)
            self.assertTrue(browser_fetch._SESSION_LOCK.locked())

            process.returncode = 0
            session.close()

        self.assertGreaterEqual(terminate.call_count, 1)
        self.assertIsNone(session.chrome_process)
        self.assertFalse(session.owns_chrome)
        self.assertFalse(browser_fetch._SESSION_LOCK.locked())

    def test_close_keeps_chrome_ownership_until_debug_port_is_released(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        process = _FakeProcess(pid=1005)
        session.chrome_process = process
        session.owns_chrome = True
        browser_fetch._SESSION_LOCK.acquire()
        session._lock_acquired = True

        with (
            mock.patch.object(
                browser_fetch,
                "_terminate_process_tree",
                side_effect=lambda owned: setattr(owned, "returncode", 0),
            ),
            mock.patch.object(
                session,
                "_wait_until_port_released",
                side_effect=[browser_fetch.BrowserFetchError("端口 9223 未释放"), None],
            ),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "未释放"):
                session.close()

            self.assertIs(session.chrome_process, process)
            self.assertTrue(session.owns_chrome)
            self.assertTrue(browser_fetch._SESSION_LOCK.locked())

            session.close()

        self.assertIsNone(session.chrome_process)
        self.assertFalse(session.owns_chrome)
        self.assertFalse(browser_fetch._SESSION_LOCK.locked())

    def test_windows_tree_failure_does_not_fall_back_to_root_only_kill(self):
        process = _FakeProcess(pid=1006)
        result = mock.Mock(returncode=1)
        with (
            mock.patch.object(browser_fetch.os, "name", "nt"),
            mock.patch.object(browser_fetch.subprocess, "run", return_value=result),
            mock.patch.object(browser_fetch, "_wait_for_process_exit", return_value=False),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "taskkill"):
                browser_fetch._terminate_process_tree(process)

        self.assertEqual(process.kill_calls, 0)

    def test_posix_tree_failure_escalates_and_reports_still_running_process(self):
        process = _FakeProcess(pid=1007)
        with (
            mock.patch.object(browser_fetch.os, "name", "posix"),
            mock.patch.object(
                browser_fetch.os, "getpgid", return_value=2007, create=True
            ),
            mock.patch.object(browser_fetch.os, "killpg", create=True) as killpg,
            mock.patch.object(browser_fetch.signal, "SIGKILL", 9, create=True),
            mock.patch.object(
                browser_fetch,
                "_wait_for_process_exit",
                side_effect=[False, False],
            ),
        ):
            with self.assertRaises(browser_fetch.BrowserFetchError):
                browser_fetch._terminate_process_tree(process)

        self.assertEqual(
            killpg.call_args_list,
            [
                mock.call(2007, browser_fetch.signal.SIGTERM),
                mock.call(2007, 9),
            ],
        )

    def test_start_browser_rejects_debug_endpoint_not_owned_by_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            session = browser_fetch.BrowserSession(
                ["https://example.test"], port=9223, profile=directory
            )
            process = _FakeProcess()
            with (
                mock.patch.dict(os.environ, {"CQU_BROWSER_START_TIMEOUT": "0.5"}),
                mock.patch.object(browser_fetch, "_port_in_use", return_value=False),
                mock.patch.object(browser_fetch, "_launch_chrome", return_value=process),
                mock.patch.object(browser_fetch, "_probe_debug_port", return_value=True),
                mock.patch.object(
                    browser_fetch,
                    "_debug_targets",
                    return_value=[{"url": "about:blank#external-session"}],
                ),
                mock.patch.object(browser_fetch.time, "monotonic", side_effect=[0, 0, 1]),
                mock.patch.object(browser_fetch.time, "sleep"),
            ):
                with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "未就绪"):
                    session._start_browser()

    def test_identity_marker_uses_startup_url_that_chrome_preserves(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        self.assertRegex(
            session._identity_url,
            r"^data:text/html,<title>cqu-browser-session-[0-9a-f]+</title>$",
        )

    def test_attach_failure_cleans_up_managed_chrome(self):
        session = browser_fetch.BrowserSession(["https://example.test"], port=9223)
        process = _FakeProcess()
        with (
            mock.patch.object(browser_fetch, "_port_in_use", return_value=False),
            mock.patch.object(browser_fetch, "_launch_chrome", return_value=process),
            mock.patch.object(browser_fetch, "_probe_owned_debug_port", return_value=True),
            mock.patch.object(session, "_prewarm"),
            mock.patch.object(session, "_attach", side_effect=browser_fetch.BrowserFetchError("attach failed")),
            mock.patch.object(
                browser_fetch,
                "_terminate_process_tree",
                side_effect=lambda owned: setattr(owned, "returncode", 0),
            ) as terminate,
            mock.patch.object(session, "_wait_until_port_released"),
        ):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "attach failed"):
                session.__enter__()
        terminate.assert_called_once_with(process)

    def test_concurrent_sessions_do_not_create_two_browsers(self):
        first = browser_fetch.BrowserSession(["https://one.test"], port=9223)
        second = browser_fetch.BrowserSession(["https://two.test"], port=9223)
        process = _FakeProcess()
        driver = _FakeDriver()
        with (
            mock.patch.object(browser_fetch, "_port_in_use", return_value=False),
            mock.patch.object(browser_fetch, "_launch_chrome", return_value=process) as launch,
            mock.patch.object(browser_fetch, "_probe_owned_debug_port", return_value=True),
            mock.patch.object(
                browser_fetch,
                "_terminate_process_tree",
                side_effect=lambda owned: setattr(owned, "returncode", 0),
            ),
            mock.patch.object(first, "_prewarm"),
            mock.patch.object(first, "_attach", side_effect=lambda: setattr(first, "driver", driver)),
            mock.patch.object(first, "_wait_until_port_released"),
        ):
            first.__enter__()
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "已有浏览器会话"):
                second.__enter__()
            first.close()
        self.assertEqual(launch.call_count, 1)

    def test_fetch_html_uses_compatibility_context_wrapper(self):
        context = mock.MagicMock()
        context.__enter__.return_value.fetch.return_value = "<html><body>loaded</body></html>"
        urls = ["https://one.test", "https://two.test"]
        with mock.patch.object(browser_fetch, "BrowserSession", return_value=context) as session_class:
            result = browser_fetch.fetch_html("https://two.test", urls)
        self.assertIn("loaded", result)
        session_class.assert_called_once_with(urls)
        context.__enter__.return_value.fetch.assert_called_once_with("https://two.test")
        context.__exit__.assert_called_once()

    def test_fetch_html_rejects_empty_waf_document_without_real_browser(self):
        context = mock.MagicMock()
        context.__enter__.return_value.fetch.side_effect = browser_fetch.BrowserFetchError(
            "未通过 WAF 挑战"
        )
        with mock.patch.object(browser_fetch, "BrowserSession", return_value=context):
            with self.assertRaisesRegex(browser_fetch.BrowserFetchError, "未通过 WAF 挑战"):
                browser_fetch.fetch_html("https://example.test")

    def test_find_binary_honors_explicit_path(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory, "chrome")
            binary.write_text("", encoding="ascii")
            with mock.patch.dict(os.environ, {"CQU_BROWSER_BINARY": str(binary)}):
                self.assertEqual(browser_fetch._find_binary(), str(binary))


if __name__ == "__main__":
    unittest.main()
