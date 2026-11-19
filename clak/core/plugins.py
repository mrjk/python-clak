"""Plugin conventions for Parser mixins.

A mixin contributes behavior by defining ``cli_hook__<name>(self, instance,
ctx, **_)`` methods. ``ParserNode`` collects them at build time and the
dispatcher runs them for every node of the command path, before
``cli_group`` / ``cli_run``. Read configuration from ``instance`` (the node
being walked) so a subcommand's ``Meta`` wins.
"""

CLI_HOOK_PREFIX = "cli_hook__"
