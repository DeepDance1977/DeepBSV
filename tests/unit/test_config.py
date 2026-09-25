from deepbsv.core.config import Settings


def test_default_settings():
    settings = Settings(
        BSV_RPC_HOST="127.0.0.1",
        BSV_RPC_PORT=8332,
        _env_file=None
    )
    assert settings.rpc_host == "127.0.0.1"
    assert settings.rpc_port == 8332
    assert settings.rpc_url == "http://127.0.0.1:8332"
