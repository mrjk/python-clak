#!/usr/bin/env python3
"""Demo: list users with ListViewMixin and CLI column control."""

from clak import Argument, ListViewMixin, Parser


class AppMain(ListViewMixin, Parser):
    """List demo users as a table.

    Try:
      ./script_views.py
      ./script_views.py --columns name,role
      ./script_views.py --add-index
      ./script_views.py --columns name --no-expand-keys
    """

    class Meta:
        # True = all flags, False = none, or a subset like ("columns",)
        view_cli_options = True

    role = Argument("--role", help="Filter by role")

    def cli_run(self, role=None, **_):
        users = [
            {"name": "ada", "role": "admin", "city": "London"},
            {"name": "linus", "role": "dev", "city": "Helsinki"},
            {"name": "grace", "role": "dev", "city": "New York"},
        ]
        if role:
            users = [user for user in users if user["role"] == role]
        return users


if __name__ == "__main__":
    AppMain()
