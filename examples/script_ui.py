#!/usr/bin/env python3
"""Demo: clak.ui components with RuntimeOptMixin (attended vs unattended).

Try:
  ./script_ui.py --help
  ./script_ui.py                           # prompts on a terminal
  ./script_ui.py --no-input                # defaults only, fails if a value is missing
  ./script_ui.py --no-input --name ada --yes
  ./script_ui.py --interactive=never --name ada --yes
  printf 'ada\n30\n2\ny\n\n' | ./script_ui.py --interactive=always
  CI=1 ./script_ui.py                      # CI => never, like --no-input
  CI=1 ./script_ui.py --interactive=auto   # explicit auto still sees CI
  ./script_ui.py --no-input --name ada --delete   # dangerous: needs --yes
"""

import time

from clak import Argument, Parser, RuntimeOptMixin
from clak.comp.runtime import ui_session


class AppMain(RuntimeOptMixin, Parser):
    """Create a user, asking only for what was not given."""

    name = Argument("--name", help="User name (prompted when missing)")
    role = Argument("--role", help="User role (prompted when missing)")
    delete = Argument("--delete", action="store_true", help="Also run a dangerous step")

    def cli_run(self, ctx, name=None, role=None, delete=False, **_):
        ui = ui_session(ctx)

        name = name or ui.text("Your name", default="anonymous")
        role = role or ui.choice("Pick a role", ["admin", "dev", "guest"], default="dev")

        if not ui.confirm(f"Create {name} as {role}?", default=True):
            print("Cancelled.")
            return 1

        if delete and not ui.confirm("Delete all previous users?", dangerous=True):
            print("Kept previous users.")

        with ui.spinner("Creating user"):
            time.sleep(0.5)

        ui.pause("Press Enter to show the result, q to quit")
        print({"name": name, "role": role, "interactive": ctx.interactive})
        return 0


if __name__ == "__main__":
    AppMain()
