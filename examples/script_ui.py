#!/usr/bin/env python3
"""Demo: interactive components from clak.ui (prompts, confirm, continue, wait).

Try:
  ./script_ui.py
  echo -e "ada\n3\n2\ny\n\n" | ./script_ui.py   # piped answers
"""

from clak.ui import (
    ChoicePrompt,
    ConfirmPrompt,
    ContinuePrompt,
    TextPrompt,
    UIAbort,
    WaitSpinner,
    prompt_text,
)


def main():
    try:
        name = prompt_text("Your name", default="anonymous")
        age = TextPrompt("Age", cast=int, validate=lambda v: v > 0).ask()
        role = ChoicePrompt("Pick a role", ["admin", "dev", "guest"], default="dev").ask()

        if not ConfirmPrompt(f"Create {name} ({age}) as {role}?", default=True).ask():
            print("Cancelled.")
            return 1

        with WaitSpinner("Creating user"):
            import time

            time.sleep(1)

        if not ContinuePrompt("Press Enter to show the result, q to quit").ask():
            return 0
        print({"name": name, "age": age, "role": role})
    except UIAbort as err:
        print(f"Aborted: {err}")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
