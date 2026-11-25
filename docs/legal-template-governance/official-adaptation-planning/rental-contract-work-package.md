# 租赁合同纠纷 — Governance Work Package

> **Status: OPEN / NO-GO.** This is a post-baseline governance addendum only.
> No official source has been identified or approved. No legal review has occurred.
> No mapping is approved. No implementation or release is authorized.
> The existing rental output is a project-authored software baseline, not an official template.

- Work package: `wp-rental-source-discovery`
- Case type: `rental`
- Current stage: `SOURCE_DISCOVERY`
- Baseline commit: `b81810ad2669194b30094fd5dd91613c8d234e82`
- Created: 2026-11-26
- Machine-readable record: `rental-contract-work-package.json`
- Validator: `tools/check_rental_governance_package.py`

This package does **not** alter the frozen five-case planning records (15 routes, 131 gaps,
199 crosswalks) in this directory. It records a separate, post-baseline workstream for the
rental case type that already exists in the runtime.

---

## 1. Why this package exists

The application now generates three rental-contract documents:

- 民事起诉状（租赁合同纠纷）
- 证据清单
- 送达地址确认书

The engineering path is implemented and tested, but the legal-template governance path has not
started. `case-template-mapping.json` still covers only the original five case types. Adding
rental entries without source evidence, a written comparison and review evidence would create
false governance coverage. This package starts the missing work at the correct first stage:
**source discovery**.

---

## 2. Current runtime state

| Item | Status |
|---|---|
| Runtime model | `RentalCaseModel` in `models/case_model.py` |
| Wizard page | `views/pages/rental.py` |
| Draft support | `drafts/schema.py`, `views/draft_io.py` |
| Document export | `utils/doc_generator.py` |
| Evidence suggestions | `utils/evidence_library.py` |
| Fact exemplars | `utils/facts_examples.py` |
| Automated tests | `tests/test_rental_case.py`, `tests/test_word_acceptance.py`, `tests/test_e2e_documents.py` |
| Engineering status | IMPLEMENTED_AND_TESTED |
| Runtime characterization | PROJECT_AUTHORED_STRUCTURED_TEMPLATE |
| Governance status | NOT_REGISTERED |

Current fields include property address, contract date, lease term, monthly rent, payment cycle,
arrears period and amount, late fee, demand history, contract status, termination date, whether
the premises were returned, court name, and optional user-supplied claims/facts.

Current claims cover termination when requested, arrears, late fees, return of premises in
termination/requested-termination cases, and litigation costs. The model does not claim to cover
every rental dispute type.

---

## 3. Explicit non-claims

This package does **not** claim:

- that an official rental-contract template exists or has been located;
- that any current rental output conforms to an official template;
- that any source may be adapted or redistributed;
- that any legal/content review has occurred;
- that any mapping is approved;
- that the current rental implementation is authorized by this package;
- that engineering tests are legal approval or release approval.

The absence of a rental entry in the frozen five-case analysis is **not** evidence that no
official rental template exists. It only records the scope of that earlier audit.

---

## 4. Source discovery target

The first task is to locate and record authoritative sources for:

1. a rental-contract civil complaint;
2. a standalone evidence-list document, or a decision that the official complaint's evidence
   section is the only relevant counterpart;
3. a service-address confirmation form, or a documented decision that no counterpart exists in
   the inspected material.

For every candidate, record a source-registry entry with an official URL and explicit `null`
values for unknown attributes. A URL alone does not establish authenticity. A retrieved file does
not establish legal applicability. Do not populate `case-template-mapping.json` until source
evidence exists.

Current source-discovery state:

```text
candidate_source_ids: []
selected_source_id:   null
official_counterpart: UNKNOWN
status:               NOT_STARTED
```

---

## 5. Known legal and procedural questions

- Is the correct counterpart a generic lease dispute, a residential lease, a commercial lease,
  or another variant?
- Must the plaintiff's ownership, right to rent, or authority to sublease be captured?
- Should the complaint request termination, confirm an already-completed termination, or make no
  termination claim in each procedural posture?
