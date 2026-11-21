"""HTTP API mixins: serve a clak command tree over HTTP (POC).

- :class:`ApiServerMixin` goes on the **root** app. It discovers the commands
  to expose, runs them on request and starts a server through a pluggable
  *driver* (``fastapi`` ships first; register others in ``API_DRIVERS``).
- :class:`ApiEndpointMixin` goes on each **command** to expose (opt-in).
- :class:`ApiServeCmd` is a ready-made ``serve`` subcommand.

Mapping: ``app users add`` becomes ``POST /users/add``. The JSON body is a
dict of argument ``dest`` -> value, the response is the command's return
value as JSON. Validation is done by the command's own argparse parser.

Example::

    class Add(ApiEndpointMixin, Parser):
        name = Argument("name")
        def cli_run(self, ctx, **_):
            return {"added": ctx.args.name}

    class App(ApiServerMixin, Parser):
        add = Command(Add)
        serve = Command(ApiServeCmd)

Settings (``Meta``): ``api_host``, ``api_port``, ``api_driver``,
``api_auth_user``, ``api_auth_password``, ``api_docs`` (basic auth when both are set),
and ``api_path`` on an endpoint to override its URL path.
"""

import argparse
import json
import logging
import secrets
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from clak import _optional
from clak.core.descriptors import Argument, MetaSetting
from clak.core.parser import Parser
from clak.exception import ClakParseError, ClakUserError
from clak.views.serialize import dump_json

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class ApiError(Exception):
    """Error raised while serving a request; carries the HTTP status."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class ApiRoute:
    """One exposed command."""

    path: str  # URL path, e.g. "/users/add"
    node: Any  # leaf command node
    tokens: List[str]  # argv tokens leading to the node, e.g. ["users", "add"]


@dataclass
class ApiAuth:
    """Basic auth credentials."""

    user: str
    password: str

    def check(self, user: str, password: str) -> bool:
        """Constant-time credentials check."""
        ok_user = secrets.compare_digest(user.encode(), self.user.encode())
        ok_pass = secrets.compare_digest(password.encode(), self.password.encode())
        return ok_user and ok_pass


# Drivers
# ============================


class ApiDriver:
    """HTTP backend. Subclass and register in :data:`API_DRIVERS`.

    ``build`` returns a backend app; each request must call
    ``server.api_call(route, body)`` and translate :class:`ApiError`.
    """

    def build(
        self,
        server: "ApiServerMixin",
        routes: List[ApiRoute],
        auth: Optional[ApiAuth],
        docs: bool = True,
    ) -> Any:
        """Create the backend application object."""
        raise NotImplementedError

    def run(self, app: Any, host: str, port: int) -> None:
        """Serve *app* (blocking)."""
        raise NotImplementedError


class FastApiDriver(ApiDriver):
    """FastAPI + uvicorn driver (extra: ``mrjk.clak[api]``)."""

    def build(self, server, routes, auth, docs=True):
        fastapi = _optional.require("fastapi", "The API server")
        # pylint: disable=import-outside-toplevel
        from fastapi import Body, Depends, FastAPI, HTTPException
        from fastapi.security import HTTPBasic, HTTPBasicCredentials

        security = HTTPBasic(auto_error=auth is not None)

        def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
            if auth is None:
                return
            if not credentials or not auth.check(
                credentials.username, credentials.password
            ):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )

        app = fastapi.FastAPI(
            title=server.query_cfg_parents("app_name", default="clak"),
            docs_url="/docs" if docs else None,
            redoc_url="/redoc" if docs else None,
            openapi_url="/openapi.json" if docs else None,
        )

        def make_handler(route):
            def handler(body: Optional[dict] = Body(default=None)):
                try:
                    return server.api_call(route, body or {})
                except ApiError as err:
                    raise HTTPException(status_code=err.status, detail=err.message)

            return handler

        for route in routes:
            app.add_api_route(
                route.path,
                make_handler(route),
                methods=["POST"],
                dependencies=[Depends(authenticate)],
                summary=" ".join(route.tokens),
            )
        return app

    def run(self, app, host, port):
        uvicorn = _optional.require("uvicorn", "The API server")
        config = uvicorn.Config(app, host=host, port=port)  # sets up logging
        log = logging.getLogger("uvicorn.error")
        base = f"http://{host}:{port}"
        for route in app.routes:
            if getattr(route, "methods", None) and route.path not in (
                "/docs",
                "/redoc",
                "/openapi.json",
                "/docs/oauth2-redirect",
            ):
                methods = ",".join(sorted(route.methods))
                log.info("Endpoint: %s %s%s", methods, base, route.path)
        for label, url in (
            ("Swagger UI", app.docs_url),
            ("ReDoc", app.redoc_url),
            ("OpenAPI spec", app.openapi_url),
        ):
            if url:
                log.info("%s: %s%s", label, base, url)
        if not app.openapi_url:
            log.info("API docs are disabled")
        uvicorn.Server(config).run()


API_DRIVERS: Dict[str, type] = {"fastapi": FastApiDriver}


# Mixins
# ============================


class ApiEndpointMixin:  # pylint: disable=too-few-public-methods
    """Mark a command as exposed by the API server (opt-in)."""

    meta__config__api_path = MetaSetting(help="Override the URL path of this endpoint")


def _iter_nodes(node):
    for child in node.children.values():
        yield child
        yield from _iter_nodes(child)


def _body_to_argv(parser: argparse.ArgumentParser, body: dict) -> List[str]:
    """Turn ``{dest: value}`` into argv tokens using the parser's actions."""
    # pylint: disable=protected-access
    actions = {a.dest: a for a in parser._actions}
    unknown = set(body) - set(actions)
    if unknown:
        raise ClakParseError(f"Unknown argument(s): {', '.join(sorted(unknown))}")

    argv: List[str] = []
    for dest, value in body.items():
        action = actions[dest]
        flag = action.option_strings[0] if action.option_strings else None
        if action.nargs == 0:  # store_true / store_false / count / ...
            if value:
                argv.extend([flag] * (value if isinstance(value, int) and value > 1 else 1))
            continue
        values = value if isinstance(value, list) else [value]
        if flag is None:
            argv.extend(str(v) for v in values)
        elif action.nargs in (None, "?"):
            for v in values:  # repeatable for append actions
                argv.extend([flag, str(v)])
        else:
            argv.append(flag)
            argv.extend(str(v) for v in values)
    return argv


