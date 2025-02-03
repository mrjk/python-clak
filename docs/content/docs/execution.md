# Make script executable
This guide explains different ways to make your Python scripts executable and runnable from the command line. Whether you're developing a simple script or a full CLI application, you'll learn how to:

- Run scripts directly with Python
- Make scripts executable on Unix-like systems
- Package scripts as command-line tools
- Use package managers like pip, Poetry, PDM and UV

We'll cover best practices and common patterns for each approach.


There are different ways:

- Direct call:
  - `python script.py --help`
  - `python script.py ...`
- Direct executable:
  - `chmod +x script.py`
  - `./script.py --help`
  - `./script.py ...`
- Module call, when packaged:
  - `python -m pkg --help`
  - `python -m pkg ...`


## Without package managers


### With python interpreter

The simplest way is to call Python directly with your script:

1. Create your Python script:

   ```python
   import sys

   def main():
       print("Hello, World!")
       return 0

   if __name__ == "__main__":
       sys.exit(main())
   ```

2. Run the script:
  
```bash
   python script.py --help
   python script.py ...
   ```

This method requires no additional setup or modifications to the script file.

### As executable script

To make a Python script executable without using package managers, follow these steps:

1. Add a shebang line at the beginning of your script:

   ```python
   #!/usr/bin/env python3
   
   import sys
   
   def main():
       print("Hello, World!")
   
   if __name__ == "__main__":
       sys.exit(main())
   ```

2. Make the script executable:
  
   ```bash
   chmod +x script.py
   ```

3. Run the script:
  
   ```bash
   ./script.py --help
   # or from anywhere if the script is in $PATH
   script.py --help

   ```

## With package managers

Here's how to make your Python scripts executable using different package managers:

### Setuptools

1. Create a `setup.py`:

   ```python
   from setuptools import setup

   setup(
       name="your-package",
       version="0.1.0",
       packages=["your_package"],
       entry_points={
           "console_scripts": [
               "your-command=your_package.main:main",
           ],
       },
   )
   ```

2. Install in development mode:
  
   ```bash
   pip install -e .
   ```

3. Run your command:
  
   ```bash
   your-command
   ```

### Poetry

1. Configure `pyproject.toml`:

   ```toml
   [tool.poetry]
   name = "your-package"
   version = "0.1.0"
   description = ""
   authors = ["Your Name <your@email.com>"]

   [tool.poetry.dependencies]
   python = "^3.8"

   [tool.poetry.scripts]
   your-command = "your_package.main:main"
   ```

2. Install using Poetry:

   ```bash
   poetry install
   ```

3. Run your command:
  
   ```bash
   poetry run your-command

   ```

### PDM

1. Configure `pyproject.toml`:

   ```toml
   [project]
   name = "your-package"
   version = "0.1.0"
   dependencies = []

   [project.scripts]
   your-command = "your_package.main:main"
   ```

2. Install using PDM:
  
   ```bash
   pdm install
   ```

3. Run your command:
  
   ```bash
   pdm run your-command

   ```

### UV

1. Configure `pyproject.toml` (similar to Poetry or PDM format):

   ```toml
   [project]
   name = "your-package"
   version = "0.1.0"
   dependencies = []

   [project.scripts]
   your-command = "your_package.main:main"
   ```

2. Install using UV:
  
   ```bash
   uv pip install -e .
   ```

3. Run your command:
  
   ```bash
   your-command

   ```

### Best Practices

1. Always use `sys.exit(main())` in your entry points for proper exit code handling
2. Include proper argument parsing (e.g., using `argparse` or `click`)
3. Use descriptive command names that don't conflict with existing system commands
4. Provide proper documentation and help messages
5. Handle errors gracefully

Example of a well-structured entry point:

```python
#!/usr/bin/env python3
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Your command description")
    parser.add_argument("--option", help="An option description")
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        # Your main logic here
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

```
