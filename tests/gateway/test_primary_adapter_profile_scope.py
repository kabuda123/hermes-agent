"""Keep the deployed primary-adapter credential scope across upstream updates."""

from unittest.mock import AsyncMock, Mock

import pytest

from agent import secret_scope
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.run import GatewayRunner


@pytest.mark.asyncio
async def test_primary_adapter_creation_uses_launch_profile_scope(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("WEIXIN_CDN_BASE_URL=https://profile.example\n")
    monkeypatch.setattr("gateway.run.get_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(secret_scope, "_MULTIPLEX_ACTIVE", True)
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(multiplex_profiles=True, platforms={
        Platform.WEIXIN: PlatformConfig(enabled=True, token="test")})
    runner._abort_startup_if_shutdown_requested = AsyncMock(return_value=False)
    runner._multiplex_on = Mock(return_value=True)
    runner._wire_adapter_handlers = Mock()
    seen = []

    def create(platform, config):
        seen.append(secret_scope.get_secret("WEIXIN_CDN_BASE_URL"))
        return object()

    runner._create_adapter = create
    previous = secret_scope.current_secret_scope()
    result = await runner._start_prefilter_platforms()
    assert seen == ["https://profile.example"]
    assert result[1] == 1
    assert secret_scope.current_secret_scope() is previous
