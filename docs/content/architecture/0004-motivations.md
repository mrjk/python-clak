# 4. Motivations

Date: 2025-01-27

## Status

Accepted

## Context

The issue motivating this decision, and any context that influences or constrains the decision.

Other alternatives:
- Current lib are heavy.
- Documentation is hard to understand
- Argparse API is at the same time amazing and awful
- None really fit to git-like applications
- Large programs become messy because lack of structure (functions/decorators)


## Decision

The change that we're proposing or have agreed to implement.

Create the clak arg parser library over argparse.
- Improve developper UX: improve argparse usability for git-like CLI apps
- Use class, and use more pythonic mechanisms such as class inheritance
- Keep library light and portable


## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
