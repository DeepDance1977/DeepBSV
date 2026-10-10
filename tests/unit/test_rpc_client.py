```python
import httpx
import pytest

from deepbsv.rpc.client import BSVNodeRPCClient, BSVNodeRPCError


def assert_rpc_request(
    kwargs: dict[str, object],
    method: str,
    params: list[object],
) -> None:
    payload = kwargs.get("json")

    assert isinstance(payload, dict)
    assert payload["method"] == method
    assert payload["params"] == params


@pytest.mark.asyncio
async def test_get_mining_candidate_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = httpx.Request("POST", "http://127.0.0.1:8332")

    async def mock_post(
        *_args: object,
        **kwargs: object,
    ) -> httpx.Response:
        assert_rpc_request(
            kwargs,
            "getminingcandidate",
            [True],
        )

        fake_payload = {
            "result": {
                "id": "cand_001",
                "prevhash": "00" * 32,
                "coinbase": (
                    "01000000010000000000000000000000000000000000000000"
                    "0000000000000000000000ffffffff"
                    "0b03e8031a4d494e494e47"
                    "ffffffff"
                    "0100f2052a01000000"
                    "00000000"
                ),
                "version": 536870912,
                "coinbaseValue": 5000000000,
                "nBits": "207fffff",
                "time": 1700000000,
                "height": 100,
                "merkleProof": [],
            },
            "error": None,
            "id": 1,
        }

        return httpx.Response(
            200,
            json=fake_payload,
            request=req,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        mock_post,
    )

    client = BSVNodeRPCClient()
    candidate = await client.get_mining_candidate()

    assert candidate["id"] == "cand_001"
    assert candidate["prevhash"] == "00" * 32
    assert candidate["coinbase"]
    assert candidate["version"] == 536870912
    assert candidate["coinbaseValue"] == 5000000000
    assert candidate["nBits"] == "207fffff"
    assert candidate["time"] == 1700000000
    assert candidate["height"] == 100
    assert candidate["merkleProof"] == []


@pytest.mark.asyncio
async def test_get_mining_candidate_without_coinbase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = httpx.Request("POST", "http://127.0.0.1:8332")

    async def mock_post(
        *_args: object,
        **kwargs: object,
    ) -> httpx.Response:
        assert_rpc_request(
            kwargs,
            "getminingcandidate",
            [False],
        )

        fake_payload = {
            "result": {
                "id": "cand_002",
                "prevhash": "00" * 32,
                "version": 536870912,
                "coinbaseValue": 5000000000,
                "nBits": "207fffff",
                "time": 1700000001,
                "height": 101,
                "merkleProof": [],
            },
            "error": None,
            "id": 1,
        }

        return httpx.Response(
            200,
            json=fake_payload,
            request=req,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        mock_post,
    )

    client = BSVNodeRPCClient()
    candidate = await client.get_mining_candidate(
        provide_coinbase=False,
    )

    assert candidate["id"] == "cand_002"
    assert "coinbase" not in candidate
    assert candidate["version"] == 536870912
    assert candidate["coinbaseValue"] == 5000000000
    assert candidate["nBits"] == "207fffff"
    assert candidate["time"] == 1700000001
    assert candidate["height"] == 101
    assert candidate["merkleProof"] == []


@pytest.mark.asyncio
async def test_rpc_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = httpx.Request("POST", "http://127.0.0.1:8332")

    async def mock_post(
        *_args: object,
        **kwargs: object,
    ) -> httpx.Response:
        assert_rpc_request(
            kwargs,
            "getminingcandidate",
            [True],
        )

        fake_payload = {
            "result": None,
            "error": {
                "code": -10,
                "message": "Node is warming up",
            },
            "id": 1,
        }

        return httpx.Response(
            200,
            json=fake_payload,
            request=req,
        )

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        mock_post,
    )

    client = BSVNodeRPCClient()

    with pytest.raises(BSVNodeRPCError) as exc_info:
        await client.get_mining_candidate()

    assert exc_info.value.code == -10
    assert "warming up" in exc_info.value.message
```
