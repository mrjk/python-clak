"""ApiServerMixin / ApiEndpointMixin: routes, execution, auth, drivers."""

import builtins

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from clak import (  # noqa: E402
    ApiEndpointMixin,
    ApiServeCmd,
    ApiServerMixin,
    Argument,
    Command,
    Parser,
)
from clak.comp.api import API_DRIVERS, ApiAuth, ApiDriver  # noqa: E402
from clak.exception import ClakUserError  # noqa: E402

pytestmark = pytest.mark.tags("unit-tests")


class Add(ApiEndpointMixin, Parser):
    name = Argument("name")
    count = Argument("--count", type=int, default=1)
    loud = Argument("--loud", action="store_true")
    tag = Argument("--tag", action="append")

    def cli_run(self, ctx, **_):
        a = ctx.args
        return {"name": a.name, "count": a.count, "loud": a.loud, "tag": a.tag}


class Hidden(Parser):
    def cli_run(self, ctx, **_):
        return "secret"


class Boom(ApiEndpointMixin, Parser):
    def cli_run(self, ctx, **_):
        raise ClakUserError("nope")


class Users(Parser):
    add = Command(Add)


class App(ApiServerMixin, Parser):
    users = Command(Users)
    hidden = Command(Hidden)
    boom = Command(Boom)
    serve = Command(ApiServeCmd)


def client(app=None, auth=None):
    app = app or App(parse=False)
    return TestClient(app.api_app(auth))


def test_routes_are_opt_in():
    paths = sorted(r.path for r in App(parse=False).api_routes())
    assert paths == ["/boom", "/users/add"]


def test_call_ok():
    res = client().post("/users/add", json={"name": "bob", "count": 3, "loud": True})
    assert res.status_code == 200
    assert res.json() == {"name": "bob", "count": 3, "loud": True, "tag": None}


def test_append_values():
    res = client().post("/users/add", json={"name": "bob", "tag": ["a", "b"]})
    assert res.json()["tag"] == ["a", "b"]


@pytest.mark.parametrize(
    "body",
    [{"name": "bob", "count": "x"}, {}, {"name": "bob", "bogus": 1}],
)
def test_validation_errors_are_422(body):
    assert client().post("/users/add", json=body).status_code == 422


def test_user_error_is_400():
    assert client().post("/boom").status_code == 400


def test_hidden_command_not_served():
    assert client().post("/hidden").status_code == 404


def test_basic_auth():
    c = client(auth=ApiAuth("u", "p"))
    body = {"name": "bob"}
    assert c.post("/users/add", json=body).status_code == 401
    assert c.post("/users/add", json=body, auth=("u", "bad")).status_code == 401
    assert c.post("/users/add", json=body, auth=("u", "p")).status_code == 200


def test_auth_needs_both():
    with pytest.raises(ClakUserError):
        App(parse=False).api_auth(user="u")


def test_custom_driver(monkeypatch):
    seen = {}

    class Fake(ApiDriver):
        def build(self, server, routes, auth, docs=True):
            seen["routes"] = [r.path for r in routes]
            return "app"

        def run(self, app, host, port):
            seen["run"] = (app, host, port)

    class Custom(App):
        class Meta:
            api_driver = "fake"

    monkeypatch.setitem(API_DRIVERS, "fake", Fake)
    Custom(parse=False).api_serve(host="h", port=1)
    assert seen["run"] == ("app", "h", 1)
    assert "/users/add" in seen["routes"]


def test_serve_cmd_starts_driver(monkeypatch):
    calls = {}

    class Fake(ApiDriver):
        def build(self, server, routes, auth, docs=True):
            calls["auth"] = auth
            return "app"

        def run(self, app, host, port):
            calls["run"] = (host, port)

    class Custom(App):
        class Meta:
            api_driver = "fake"

    monkeypatch.setitem(API_DRIVERS, "fake", Fake)
    Custom(parse=False).dispatch(
        ["serve", "--host", "0.0.0.0", "--port", "9", "--auth-user", "u",
         "--auth-password", "p"]
    )
    assert calls["run"] == ("0.0.0.0", 9)
    assert calls["auth"].user == "u"


def test_missing_extra(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("fastapi"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ClakUserError) as exc:
        App(parse=False).api_app()
    assert "mrjk.clak[api]" in exc.value.advice


def test_docs_enabled_by_default():
    client = TestClient(App(parse=False).api_app())
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_docs_can_be_disabled():
    client = TestClient(App(parse=False).api_app(docs=False))
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.post("/users/add", json={"name": "x"}).status_code == 200
