# Regression and Rollback Plan

**Future engineering acceptance criteria. Nothing here is implemented in this task.**

This plan states what a *future authorized* implementation must prove, and how it must be revertible.

---

## 1. Functional scenarios

For each selected future pilot, tests must cover:

```text
normal complete input
missing optional input
missing required input
one plaintiff / one defendant
multiple plaintiffs
multiple defendants
enterprise parties
unknown facts (tri-state UNKNOWN)
confirmed negative facts
confirmed positive facts
partially paid amounts
date boundary cases
zero amounts
conditional claim suppression
invalid or contradictory claims
```

Only the scenarios relevant to the category are required, but the tri-state scenarios
(UNKNOWN / CONFIRMED_TRUE / CONFIRMED_FALSE) are mandatory wherever a tri-state fact exists.

## 2. DOCX structure verification

Plan to verify, per pilot:

```text
document title
party information
section ordering
tables
checkboxes (if any)
conditional blocks
Chinese typography
line wrapping
page breaks
signature and date
missing-value placeholders
evidence sections
```

Actual visual DOCX comparison belongs to the future authorized implementation phase; this plan only
names the checks.

## 3. Existing regressions that must keep passing

```text
tests/test_e2e_documents.py
tests/test_factual_confirmation.py
tests/test_navigation_requirements.py
tests/test_transactional_export.py
tests/test_template_governance.py
tests/test_template_crosswalk.py
tests/test_template_adaptation_plan.py
```

Offline behaviour must remain verifiable: no test may require network access.

## 4. Rollback requirements

A future approved adaptation must be disableable or revertible without:

- losing original user inputs;
- rewriting existing facts;
- breaking unrelated case types;
- disabling the legacy document path prematurely;
- invalidating source and approval audit evidence.

Concretely, a future implementation must:

1. keep the current export path available until release approval;
2. keep the export transaction (staging directory + single rename) intact;
3. keep `build_case_model()` as the single source for preview and export;
4. record which source version and which approval supported the new path, so a rollback does not
   orphan the audit trail;
5. allow a per-case, per-document revert rather than an all-or-nothing revert.

**No runtime feature flag or rollback mechanism is implemented now.** This section is a requirement
specification only.

## 5. Acceptance criteria (future)

A future change is engineering-acceptable only when:

```text
[ ] every existing test still passes unchanged
[ ] new tests cover the new fields and their tri-state paths
[ ] the offline guarantee is intact
[ ] the DOCX integrity check still passes
[ ] no official example text appears in any output
[ ] the rollback requirements above are demonstrably satisfied
```

Engineering acceptance is **not** legal approval and **not** release approval.
