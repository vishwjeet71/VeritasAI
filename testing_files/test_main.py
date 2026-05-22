import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app, users_info
client = TestClient(app)


# SETUP ROUTE TESTS 

def test_setup_user_success():
    response = client.post(
        "/api/setup",
        json={"userid": "testuser"}
    )

    assert response.status_code == 200
    assert response.json() == {"testuser": "setup done"}

    assert "testuser" in users_info
    assert users_info["testuser"]["user_groq"] is None


# UPDATE USER TESTS

def test_update_user_success():
    users_info["updateuser"] = {
        "user_groq": None,
        "user_SerperDev": None,
        "user_model": MagicMock()
    }

    response = client.post(
        "/api/update",
        json={
            "userid": "updateuser",
            "usergroq": "groq-key",
            "user_SerperDev": "serper-key"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"updateuser": "update done"}

    assert users_info["updateuser"]["user_groq"] == "groq-key"
    assert users_info["updateuser"]["user_SerperDev"] == "serper-key"


def test_update_user_not_found():
    response = client.post(
        "/api/update",
        json={
            "userid": "unknown",
            "usergroq": "abc",
            "user_SerperDev": "xyz"
        }
    )

    assert response.status_code == 404
    assert response.json() == {"unknown": "user not found"}


# CHECK ROUTE TESTS

@patch("main.groq.Groq")
def test_check_input_with_fallback_env(mock_groq):
    mock_model = MagicMock()
    mock_model.input_handler.return_value = {
        "result": "processed"
    }

    users_info["checkuser"] = {
        "user_groq": None,
        "user_SerperDev": None,
        "user_model": mock_model
    }

    response = client.post(
        "/api/check",
        json={
            "userid": "checkuser",
            "input": "test input"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"result": "processed"}

    mock_model.input_handler.assert_called_once_with("test input")
    mock_groq.assert_called_once()


@patch("main.groq.Groq")
def test_check_input_with_custom_keys(mock_groq):
    mock_model = MagicMock()
    mock_model.input_handler.return_value = {
        "status": "ok"
    }

    users_info["customuser"] = {
        "user_groq": "custom-groq-key",
        "user_SerperDev": "custom-serper",
        "user_model": mock_model
    }

    response = client.post(
        "/api/check",
        json={
            "userid": "customuser",
            "input": "hello"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    assert mock_model.serperdev == "custom-serper"
    mock_groq.assert_called_with(api_key="custom-groq-key")


def test_check_input_invalid_user():
    response = client.post(
        "/api/check",
        json={
            "userid": "missinguser",
            "input": "hello"
        }
    )

    assert response.status_code == 200


# VERIFY CLAIMS TESTS

@patch("main.vc.verify_claims_batch")
def test_verify_claims(mock_verify):
    mock_verify.return_value = {
        "verified": True
    }

    response = client.post(
        "/api/verify",
        json={
            "userid": "u1",
            "claims": ["claim1", "claim2"]
        }
    )

    assert response.status_code == 200
    assert response.json() == {"verified": True}


# CLEAR API TESTS

def test_clear_api_success():
    users_info["clearuser"] = {
        "user_groq": "abc",
        "user_SerperDev": "xyz",
        "user_model": MagicMock()
    }

    response = client.post(
        "/api/clear-Api",
        json={"userid": "clearuser"}
    )

    assert response.status_code == 200

    assert users_info["clearuser"]["user_groq"] is None
    assert users_info["clearuser"]["user_SerperDev"] is None


def test_clear_api_user_not_found():
    response = client.post(
        "/api/clear-Api",
        json={"userid": "nouser"}
    )

    assert response.status_code == 404
    assert response.json() == {"nouser": "user not found"}


# DELETE USER TESTS

def test_delete_user_success():
    users_info["deleteuser"] = {
        "user_groq": None,
        "user_SerperDev": None,
        "user_model": MagicMock()
    }

    response = client.post(
        "/api/delete-user",
        json={"userid": "deleteuser"}
    )

    assert response.status_code == 200
    assert response.json() == {"deleteuser": "deleted"}

    assert "deleteuser" not in users_info


def test_delete_user_already_deleted():
    response = client.post(
        "/api/delete-user",
        json={"userid": "alreadygone"}
    )

    assert response.status_code == 200
    assert response.json() == {"alreadygone": "already deleted"}


# INPUT VALIDATION TESTS

def test_setup_missing_userid():
    response = client.post(
        "/api/setup",
        json={}
    )

    assert response.status_code == 422


def test_check_missing_input():
    response = client.post(
        "/api/check",
        json={
            "userid": "abc"
        }
    )

    assert response.status_code == 422