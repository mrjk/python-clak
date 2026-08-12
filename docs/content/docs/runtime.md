# Runtime and facts (`ctx.runtime` / `ctx.facts`)

During command execution, Clak attaches two objects on `ctx` for both **Clak
internals** and your `cli_run` / hooks:

| Object | Role |
| --- | --- |
| `ctx.runtime` | Core CLI/session: TTY, launch context, display, terminal size |
| `ctx.facts` | Optional OS sugar: user/group, hostname, distro (lazy) |

```python
def cli_run(self, ctx, **_):
    r = ctx.runtime
    if r.interactive and r.from_shell:
        ...
    width, _ = r.get_size()

    f = ctx.facts
    print(f.hostname, f.distro_id)
```

Detection runs once when the execute loop starts. Prefer these objects over
re-checking `isatty()` or `get_terminal_size()` yourself.


## Part 1 - Core (`ctx.runtime`)

Eager, local-only. No DNS or NSS.

### Streams / launch

| Field | Type | Meaning |
| --- | --- | --- |
| `stdin_tty` / `stdout_tty` / `stderr_tty` | `bool` | Per-fd TTY |
| `interactive` | `bool` | `stdin_tty and stdout_tty` |
| `ctty` | `str \| None` | Process controlling terminal (one per process), e.g. `/dev/pts/3` |
| `from_shell` | `bool` | Parent executable basename looks like a shell |
| `parent_ppid` | `int` | Parent pid |
| `parent_exe` | `str \| None` | Parent executable path (no args) |
| `parent_cmd` | `str \| None` | Parent full command line |

`interactive` is for “classic interactive CLI” defaults. Piped stdin with a
controlling terminal still possible: use `ctty` (open `/dev/tty`) for prompts.

### Display / env

| Field | Type | Meaning |
| --- | --- | --- |
| `encoding` | `str` | stdout encoding |
| `color_level` | `str` | `none` / `16` / `256` / `truecolor` |
| `color_support` | `bool` | `color_level != "none"` |
| `unicode_support` | `bool` | UTF-family stdout encoding |
| `hyperlinks_support` | `bool` | Best-effort OSC-8 heuristic |
| `pager` | `str \| None` | `CLAK_PAGER` or `PAGER` |
| `term_width` / `term_height` | `int` | Last known size |
| `narrow_width` | `int` | Threshold for `is_narrow` (default `80`) |
| `is_narrow` | `bool` | `term_width < narrow_width` |

`get_size() -> (width, height)` refreshes size. Honors `CLAK_COLUMNS` /
`CLAK_LINES`, then the usual `COLUMNS` / `LINES` (via
`shutil.get_terminal_size`). `TERM` is terminal *type* (for color), not size.

**Narrow width precedence:** `detect_runtime(narrow_width=...)` arg >
`Meta.runtime_narrow_width` > `CLAK_NARROW_WIDTH` > `80`.

```python
class App(Parser):
    class Meta:
        runtime_narrow_width = 100
```

**Color precedence:** `NO_COLOR` > `CLAK_COLORS=0` > `FORCE_COLOR` /
`CLICOLOR_FORCE` > non-TTY stdout > `COLORTERM` / `TERM`.


## Part 2 - Facts (`ctx.facts`) - optional sugar

Almost out of topic for a CLI kit; handy for apps. The `FactsInfo` object is
attached immediately; **field resolution is lazy** (and cached).

### Process identity (real)

| Field | Notes |
| --- | --- |
| `uid` / `gid` / `group_ids` | Numeric (local) |
| `user_name` / `group_name` / `groups` | Names via NSS (`pwd`/`grp`); may block |

`groups` is `dict[str, int]` (name -> gid). Unresolvable gids stay in
`group_ids` only.

### Running credentials (effective)

Same shape under `ctx.facts.running` (`uid`, `gid`, `group_ids`, `user_name`,
`group_name`, `groups`).

### Host / distro

| Field | Notes |
| --- | --- |
| `hostname` | `socket.gethostname()` (lazy, local) |
| `fqdn` / `domain` | DNS; see timeout below |
| `distro_id` / `distro_name` / `distro_version` / `distro_like` | From `/etc/os-release` |
| `distro` | Full os-release map |
| `clear_cache()` | Drop cached values |

### Lazy resolve, logging, `CLAK_FACTS_TIMEOUT`

Before a **blocking** resolve (FQDN, NSS names), Clak logs an **INFO** line on
logger `clak.facts`. If a CLI appears to hang, re-run with higher verbosity to
see that message.

| `CLAK_FACTS_TIMEOUT` | Behavior |
| --- | --- |
| unset / empty | **30 seconds** (default) |
| positive number | Timeout in seconds; soft fallback + WARNING |
| `0` | Skip blocking resolve; use fallback immediately |
| `-1` | No timeout |

On FQDN timeout/error: `fqdn` falls back to `hostname`, `domain` is `None`.
On NSS timeout: names are `None` / empty `groups`.


## Related

- [Logging](logging.md) (`--log-colors` still has its own resolve path)
- [Views](views.md) (`--width` uses `ctx.runtime.term_width` / `stdout_tty`)
