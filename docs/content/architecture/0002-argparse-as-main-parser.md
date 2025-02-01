# 2. Argparse as main parser

Date: 2025-01-26

## Status

Accepted

## Context

The issue motivating this decision, and any context that influences or constrains the decision.

Argparse is the de facto python command line parsing library, and it comes with almost
everything. However, it's developper API is not that easy to use, code can become hard to read and
to maintain, reusability is difficult and creating complex command lines can be a nightmare.

There are plenty of other libraries, and they have their own pros and cons, some became quite heavy by the time, and even slow to run/start. The idea here is to keep things light, still while providing a nicer API for argparse.

I ve been inspirated from many existing libraries

Other libraries doing this apporach:
- cliff (openstack)
  - Views
  - strong opiniated architecture
  - class based config
- click ()
  - Arg/Options distinction
  - decorator based config
- Typer ()
  - 

## Decision

The change that we're proposing or have agreed to implement.

We want to use argparse as primer parsing libray. 

We want to keep the same api, but we want to provide a new opiniated architecture:
add_argument() => Argument, Option, Subcommand
  * We use click/Typer semantic here, as it's easier to make distinction between arguments, options and subcommands. In argparse, those concepts are quite mixed, and eventually make difficult onboarding.



## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.


We try to keep the same logic, thus
people knowing well argparse wont' be lost while newcomer may embrace easier argparsing.

minimize learning curve
bring opiniated architecture
allow easy command based recursions, like git
declarative configuration via class


