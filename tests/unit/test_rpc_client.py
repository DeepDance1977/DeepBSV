import pytest
import httpx
from deepbsv.core.config import Settings
from deepbsv.rpc.client import BSVRPCClient
from deepbsv.rpc.exceptions import (
    BSVRPCAuthenticationError,
    BSVRPCConnectionError,
    BSVRPCResponseError,
)
from tests.mocks.rpc_responses import RPC_ERROR_RESPONSE, VALID_GETMININGCANDIDATE_RESPONSE


@pytest.fixture
def dummy_settings():
    return Settings(
        BSV_RPC_HOST="localhost",
        BSV_RPC_PORT=8332,
        BSV_RPC_USER="user",
        BSV_RPC_PASSWORD="pass",
        _env_file=None,
    )


@pytest.mark.asyncio
async def test_get_mining_candidate_success(httpx_mock, dummy_settings):
    httpx_mock.add_response(
        url=dummy_settings.rpc_url,
        json={"result": VALID_GETMININGCANDIDATE_RESPONSE, "error": None, "id": "deepbsv"},
        status_code=200,
    )

    client = BSVRPCClient(dummy_settings)
    candidate = await client.get_mining_candidate()
    await client.close()

    assert candidate.id == "cand_00112233445566778899"
    assert candidate.height == 820000


@pytest.mark.asyncio
async def test_rpc_auth_error(httpx_mock, dummy_settings):
    httpx_mock.add_response(url=dummy_settings.rpc_url, status_code=401)

    client = BSVRPCClient(dummy_settings)
    with pytest.raises(BSVRPCAuthenticationError):
        await client.get_mining_candidate()
    await client.close()


@pytest.mark.asyncio
async def test_rpc_connection_error(httpx_mock, dummy_settings):
    httpx_mock.add_exception(httpx.RequestError("Connection refused"))

    client = BSVRPCClient(dummy_settings)
    with pytest.raises(BSVRPCConnectionError):
        await client.get_mining_candidate()
    await client.close()


@pytest.mark.asyncio
async def test_rpc_response_error(httpx_mock, dummy_settings):
    httpx_mock.add_response(url=dummy_settings.rpc_url, json=RPC_ERROR_RESPONSE, status_code=200)

    client = BSVRPCClient(dummy_settings)
    with pytest.raises(BSVRPCResponseError) as exc_info:
        await client.get_mining_candidate()
    await client.close()

    assert exc_info.value.code == -10
