# Architecture Standards

These standards constrain solution design. A design that departs from a standard
is permitted, but the departure must be recorded as a decision with its rationale
and the alternatives considered.

## ARC-01 Components are defined by responsibility

A component is named for what it is responsible for, not for the technology that
implements it. Technology choices belong in decisions, not in component names,
so that the design survives a change of platform.

Each component has one primary responsibility. A component whose responsibility
requires the word "and" is usually two components.

## ARC-02 Explicit dependencies

Every component declares what it depends on. Cyclic dependencies between
components are not permitted. Where a cycle appears unavoidable, it indicates a
missing component that owns the shared concern.

## ARC-03 Data residency

Personal information and claims data remain within the designated regional
boundary at rest and in transit. Services that process this data are deployed in
approved regions only. A design that sends regulated data to a service outside
the boundary must record this as a risk and name the control that mitigates it.

## ARC-04 Personal information handling

Personal information is minimised, encrypted at rest and in transit, and access
to it is logged. Systems pass identifiers rather than full records where the
consuming component does not need the detail.

Personal information is never written to application logs, trace attributes, or
error messages.

## ARC-05 Auditability of automated decisions

Where a component makes or materially influences an automated decision about a
customer, the design records how the decision, its inputs, and the version of
the rules or model used are captured. It must be possible to reconstruct why a
specific decision was made months later.

Designs that compute a decision without persisting its basis fail this standard.

## ARC-06 Integration style

Synchronous request/response is used where the caller needs the result to
proceed. Asynchronous messaging is used where the work can complete
independently of the caller. Long-running work behind a synchronous interface is
not acceptable.

Every integration point states its failure behaviour: retry policy, timeout, and
what the caller experiences when the dependency is unavailable.

## ARC-07 Degradation

The design states what happens when a dependency fails. Preferred behaviour is
graceful degradation to a safe path, typically routing to manual handling,
rather than failing the customer interaction outright.

Automatic fallback to a less accurate automated decision is not acceptable for
decisions affecting customer outcomes; those fall back to human review.

## ARC-08 Observability

Each component emits health, throughput, latency, and error signals. Any
component participating in an automated decision additionally emits the decision
outcome distribution, so that drift is detectable without inspecting individual
records.

Traces carry a correlation identifier that survives across component boundaries.

## ARC-09 Access control

Access is granted to identities, not to shared secrets, and is scoped to the
minimum required. Service-to-service calls authenticate as a workload identity.
Standing human access to production data is not granted by default.

## ARC-10 Data flows

The design describes how data moves between components: what is carried, in
which direction, and triggered by what. A component diagram without data flows
is incomplete, because the risks in a regulated system usually live in the flows
rather than in the boxes.

## ARC-11 Recording decisions

A design decision records the choice made, the reasoning, and the alternatives
that were considered and rejected. A decision presented without alternatives
reads as though none were evaluated and will be challenged at the gate.

## ARC-12 Traceability to requirements

Every approved requirement is traceable to at least one component or data flow.
Requirements with no home in the design are recorded as risks rather than
silently dropped.
