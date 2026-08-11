# Design Format

Every design artifact produced in the delivery lifecycle uses this structure. The
format exists so that reviewers can compare designs and find the same
information in the same place, and so that a gate reviewer can tell quickly
whether something is missing.

## FMT-01 Overview

Two to five sentences describing the shape of the solution and the approach
taken. Written for a reviewer who has read the requirements but not thought
about the solution. The overview states the approach, not the motivation, which
belongs in decisions.

## FMT-02 Components

A list of components, each with:

- a name describing its responsibility,
- a one-sentence statement of what it is responsible for,
- the components it depends on.

Components are listed in dependency order where one exists, with the most
depended-upon first.

## FMT-03 Data flows

Each flow describes what data moves, from which component to which, what
triggers it, and whether it is synchronous or asynchronous.

Flows are written as sentences rather than arrows so that the trigger and the
payload are both visible. A flow that does not say what triggers it is
incomplete.

## FMT-04 Decisions

Each decision records the choice, the rationale, and the alternatives
considered. Decisions cover anything a reviewer might reasonably have chosen
differently, including integration style, where state lives, how a rule set is
maintained, and how the solution handles failure.

Restating a standard is not a decision. Departing from one always is.

## FMT-05 Risks

Risks name what could go wrong and why it matters, in terms of customer,
regulatory, or operational impact. A risk with no consequence stated is an
observation, not a risk.

Requirements the design does not cover are recorded here rather than omitted.

## FMT-06 Citations

The design cites the standards and format sections it relied on, naming the
document and section. Citations point to material that was actually retrieved
and read.

## FMT-07 What the design does not contain

The design does not contain story breakdowns, estimates, sprint plans, or test
cases. Those belong to the work breakdown that follows it. A design carrying
estimates has usually skipped past the design question.

The design also does not restate the requirements. It references them by
identifier.
