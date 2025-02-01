# 5. comparison-with-cliff

Date: 2025-01-27

## Status

Accepted

## Context

The issue motivating this decision, and any context that influences or constrains the decision.

Cliff argparse is a powerful tool for creating CLI applications created by the openstack foundation. I really liked what deliver this library, but this library is meant to be really extensible, and thus complex. Also, it requires a lot of boilerplate to quickstart.

Amazing:

- Designed for git-like commands
- Command discovery is probably the best from what we can do today
- Class based opinionated code structure
- Provide concept of views

- Battery included, completion, views and extendable


Pros:

- Provide a flat structure for commands (hierarchy is managed as a flat list)
- very well designed for fully extendable CLI


Cons:

- Learning curve is high
- Complex
- Large Boilerplate, multi file structure often too large for small projects
- Documentation is difficult, especially at the begining, the cliffdemo is almost required to understand how to use it.
- Extending the cli in python submodules implies editing settings in the package. It is sometime difficult to manage it correctly.
- Very powerful, but not very popular

## Decision

The change that we're proposing or have agreed to implement.

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
