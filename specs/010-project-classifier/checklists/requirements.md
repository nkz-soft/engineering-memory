# Specification Quality Checklist: Project classifier

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-25
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Two questions were raised and answered, and the answers are now requirements rather than notes.
  Ambiguity resolves by declared priority, with a tie at the top yielding `project:unknown`
  (FR-007, FR-007a). An unconfigured rule set is a warning and an empty rule set; a configured one
  that is missing is a failure (FR-012a). Both were asked rather than assumed because they are
  visible in the rule set a user writes, and because a wrong guess on either is expensive to
  reverse once a bank has been filled under it.
- The second answer carries a consequence the spec is obliged to state rather than hide: §17 skips
  unchanged conversations, so `project:unknown` written by a rule-less run does not correct itself.
  FR-012b makes the warning say so, and the Assumptions record that a reclassification pass is
  separate work.
- Everything else a reader might expect to be asked is settled in Assumptions: literal aliases
  rather than patterns, unscored matches, a single-valued project, and the sanitized conversation
  as the input. Each follows from a document already binding — §6, §7, §15, §17 or Principle IV.
- Mechanisms are deliberately deferred to `plan.md`: the configuration file's format, how the rule
  set is indexed for a corpus-sized scan, where the composed fallback of FR-013 lives in the test
  layout, and whether loading is a separate component from classifying.
- FR-004's "bounded by something other than a letter or a digit" is stated as behaviour rather than
  as a regular expression, so the requirement survives whatever the implementation uses to express
  it. SC-005 is what holds it to account.
