from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import config
from tools.cdp_browser import CDPBrowserManager


class _FakeBrowser:
    def __init__(self) -> None:
        self.contexts = []

    def is_connected(self) -> bool:
        return True


def _build_playwright(connect_impl):
    return SimpleNamespace(
        chromium=SimpleNamespace(connect_over_cdp=connect_impl)
    )


@pytest.mark.asyncio
async def test_connect_via_cdp_retries_until_success(monkeypatch, caplog):
    manager = CDPBrowserManager()
    manager.debug_port = 9222
    browser = _FakeBrowser()
    attempts = {"count": 0}

    async def connect_over_cdp(ws_url: str, timeout: int | None = None):
        del ws_url, timeout
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("403 Forbidden")
        return browser

    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "CDP_CONNECT_RETRY_COUNT", 3)
    monkeypatch.setattr(config, "CDP_CONNECT_RETRY_DELAY_SEC", 0)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 1)
    caplog.set_level(logging.WARNING, logger="MediaCrawler")

    await manager._connect_via_cdp(_build_playwright(connect_over_cdp))

    assert attempts["count"] == 3
    assert manager.browser is browser
    assert "CDP connect attempt 1/3 failed" in caplog.text
    assert "Retrying in 0s" in caplog.text


@pytest.mark.asyncio
async def test_connect_via_cdp_raises_after_retry_limit(monkeypatch):
    manager = CDPBrowserManager()
    manager.debug_port = 9222
    attempts = {"count": 0}

    async def connect_over_cdp(ws_url: str, timeout: int | None = None):
        del ws_url, timeout
        attempts["count"] += 1
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "CDP_CONNECT_RETRY_COUNT", 2)
    monkeypatch.setattr(config, "CDP_CONNECT_RETRY_DELAY_SEC", 0)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 1)

    with pytest.raises(RuntimeError, match="after 2 attempts"):
        await manager._connect_via_cdp(_build_playwright(connect_over_cdp))

    assert attempts["count"] == 2