class ApiServerMixin:
    """Root mixin: route discovery, request execution, server start."""

    meta__config__api_host = MetaSetting(help=f"Listen address ({DEFAULT_HOST})")
    meta__config__api_port = MetaSetting(help=f"Listen port ({DEFAULT_PORT})")
    meta__config__api_driver = MetaSetting(help="HTTP backend name (fastapi)")
    meta__config__api_auth_user = MetaSetting(help="Basic auth user")
    meta__config__api_auth_password = MetaSetting(help="Basic auth password")
    meta__config__api_docs = MetaSetting(
        help="Serve Swagger UI, ReDoc and OpenAPI spec (default: true)"
    )

    _api_lock = threading.Lock()

    def api_routes(self) -> List[ApiRoute]:
        """Endpoints below this node (commands including ApiEndpointMixin)."""
        routes = []
        for node in _iter_nodes(self):
            if not isinstance(node, ApiEndpointMixin):
                continue
            tokens = [n.key for n in node.get_hierarchy()[1:]]
            path = node.query_cfg_parents("api_path", default=None)
            routes.append(ApiRoute(path or "/" + "/".join(tokens), node, tokens))
        return routes

    def api_call(self, route: ApiRoute, body: dict) -> Any:
        """Run one command and return JSON-able data (raises ApiError)."""
        if not isinstance(body, dict):
            raise ApiError(422, "Body must be a JSON object")
        try:
            argv = route.tokens + _body_to_argv(route.node.parser, body)
            args = self.parser.parse_args(argv).__dict__
            # ctx lives on the root node: serialize requests (POC)
            with self._api_lock:
                data = self.cli_execute(args=args)
        except argparse.ArgumentError as err:
            raise ApiError(422, str(err)) from err
        except ClakParseError as err:
            raise ApiError(422, str(err)) from err
        except ClakUserError as err:
            raise ApiError(400, str(err)) from err
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.exception("API command failed")
            raise ApiError(500, f"{err.__class__.__name__}: {err}") from err
        return json.loads(dump_json(data))

    def api_auth(self, user=None, password=None) -> Optional[ApiAuth]:
        """Credentials from arguments or Meta; None disables auth."""
        user = user or self.query_cfg_parents("api_auth_user", default=None)
        password = password or self.query_cfg_parents(
            "api_auth_password", default=None
        )
        if bool(user) != bool(password):
            raise ClakUserError("Basic auth needs both a user and a password")
        return ApiAuth(user, password) if user else None

    def api_app(self, auth: Optional[ApiAuth] = None, docs: Optional[bool] = None) -> Any:
        """Build the backend app (useful for tests or external servers)."""
        name = self.query_cfg_parents("api_driver", default="fastapi")
        if name not in API_DRIVERS:
            raise ClakUserError(
                f"Unknown API driver: {name}", advice=f"Available: {list(API_DRIVERS)}"
            )
        if docs is None:
            docs = self.query_cfg_parents("api_docs", default=True)
        return API_DRIVERS[name]().build(self, self.api_routes(), auth, docs)

    def api_serve(
        self, host=None, port=None, auth: Optional[ApiAuth] = None, docs=None
    ):
        """Start the server (blocking)."""
        host = host or self.query_cfg_parents("api_host", default=DEFAULT_HOST)
        port = int(port or self.query_cfg_parents("api_port", default=DEFAULT_PORT))
        name = self.query_cfg_parents("api_driver", default="fastapi")
        app = self.api_app(auth if auth is not None else self.api_auth(), docs=docs)
        API_DRIVERS[name]().run(app, host, port)


class ApiServeCmd(Parser):
    """Start the HTTP API server (parent app must use ApiServerMixin)."""

    host = Argument("--host", default=None, help="Listen address")
    port = Argument("--port", type=int, default=None, help="Listen port")
    auth_user = Argument("--auth-user", default=None, help="Basic auth user")
    auth_password = Argument(
        "--auth-password", default=None, help="Basic auth password"
    )
    docs = Argument(
        "--docs",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Serve Swagger UI and OpenAPI spec (default: enabled)",
    )

    def cli_run(self, ctx, **_):
        root = ctx.cli_root
        if not isinstance(root, ApiServerMixin):
            raise ClakUserError("The root command must include ApiServerMixin")
        args = ctx.args
        root.api_serve(
            host=args.host,
            port=args.port,
            auth=root.api_auth(args.auth_user, args.auth_password),
            docs=args.docs,
        )
