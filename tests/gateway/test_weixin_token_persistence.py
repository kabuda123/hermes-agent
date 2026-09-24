"""Preserve the deployed fork's stale-token recovery during upstream upgrades."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms import weixin


@pytest.mark.asyncio
@pytest.mark.parametrize("refresh_during_send", [False, True])
@pytest.mark.parametrize("send_media", [False, True])
async def test_stale_token_recovery_preserves_disk_and_newer_token(tmp_path, monkeypatch, refresh_during_send, send_media):
    adapter = weixin.WeixinAdapter(PlatformConfig(enabled=True, token="test", extra={"account_id": "account"}))
    adapter._send_session = object()
    adapter._token = "test"
    adapter._account_id = "account"
    adapter._token_store = weixin.ContextTokenStore(str(tmp_path))
    await adapter._token_store.set("account", "peer", "old")
    sent = []

    async def send(*args, **kwargs):
        sent.append(kwargs["context_token"])
        if len(sent) == 1:
            if refresh_during_send:
                await adapter._token_store.set("account", "peer", "new")
            return {"ret": -2, "errmsg": "prepare failed"}
        return {"ret": 0}

    if send_media:
        monkeypatch.setattr(weixin, "_send_items", send)
        monkeypatch.setattr(weixin, "_upload_ciphertext", AsyncMock(return_value="enc-q"))
        monkeypatch.setattr(weixin, "_get_upload_url", AsyncMock(return_value={"upload_full_url": "https://cdn.example/upload"}))
        doc = tmp_path / "report.pdf"
        doc.write_bytes(b"%PDF-1.4")
        result = await adapter.send_document("peer", str(doc))
    else:
        monkeypatch.setattr(weixin, "_send_message", send)
        result = await adapter.send("peer", "hello")

    assert result.success
    assert sent == ["old", None]
    expected = "new" if refresh_during_send else None
    assert adapter._token_store.get("account", "peer") == expected
    restored = weixin.ContextTokenStore(str(tmp_path))
    restored.restore("account")
    assert restored.get("account", "peer") == expected


@pytest.mark.asyncio
async def test_queued_send_reads_token_after_acquiring_send_gate(tmp_path, monkeypatch):
    adapter = weixin.WeixinAdapter(PlatformConfig(enabled=True, token="test", extra={"account_id": "account"}))
    adapter._send_session = object()
    adapter._token = "test"
    adapter._account_id = "account"
    adapter._token_store = weixin.ContextTokenStore(str(tmp_path))
    await adapter._token_store.set("account", "peer", "old")
    sent = []
    started = asyncio.Event()

    async def send(*args, **kwargs):
        sent.append(kwargs["context_token"])
        return {"ret": 0}

    async def queued_send():
        started.set()
        return await adapter.send("peer", "hello")

    monkeypatch.setattr(weixin, "_send_message", send)
    async with adapter._send_text_gate:
        task = asyncio.create_task(queued_send())
        await started.wait()
        await adapter._token_store.set("account", "peer", "new")
    assert (await task).success
    assert sent == ["new"]
