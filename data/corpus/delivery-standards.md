# Delivery Standards

These standards govern how requirements are written and how work is broken down.
They apply to every initiative entering the delivery lifecycle.

## STD-01 Requirement identifiers

Functional requirements are numbered FR-01 upward. Non-functional requirements
are numbered NFR-01 upward. Identifiers are stable once assigned: if a
requirement is withdrawn, its number is retired rather than reused, so that
traceability from design and tests survives.

## STD-02 Requirement statements

A requirement is a single sentence describing one observable behaviour or
constraint. Statements use "must" for obligations and "should" for preferences,
and a requirement marked "should" may be descoped without a change request.

Compound requirements joined by "and" are split. A statement that describes two
behaviours cannot be tested as a single unit.

## STD-03 Rationale

Every requirement records why it exists. Rationale referencing a regulation, a
policy, or a measurable business outcome is preferred over rationale referencing
a stakeholder preference.

Rationale is what allows a reviewer to challenge a requirement rather than
merely accept it.

## STD-04 Acceptance criteria

Acceptance criteria are written from the perspective of an observer of the
system. Each criterion states the condition and the expected result. Criteria
that describe internal implementation are rejected.

At least one criterion per requirement covers the failure or exception path.
Requirements with only happy-path criteria are incomplete.

## STD-05 Non-functional categories

Non-functional requirements are classified into one of: data handling, privacy,
auditability, performance, availability, access control, or operability. Each
carries a threshold or a defined behaviour, never a bare adjective.

Performance requirements state the measure, the threshold, and the load under
which the threshold holds. "Responds quickly" is not a requirement; "returns a
decision within 2 seconds at 50 requests per second" is.

## STD-06 Automated decisions

Where the system makes a decision affecting a customer without human review, the
requirements must state:

- the criteria that drive the decision and where they are maintained,
- how the decision is recorded so it can be reconstructed later,
- the route by which a customer or employee can request a human review.

## STD-07 Personal information

Requirements involving personal information state what is collected, why it is
needed, how long it is retained, and who may access it. Data minimisation is the
default: if an attribute is not required for the stated outcome, it is not
collected.

## STD-08 Audit records

Any action that changes a customer-visible outcome produces an audit record
containing what changed, who or what changed it, when, and the inputs the
decision relied upon. Audit records are append-only and retained per the
retention schedule.

## STD-09 Story slicing

Stories are sliced vertically so that each delivers observable behaviour.
Horizontal slices organised by technical layer are not acceptable, because they
cannot be demonstrated or independently validated.

A story that cannot be demonstrated to a stakeholder is a task, not a story, and
belongs inside a story rather than beside it.

## STD-10 Estimation

Stories are estimated in points reflecting relative complexity, uncertainty, and
effort together. Points are not hours. A story estimated above 8 points is split
before it enters a sprint.

## STD-11 Test coverage of the breakdown

Every story carries at least one test case. Test cases are written in
given/when/then form and classified as unit, integration, or end to end. The
risky and exceptional paths are covered explicitly; a breakdown whose tests only
cover happy paths is returned at the gate.

## STD-12 Dependencies between stories

Dependencies are recorded on the dependent story, naming the story it waits for.
Dependencies are stated only where a genuine ordering constraint exists.
Inventing sequence where none exists removes the delivery team's ability to
parallelise.
