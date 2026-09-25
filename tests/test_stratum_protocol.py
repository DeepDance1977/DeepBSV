import json
import pytest
from deepbsv.stratum.protocol import StratumProtocolHandler, StratumSession, StratumError


@pytest.fixture
def session():
    return StratumSession(session_id="abcdef1234567890")


@pytest.fixture
def handler():
    return StratumProtocolHandler()


def test_session_initialization(session):
    assert session.session_id == "abcdef1234567890"
    assert not session.is_subscribed
    assert not session.is_authorized
    assert session.worker_name is None


def test_parse_valid_json(handler):
    raw = '{"id": 1, "method": "mining.subscribe", "params": []}'
    data = handler.parse_message(raw)
    assert data["id"] == 1
    assert data["method"] == "mining.subscribe"


def test_parse_invalid_json(handler):
    raw = '{"id": 1, "method": invalid}'
    with pytest.raises(StratumError) as exc_info:
        handler.parse_message(raw)
    assert exc_info.value.code == -32700


def test_handle_subscribe(handler, session):
    req = {
        "id": 1,
        "method": "mining.subscribe",
        "params": ["cgminer/4.10.0"]
    }
    response = handler.handle_request(session, req)

    assert response["id"] == 1
    assert response["error"] is None
    assert session.is_subscribed is True
    assert session.extranonce1 == "abcdef12"
    assert response["result"][1] == "abcdef12"
    assert response["result"][2] == 4


def test_handle_authorize(handler, session):
    req = {
        "id": 2,
        "method": "mining.authorize",
        "params": ["user.worker1", "password"]
    }
    response = handler.handle_request(session, req)

    assert response["id"] == 2
    assert response["result"] is True
    assert session.is_authorized is True
    assert session.worker_name == "user.worker1"


def test_handle_submit_unauthorized(handler, session):
    req = {
        "id": 3,
        "method": "mining.submit",
        "params": ["user.worker1", "job1", "00000000", "5f1b2c3d", "12345678"]
    }
    response = handler.handle_request(session, req)

    assert response["id"] == 3
    assert response["result"] is None
    assert response["error"]["code"] == 24
    assert "Unauthorized" in response["error"]["message"]


def test_handle_submit_authorized(handler, session):
    session.authorize("user.worker1")
    req = {
        "id": 3,
        "method": "mining.submit",
        "params": ["user.worker1", "job1", "00000000", "5f1b2c3d", "12345678"]
    }
    response = handler.handle_request(session, req)

    assert response["id"] == 3
    assert response["result"] is True
    assert response["error"] is None


def test_handle_unknown_method(handler, session):
    req = {
        "id": 4,
        "method": "mining.unknown_method",
        "params": []
    }
    response = handler.handle_request(session, req)

    assert response["id"] == 4
    assert response["result"] is None
    assert response["error"]["code"] == -32601


def test_create_notification(handler):
    notification = handler.create_notification("mining.set_difficulty", [8])
    assert notification["id"] is None
    assert notification["method"] == "mining.set_difficulty"
    assert notification["params"] == [8]
