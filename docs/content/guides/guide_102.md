# Nested Command-Line Applications with Clak

This guide explores advanced features of Clak, focusing on nested commands and complex command-line structures. We'll learn how to build sophisticated command-line applications with subcommands, similar to tools like `git` or `docker`.

## Nested Commands Basics

Nested commands (also known as subcommands) allow you to create hierarchical command-line interfaces. Let's start with a basic example:

``` python title="script3.py" linenums="1"
--8<-- "examples/script3.py"
```

1. Create a first sublevel `Parser` class.
   * Like root `Parser`, it must inherit from `Parser`.
2. Specific options `force` for only this subcommand
3. Define `cli_run()` method, this method will be executed when the subcommand is run.
4. Create second subcommand `Parser` class.
   * Like root `Parser`, it must inherit from `Parser`.
5. Define specific options for this subcommand
6. Define `cli_run()` method, this method will be executed when the subcommand is run.
7. Create main top level `Parser` class.
   * It must inherit from `Parser`.
   * Define global options for the application
   * Will contains our two subcommands
8. Top level options
   * Define global options for the application
   * Options will be accessible by the subcommands
9. Bind subcommand `AppCommand1` to the main parser
   * Use `Command` class to bind subcommands to the main parser
   * It use internal `argparse` subparser to handle subcommands
10. Bind subcommand `AppCommand2` to the main parser

This example demonstrates:

1. A main parser (`AppMain`) with global options
2. Two subcommands (`command1` and `command2`)
3. Each subcommand with its own arguments and behavior

Usage:

=== "Main help message"

    The main help message is:

    ``` raw linenums="0"
    $ ./script3.py --help
    usage: script3.py [-h] [--debug] [--config CONFIG] {command1,command2} ...

    Demo application with options and two subcommands.

    positional arguments:

    subcommands:
      command1                  Execute command 1
      command2                  Execute command 2

    options:
      -h, --help                  show this help message and exit
      --debug                     Enable debug mode (default: False)
      --config CONFIG, -c CONFIG  Config file path (default: config.yaml)
    ```

=== "Command1 help message"


    While `command1` help message is:

    ``` raw linenums="0"
    $ ./script3.py command1 --help
    usage: script3.py command1 [-h] [--force]

    Command 1, which says hello

    options:
      -h, --help   show this help message and exit
      --force, -f  Force (default: False)
    ```


=== "Command2 help message"


    And `command2` help message is:

    ``` raw linenums="0"
    $ ./script3.py command2 --help
    usage: script3.py command2 [-h] [--alias ALIASES] NAME

    Command 2, with option and positional arguments

    positional arguments:
      NAME                        Name

    options:
      -h, --help                  show this help message and exit
      --alias ALIASES, -a ALIASES
                                  Alias (default: None)

    ```

Usage examples:

``` raw linenums="0"
# Using command1
python script3.py command1 --force

# Using command2
python script3.py command2 --alias nickname1 --alias nickname2 John
```

## Deep Nested Commands

For more complex applications, you might need multiple levels of commands.
Let's say we want to create a command structure like:

``` raw linenums="0"
app
└── command1
    ├── sub1
    └── sub2
        ├── sub2a
        └── sub2b
```

Here's how to implement deeper command hierarchies:

```python title="script4.py" linenums="1"
--8<-- "examples/script4.py"
```

The help message is now:

``` raw linenums="0"
$ ./script4.py --help
usage: script4.py [-h] [--debug] [--config CONFIG] {command1} ...

Demo application with deep nested commands

positional arguments:

subcommands:
  command1                  Execute command 1                        
  command1 sub1             SubCommand1                              
  command1 sub2             SubCommand2                              
  command1 sub2 sub2a       SubSubCommand2a                          
  command1 sub2 sub2b       SubSubCommand2b                          

options:
  -h, --help                  show this help message and exit
  --debug                     Enable debug mode (default: False)
  --config CONFIG, -c CONFIG  Config file path (default: config.yaml)
```

Usage examples:

``` raw linenums="0"
# Using top-level command
python script.py command1 John

# Using nested command
python script.py command1 sub2 sub2a arg1 arg2

# Using global options with nested commands
python script.py --debug command1 sub2 sub2a arg1 arg2
```

## Next Steps

After mastering nested commands, you can explore:

* Command plugins and dynamic loading
* Custom argument types
* Command aliases
* Shell completion
* Configuration file integration
* Interactive command modes

Remember that well-designed command-line interfaces make your tools more user-friendly and maintainable. Take time to plan your command hierarchy and argument structure before implementation.
