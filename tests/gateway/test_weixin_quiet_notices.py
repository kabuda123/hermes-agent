"""Weixin skips unsolicited setup/reset notices without losing reset bookkeeping."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from gateway.config import GatewayConfig, Platform
from gateway.run import GatewayRunner
from gateway.session import SessionSource


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [Platform.WEIXIN, Platform.TELEGRAM])
async def test_reset_notice_keeps_sidecar_and_clears_reason(platform, monkeypatch):
    monkeypatch.setattr("gateway.run_turn.build_channel_continuity_note", lambda *_: None)
    runner = object.__new__(GatewayRunner)
    adapter = SimpleNamespace(send=AsyncMock())
    runner._delivery_adapter_for = Mock(return_value=adapter)
    runner._thread_metadata_for_source = Mock(return_value={})
    runner._reset_notice_session_info = Mock(return_value="model details")
    source = SessionSource(platform=platform, chat_id="chat", user_id="user")
    entry = SimpleNamespace(auto_reset_reason="suspended")
    notes = []

    await runner._hmwa_deliver_auto_reset_notice(entry, source, notes)

    assert notes
    assert entry.auto_reset_reason is None
    assert adapter.send.await_count == (0 if platform == Platform.WEIXIN else 1)
    if platform == Platform.WEIXIN:
        runner._reset_notice_session_info.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [Platform.WEIXIN, Platform.TELEGRAM])
@pytest.mark.parametrize("has_history", [False, True])
async def test_missing_home_channel_notice_is_silent_on_weixin(platform, has_history, monkeypatch):
    monkeypatch.setattr("agent.secret_scope.get_secret", lambda *_: "")
    monkeypatch.delenv("WEIXIN_HOME_CHANNEL", raising=False)
    monkeypatch.delenv("TELEGRAM_HOME_CHANNEL", raising=False)
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig()
    monkeypatch.setattr(GatewayRunner, "async_session_store", property(
        lambda self: SimpleNamespace(has_any_sessions=AsyncMock(return_value=True))))
    runner._deliver_platform_notice = AsyncMock()
    source = SessionSource(platform=platform, chat_id="chat", user_id="user")

    await runner._hmwa_first_contact_notes(source, [{}] if has_history else [], [])

    expected = int(platform != Platform.WEIXIN and not has_history)
    assert runner._deliver_platform_notice.await_count == expected
