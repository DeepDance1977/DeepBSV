import httpx
import pytest

from deepbsv.rpc.client import BSVNodeRPCClient, BSVNodeRPCError


@pytest.mark.asyncio
async def test_get_mining_candidate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_post(*_args: list[object], **_kwargs: dict[str, object]) -> httpx.Response:
        fake_payload = {
            "result": {
                "id": "cand_001",
                "prevhash": "0000000000000000000000000000000000000000000000000000000000000000",
                "coinb1": "01000000",
                "coinb2": "00000000",
            },
            "error": None,
            "id": 1,
        }
        return httpx.Response(200, json=fake_payload)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = BSVNodeRPCClient()
    candidate = await client.get_mining_candidate()

    assert candidate["id"] == "cand_001"
    assert "prevhash" in candidate


@pytest.mark.asyncio
async def test_rpc_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_post(*_args: list[object], **_kwargs: dict[str, object]) -> httpx.Response:
        fake_payload = {
            "result": None,
            "error": {"code": -10, "message": "Node is warming up"},
            "id": 1,
        }
        return httpx.Response(200, json=fake_payload)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = BSVNodeRPCClient()
    with pytest.raises(BSVNodeRPCError) as exc_info:
        await client.get_mining_candidate()

    assert exc_info.value.code == -10
    assert "warming up" in exc_info.value.message
