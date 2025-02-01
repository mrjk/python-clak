# 7. comparison-with-typer

Date: 2025-01-27

## Status

Accepted

## Context

The issue motivating this decision, and any context that influences or constrains the decision.


Amazing:

- Heavy usage of python annotations
- Beautiful output
- Battery included, completion
- Functions args are actual python args/cli kwargs
- Rich library integration


Pros:

- Low initial boilerplate, low learning curve
- Provide a nested structure for sub-commands (hierarchy is managed with parent/child relationship)
- Relatively easy to start


Cons:

- Complex command lines can be make
- Changing things like help is difficult
- Executing group commands require extra function
- Documentation is extensive, but hard to follow
- Large programs does not fit well
- Not dry, we end up to duplicate always the same args everywhere, especially in large apps
- Completion and startup time is somewhat slow.

## Decision

The change that we're proposing or have agreed to implement.

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
