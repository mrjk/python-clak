# Getting Started with Clak

This guide will walk you through the basics of building command-line applications using Clak. We'll start with a minimal example and gradually explore more advanced features.

## Base Concepts

Clak is a Python library that simplifies the creation of command-line applications by providing an elegant, class-based interface on top of Python's `argparse`. The main components are:

- `Parser`: The base class for your application
- `Argument`: Class to define command-line arguments
- `Command`: (Not shown in basic examples) Used for subcommands

## Minimal Example

Let's start with a minimal example called `script1.py`, that demonstrates the core concepts:


``` python title="script1.py" linenums="1"
--8<-- "examples/script1.py"
```

1. Import `Parser` and `Argument` from `clak`.
2. Root parser class — must inherit from `Parser`.
3. Class docstring becomes the application help description.
4. Optional argument (`--` / `-`); same kwargs as `argparse.add_argument()`.
5. Positional argument (name without `-` / `--`).
6. `cli_run()` runs when the command is invoked; parameters match destinations.
7. `cli_exit(1)` sets a non-zero exit code (see [Parser API](../api/parser.md)).
8. Instantiating the root parses argv and runs the command (auto-`dispatch()`).

From this example, run it with the Python interpreter. Clak adds `-h` / `--help` automatically:

``` raw linenums="0"
$ python script1.py --help
usage: script1.py [-h] [--config CONFIG] [NAME]

Demo application with two arguments.

positional arguments:
  NAME                        First Name (default: None)

options:
  -h, --help                  show this help message and exit
  --config CONFIG, -c CONFIG  Config file path (default: config.yaml)
```

Thus, we can try to call it:

``` raw linenums="0"
$ python script1.py
No name provided, please provide a name as first argument.

$ python script1.py John
Store name 'John' in config file: config.yaml

$ python script1.py John Doe
usage: script1.py [-h] [--config CONFIG] [NAME]
script1.py: error: unrecognized arguments: Doe
```

It is also possible to run directly if you make your script executable:

``` raw linenums="0"
$ chmod +x script1.py

# You can directly run it
$ ./script1.py --help
$ ./script1.py
$ ./script1.py John
$ ./script1.py John Doe
```

This example shows:

1. Creating a basic application class that inherits from Parser
2. Defining two arguments:
   - An optional `--config` argument with a default value
   - A positional `NAME` argument that's optional (`nargs="?"`)
3. Implementing the `cli_run` method that receives the parsed arguments


## Advanced Arguments Example

Let's update our previous example with more fields:

```python title="script2.py" linenums="1"
--8<-- "examples/script2.py"
```

1. Import `Parser` and `Argument` classes from clak

2. **Boolean Flags** (`force`):
   - Uses `action="store_true"` to create a flag
   - No value needed, just presence/absence
   - Use both long and short form

3. **String Options** (`config`):
   - Basic string argument with default value
   - Can be specified with `-c`
   - Use short form only

4. **Choice Options** (`color`):
   - Restricts input to predefined choices
   - Provides validation out of the box
   - Can be specified with `--color`
   - Use long form only

5. **List Arguments** (`items`):
   - Uses `action="append"` to collect multiple values
   - Can be specified multiple times: `-m item1 -m item2`

6. **Positional Arguments**:
   - Required (`name`): Must be provided

7. **Optional Positional Arguments** (`surname`):
   - Optional with default (`surname`): Uses `nargs="?"` and `default`

8. **Variable number of arguments** (`aliases`):
   - Variable number (`aliases`): Uses `nargs="*"` for zero or more

9. **Run method** (`cli_run`):
   - This method is executed when the command is run.
   - It receives the parsed arguments as keyword arguments.
   - You can directly use them in your code.

9. **Instantiate App** (`AppMain`):
   - Instantiating the root starts parsing and runs the matched command

When executed with `-h` or `--help`:

``` raw linenums="0"
$ python script2.py -h
usage: script2.py [-h] [--force] [-c CONFIG] [--color {red,green,blue,unknown}] [--items ITEMS]
                  NAME [SURNAME] [ALIAS ...]

Demo application with many arguments.

positional arguments:
  NAME                        First Name
  SURNAME                     Last Name (default: Doe)
  ALIAS                       Aliases (default: ['Bond', 'agent 007'])

options:
  -h, --help                  show this help message and exit
  --force, -f                 Force mode (default: False)
  -c CONFIG                   Config file path (default: config.yaml)
  --color {red,green,blue,unknown}
                              Favorite color (default: unknown)
  --items ITEMS, -m ITEMS     Preferred items (default: None)

```

### Example Usage

``` raw linenums="0"
# Basic usage
python script2.py John Smith

# With options
python script2.py --force --config custom.yaml John Smith

# With color choice
python script2.py --color red John Smith

# With multiple items
python script2.py --items apple --items banana John Smith

# With aliases
python script2.py John Smith nickname1 nickname2 nickname3

# Full example
python script2.py --force --config custom.yaml --color blue \
                --items apple --items banana \
                John Smith nickname1 nickname2
```

## Next Steps

Next: [Nested command-line applications](guide_102.md) — subcommands and
multi-level trees like `git` or `docker`.
