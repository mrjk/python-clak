"Argparse Improved Formatter classes"
import argparse

class RecursiveHelpFormatter(argparse.HelpFormatter):
    """A recursive help formatter to help command discovery."""

    def _format_action(self, action):
        if not isinstance(action, argparse._SubParsersAction):
            return super()._format_action(action)

        # Get the original format parts
        parts = ['\nCommands available:\n']
        parts = []
        bullet: str = '  '
        
        def add_subparser_to_parts(parser: argparse.ArgumentParser, prefix: str = '', level: int = 0, indent: str = ".."):
            _indent = indent * level
            
            for act in parser._actions:
                if isinstance(act, argparse._SubParsersAction):
                    for subaction in act._choices_actions:
                        choice = act.choices[subaction.dest]
                        cmd = f"{prefix}{subaction.dest}"
                        parts.append(f"{_indent}{bullet}{cmd:<30} {subaction.help or ''}\n")
                        add_subparser_to_parts(choice, prefix=f"{cmd} ", level=level + 1, indent=indent)

        # Format all commands with alignment
        for subaction in action._choices_actions:
            choice = action.choices[subaction.dest]
            parts.append(f"{bullet}{subaction.dest:<30} {subaction.help or ''}\n")
            add_subparser_to_parts(choice, prefix=f"{subaction.dest} ", level=1, indent="")

        return ''.join(parts)

