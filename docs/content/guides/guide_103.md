# Advanced Usage

Clak provide a bunch of functionnalities out of the box.

## Integrated fetaures

* Automatic environment variable parsing
* Error and exception handling
* Automatic management of `--help` and `-h` flags

TODO: Where is the ref ???


## Advanced customization

Some behavior can be overriden on a per node or per argument basis.

### Arguments customization

Arguments are defined directly in classes, via the `Argument` class. This class accept a number of parameters that bring you a lot of flexibility on how arguments
are parsed.

TODO: Where is the ref ???

### Parsers `Meta`

The `Meta` class allows to change some behaviors of the parser. For example:

``` python

class MyApp(Parser):

    class Meta:
        app_name = "My app name"
        env_prefix = "MY_APP_ENV_PREFIX"

```

TODO: Where is the ref ???
