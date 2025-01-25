
from pprint import pprint

from clak import ArgumentParserPlus, Argument, Command


################################################################################

# class GitConfig(ArgumentParserPlus):

#     arguments_dict =[
#         Fn('--repo', help='Repository path'),
#         Fn('--remote', help='Remote name'),
#     ]

# class DBConfig(ArgumentParserPlus):

#     arguments_dict =[
#         Fn('--db', help='Database name'),
#         Fn('--user', help='Database user'),
#         Fn('--password', help='Database password'),
#     ]



class ProcessShow(ArgumentParserPlus):

    target_pid = Argument('--target-pid', '-p', help='Target Process ID')
    target_name = Argument('--target-name', '-n', help='Target Process name')

    arguments_dict = {
        'format': Argument('--format', choices=['json', 'text'], help='Output format'),
        'verbose': Argument('-v', '--verbose', action='store_true', help='Show verbose output')
    }

class ProcessKillOne(ArgumentParserPlus):

    kill_pid = Argument("--fff", help='Process ID to kill')
    kill_name = Argument("--ffu", help='Process name to kill')

    arguments_dict = {
        'force': Argument('-f', '--force', action='store_true', help='Force kill without confirmation'),
        'timeout': Argument('--timeout', type=int, default=5, help='Kill timeout in seconds')
    }

class ProcessKillAll(ArgumentParserPlus):

    kill_pid = Argument('--kill-pid', help='Process ID to kill')
    kill_name = Argument('--kill-name', help='Process name to kill')

    arguments_dict = {
        'force': Argument('-f', '--force', action='store_true', help='Force kill without confirmation'),
        'exclude': Argument('--exclude', help='Exclude processes matching pattern')
    }

class ProcessKill(ArgumentParserPlus):

    # kill_pid = Argument('--kill-pid', help='Process ID to kill')
    # kill_name = Argument('--kill-name', help='Process name to kill')

    arguments_dict = {
        'signal': Argument('--signal', '-s', default='SIGTERM', help='Signal to send'),
        'dry_run': Argument('--dry-run', action='store_true', help='Show what would be killed')
    }
    
    # Commands as attributes
    # one = Command(ProcessKillOne)
    # all = Command(ProcessKillAll)
    
    # Additional commands in children dict
    children = {
        'group': Command(ProcessKillAll, help='Kill a group of processes'),
        'tree': Command(ProcessKillOne, help='Kill process tree')
    }

class Process(ArgumentParserPlus):

    sort_field = Argument('--sort-field', help='Sort by field')
    filter_field = Argument('--filter-field', help='Filter by field')

    arguments_dict = {
        'output': Argument('--output', '-o', choices=['table', 'json', 'csv'], help='Output format'),
        'columns': Argument('--columns', help='Columns to display')
    }
    
    # Commands as attributes
    kill2 = Command(ProcessKill, help='Kill a process YOOOO')
    show2 = Command(ProcessShow)
    
    # Additional commands in children dict
    children = {
    
        'kill': Command(ProcessKill),
        'show': Command(ProcessShow),

    }



class MainConfig(ArgumentParserPlus):

    global_custom = Argument('--global-custom', help='My custom argument')
    global_custom2 = Argument('--global-custom2', help='My custom argument2')

    arguments_dict = {
        'config': Argument('--config', '-C', help='Config file path'),
        # 'debug': Argument('--debug', action='store_true', help='Enable debug mode')
        'debug': Argument(action='store_true', help='Enable debug mode')
    }

    # Commands as attributes
    # process = Command(Process)
    
    # Additional commands in children dict
    children = {
        'system': Command(Process, help='System-wide process operations'),
        # 'user': Command(Process, help='User process operations'),
        # 'service': Command(Process, help='Service process operations')
    }



# def main2():
parser = MainConfig()
args = parser.parse_args()
pprint(args.__dict__)


# This should display:
# pylint: disable-next=pointless-string-statement
"""
$ python examples/demo1.py --help

usage: demo1.py [-h] [--config CONFIG] [--debug] [--global-custom GLOBAL_CUSTOM] [--global-custom2 GLOBAL_CUSTOM2]
                {system} ...

positional arguments:
  system                         
  system kill                    System-wide process operations
  system kill group              
  system kill tree               
  system show                    System-wide process operations
  system kill2                   System-wide process operations
  system kill2 group             Kill a process YOOOO
  system kill2 tree              Kill a process YOOOO
  system show2                   System-wide process operations

options:
  -h, --help            show this help message and exit
  --config CONFIG, -C CONFIG
                        Config file path
  --debug               Enable debug mode
  --global-custom GLOBAL_CUSTOM
                        My custom argument
  --global-custom2 GLOBAL_CUSTOM2
                        My custom argument2

"""