- Should arrears, late fees, deposit set-off, occupation-use fees and damages be separate claims?
- What demand/notice, termination-notice and return-of-premises facts must be user-confirmed?
- How should jurisdiction be handled when the property location, defendant residence and a
  contractual jurisdiction clause differ?
- Does an official standalone evidence-list or service-address form exist for rental disputes?

These questions are inputs to future legal/content review; they are not answered here.

---

## 6. Work breakdown and current gate state

| Stage | Task | Status | Exit condition |
|---|---|---|---|
| `SOURCE_DISCOVERY` | Locate candidate sources | `NOT_STARTED` | Source record with official URL and explicit nulls |
| `SOURCE_VERIFICATION` | Verify identity, version, hash and artifact | `BLOCKED` | `SOURCE_FILE_VERIFIED` with evidence |
| `TEXT_AND_STRUCTURE_COMPARISON` | Compare official elements with rental fields | `BLOCKED` | Written comparison of elements/sections/omissions |
| `CASE_MAPPING_REVIEW` | Decide counterpart mapping | `BLOCKED` | Mapping entries added only after source evidence |
| `LEGAL_CONTENT_REVIEW` | Review claims, facts and procedure | `BLOCKED` | Documented legal/content decision |
| `RIGHTS_AND_REDISTRIBUTION_REVIEW` | Decide adaptation/redistribution rights | `BLOCKED` | Separate rights decision |
| `ENGINEERING_IMPLEMENTATION` | Implement scoped changes only | `NOT_AUTHORIZED` | Scoped engineering authorization |
| `DOCX_REGRESSION_VALIDATION` | Regression and visual inspection | `NOT_ASSESSED` | Automated DOCX tests plus pagination/table check |
| `RELEASE_APPROVAL` | Release decision | `NOT_ASSESSED` | Separate release approval |

The gate sequence is:

```text
SOURCE_AUTHENTICITY
  -> SOURCE_CONTENT_REVIEW
  -> MAPPING_APPLICABILITY_REVIEW
  -> LEGAL_CONTENT_REVIEW
  -> RIGHTS_AND_REDISTRIBUTION_REVIEW
  -> SCOPED_ENGINEERING_AUTHORIZATION
  -> IMPLEMENTATION
  -> DOCX_REGRESSION_ACCEPTANCE
  -> RELEASE_APPROVAL
```

Missing information never implies permission. A passing test suite never overrides a missing
legal, rights or source review.

---

## 7. Exit criteria for this work package

- All three rental document types have an explicit source/counterpart decision.
- Rental fields, claims and conditionality have a documented legal/content review.
- Any central mapping entry is added only with source evidence and remains unapproved until
  separately approved.
- Any runtime change has scoped engineering authorization and passes DOCX regression plus visual
  inspection.
- Release approval is recorded separately.

Until these criteria are met, the rental release gate remains `NO-GO`.

---

## 8. Integration rules

1. Keep `case-template-mapping.json` unchanged until source evidence exists.
2. Keep the frozen five-case gap analysis, crosswalk and adaptation-plan counts unchanged.
3. Do not treat the existing rental implementation as legally reviewed because tests pass.
4. Do not add an `APPROVED` mapping without a separately approved source, legal review and rights
   review.
5. Do not change rental document text under this package without scoped engineering authorization.
6. Record reviewer roles only when actual reviewers are assigned; do not invent names or dates.

---

## 9. Related files

- `models/case_model.py` — `RentalCaseModel`
- `views/pages/rental.py` — rental wizard page
- `drafts/schema.py` — rental draft fields and flags
- `utils/doc_generator.py` — shared DOCX renderer
- `utils/evidence_library.py` — rental evidence suggestions
- `utils/facts_examples.py` — rental fact exemplars
- `tests/test_rental_case.py` — rental engineering tests
- `docs/legal-template-governance/case-template-mapping.json` — frozen five-case registry
- `docs/legal-template-governance/governance.md` — change-control lifecycle and approval rules
- `docs/legal-template-governance/official-adaptation-planning/approval-gates.md` — gate sequence
