#!/usr/bin/env python3
"""Serve a CLI over HTTP with ApiServerMixin / ApiEndpointMixin.

Needs the ``api`` extra: pip install 'mrjk.clak[api]'

Try:
    ./script_api.py users add bob --count 2
    ./script_api.py serve --port 8000 --auth-user me --auth-password secret
    curl -u me:secret -X POST localhost:8000/users/add \
        -H 'content-type: application/json' -d '{"name": "bob", "count": 2}'
"""

from clak import (
    ApiEndpointMixin,
    ApiServeCmd,
    ApiServerMixin,
    Argument,
    Command,
    Parser,
)


class UsersAdd(ApiEndpointMixin, Parser):
    "Add a user"

    name = Argument("name", help="User name")
    count = Argument("--count", type=int, default=1)

    def cli_run(self, ctx, **_):
        return {"added": ctx.args.name, "count": ctx.args.count}


class Users(Parser):
    "Manage users"

    add = Command(UsersAdd)


class AppMain(ApiServerMixin, Parser):
    "Demo app"

    users = Command(Users)
    serve = Command(ApiServeCmd)


if __name__ == "__main__":
    AppMain()
