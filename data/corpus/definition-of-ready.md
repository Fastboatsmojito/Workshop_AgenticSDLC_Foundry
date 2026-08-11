# Definition of Ready

The Definition of Ready is the contract between intake and delivery. A business
requirement may not enter the delivery lifecycle until every check below is
assessed. A failing check does not block intake, but it must be recorded with a
note explaining what is missing and who owns closing it.

## DoR-01 Business outcome is stated

The requirement names the business outcome in terms a non-technical stakeholder
would recognise, not the proposed solution. "Reduce claim cycle time for low-risk
auto claims" is an outcome. "Build a rules engine" is not.

A requirement that only describes a solution fails this check.

## DoR-02 Success is measurable

At least one success measure is stated with a direction and, where possible, a
baseline. Measures must be observable after release without a special study.

Examples of acceptable measures: cycle time in days, straight-through processing
rate as a percentage, manual touches per claim, error rate per thousand
transactions.

## DoR-03 Scope boundaries are explicit

The requirement states what is in scope and what is deliberately excluded.
Exclusions matter more than inclusions, because unstated exclusions become
assumed inclusions during delivery.

## DoR-04 Every requirement is individually testable

Each functional and non-functional requirement can be verified by a test that
produces a pass or fail result. Requirements containing "fast", "user friendly",
"robust", or "as needed" fail this check unless they are accompanied by a
threshold.

Each requirement carries acceptance criteria written so a tester who was not
involved in the analysis could execute them.

## DoR-05 Non-functional requirements are covered

The following categories are considered for every initiative, and either
specified or explicitly marked not applicable with a reason:

- Data handling and personal information
- Auditability and record retention
- Performance and expected volume
- Availability and degradation behaviour
- Access control

An initiative that touches customer data and states no data handling requirement
fails this check.

## DoR-06 Regulatory and compliance obligations are identified

Any obligation arising from regulation, contract, or internal policy is stated as
a requirement rather than left as context. If an obligation is suspected but not
confirmed, it is recorded as an open question naming who can confirm it.

Automated decisions that affect a customer outcome carry an explainability
obligation and must be recorded as such.

## DoR-07 Dependencies and assumptions are recorded

Upstream systems, downstream consumers, third-party services, and organisational
dependencies are named. Assumptions are stated explicitly so they can be
challenged at the approval gate.

## DoR-08 Open questions are listed, not resolved by assumption

Anything unknown is recorded as an open question with the reason it matters.
Filling a gap with a plausible assumption and presenting it as fact fails this
check. A requirement set with honest open questions is ready; one with hidden
guesses is not.

## Assessing the checklist

Each check is marked passed or failed with a short note. The note explains the
evidence for a pass, or what is missing for a fail. Notes such as "looks fine"
carry no information and are treated as a fail on review.

The checklist is assessed against the requirements as written, not against what
the author intended to write.
