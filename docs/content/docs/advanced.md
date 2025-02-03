# Nested commands


## Advanced Features and Best Practices

### 1. Command Inheritance

You can create a base command class to share functionality:

```python
class BaseCommand(Parser):
    def common_method(self):
        pass

class SpecificCommand(BaseCommand):
    def cli_run(self):
        self.common_method()
```

### 2. Argument Inheritance

Global arguments are accessible to subcommands:

```python
class AppMain(Parser):
    verbose = Argument("--verbose", action="store_true")
    
    class SubCommand(Parser):
        def cli_run(self, verbose=False, **_):
            if verbose:
                print("Verbose mode enabled")
```

### 3. Custom Help Messages

Override the default help behavior:

```python
def cli_run(self, **_):
    print("Custom usage information:")
    self.show_usage()
    print("\nDetailed help:")
    self.show_help()
```

### 4. Command Organization Best Practices

1. **Logical Grouping**:
   - Group related commands under common parents
   - Use meaningful command names
   - Keep the hierarchy shallow (3-4 levels max)

2. **Argument Design**:
   - Put shared options in parent commands
   - Use consistent naming across commands
   - Provide sensible defaults

3. **Documentation**:
   - Write clear help messages
   - Document command relationships
   - Include examples in docstrings

4. **Code Structure**:
   - One class per command
   - Use inheritance for shared behavior
   - Keep command implementations focused

## Error Handling and Validation

1. **Command Not Found**:

```python
def cli_run(self, **_):
    if not hasattr(self, 'subcommand'):
        print("No command specified")
        self.show_help()
        return 1
```

2. **Argument Validation**:

```python
def cli_run(self, name=None, **_):
    if not name:
        print("Error: NAME is required")
        return 1
```

## Testing Nested Commands

1. **Test Command Structure**:

```python
def test_command_structure():
    app = AppMain()
    assert hasattr(app, 'command1')
    assert hasattr(app.command1, 'sub1')
```

2. **Test Command Execution**:

```python
def test_command_execution():
    app = AppMain()
    result = app.dispatch(['command1', 'John'])
    assert result == 0
```
