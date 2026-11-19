# 3. No argparse merging

Date: 2025-01-27

## Status

Accepted

## Context

The issue motivating this decision, and any context that influences or constrains the decision.

While it was an interesting feature, the argparse merging feature will not be provided. Indeed,
during author experience, it has been increadily diffilcult to write a proper and reliable implementation
doing so. Code ended up huge and messy, barely maintainable and the feature is not that important
to achive project goals.

In the end, author feels the way how was designed argparse library is not really designed to work this way,
investigating more time would require extensive dig in argparse library. Also, author may understand
why 3third party argument parsing library created their own implementations, as argparse seems a quite complicated library to extend or work with.

## Decision

The change that we're proposing or have agreed to implement.

Argparse definition merge will be not supported.

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.

This use case won't be supported, unless if someone come with an acceptable implementation.
