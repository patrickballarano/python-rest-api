from app import app
import pytest


@pytest.fixture()
def app():
    app = app()
    app.config.update(
        {
            "TESTING": True,
        }
    )

    # other setup can go here

    yield app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()


def test_request_example(client):
    response = client().get("/")
    # resp_test = '{"date": "1666735082","kubernetes": "false","version": "1.0.0"}'
    assert response.status_code == 200
    # assert resp_test in response.data


def test_history(client):
    response = client().get("/v1/history")
    assert response.status_code == 200


def test_lookup_validate(client):
    # test post call /v1/lookup/validate
    response = client().post("/v1/lookup/validate", json={"ip": "0.0.0.0"})
    assert response.status_code == 200
