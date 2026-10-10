# Authorization Gate Sequence

**Current implementation decision: `NO-GO`. Default-deny.**

Planning status and authorization are different things. This document defines the gate sequence and
records its present state. No gate is set to PASS, because no independently documented review with
applicable authority has occurred.

---

## 1. Gate sequence

```text
SOURCE_AUTHENTICITY
        |
        v
SOURCE_CONTENT_REVIEW
        |
        v
MAPPING_APPLICABILITY_REVIEW
        |
        v
LEGAL_CONTENT_REVIEW
        |
        v
RIGHTS_AND_REDISTRIBUTION_REVIEW
        |
        v
SCOPED_ENGINEERING_AUTHORIZATION
        |
        v
IMPLEMENTATION
        |
        v
DOCX_REGRESSION_ACCEPTANCE
        |
        v
RELEASE_APPROVAL
```

Gates are sequential. A failed or missing prerequisite blocks every downstream gate.

---

## 2. Current gate state

| # | Gate | State | Basis |
|---|---|---|---|
| 1 | `SOURCE_AUTHENTICITY` | `REVIEW_REQUIRED` | file retrieved and hashed (`SOURCE_FILE_VERIFIED`), but no authority-issued applicability confirmation per category |
| 2 | `SOURCE_CONTENT_REVIEW` | `REVIEW_REQUIRED` | no documented content review of the per-category forms |
| 3 | `MAPPING_APPLICABILITY_REVIEW` | `REVIEW_REQUIRED` | all 15 mappings are `CANDIDATE_SOURCE_IDENTIFIED`, `UNVERIFIED` or `NO_OFFICIAL_SOURCE_IDENTIFIED` |
| 4 | `LEGAL_CONTENT_REVIEW` | `REVIEW_REQUIRED` | no legal/content review performed; reviewer identity not recorded |
| 5 | `RIGHTS_AND_REDISTRIBUTION_REVIEW` | `REVIEW_REQUIRED` | `legal_or_copyright_review_status = NOT_REVIEWED` |
| 6 | `SCOPED_ENGINEERING_AUTHORIZATION` | `NOT_ASSESSED` | blocked by gates 1–5 |
| 7 | `IMPLEMENTATION` | `BLOCKED` | not authorized |
| 8 | `DOCX_REGRESSION_ACCEPTANCE` | `NOT_ASSESSED` | not reached |
| 9 | `RELEASE_APPROVAL` | `NOT_ASSESSED` | not reached |

Allowed planning states:

```text
NOT_ASSESSED     no work started
REVIEW_REQUIRED  evidence missing; a decision is needed
BLOCKED          a prerequisite is missing or failed
```

A future `PASS` requires independently documented evidence and applicable authority. Nothing in this
task sets a real gate to `PASS`.

---

## 3. Default-deny policy

1. Implementation authorization defaults to `NOT_AUTHORIZED`.
2. Missing information never implies permission.
3. A failed prerequisite blocks downstream authorization.
4. A successful automated test never overrides a legal-review or rights-review blocker.
5. No route, work package or source may carry `AUTHORIZED`, `APPROVED_FOR_IMPLEMENTATION` or
   `APPROVED_FOR_RELEASE`.

---

## 4. Required scope of any future authorization

A future authorization must be explicitly bound to **all** of:

```text
source_id and content hash
case_type
document_type
approved element or gap scope (explicit ID list)
selected adaptation strategy (A / B / C)
approved engineering work package (work_package_id)
required safeguards
authorized reviewer or decision-maker
decision date
decision evidence
```

A broad statement such as "the planning phase is complete" is **not** an authorization for
implementation.

---

## 5. Machine-checked invariants

`tools/check_template_adaptation_plan.py` enforces the planning-side consequences of this gate:

- every route has `implementation_authorization = NOT_AUTHORIZED`;
- every work package has `implementation_authorization = NOT_AUTHORIZED`;
- no planning record may claim an approval, a cleared rights gate or an approved source;
- a source at `SOURCE_FILE_VERIFIED` may not be recorded as adaptation-approved;
- missing authorization data fails closed (a missing value is an error, not a permission).

The validator cannot verify that a human reviewer existed. It proves planning consistency only.
