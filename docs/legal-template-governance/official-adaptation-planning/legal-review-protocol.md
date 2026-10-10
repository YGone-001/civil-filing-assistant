# Legal and Content Review Protocol

**No review has been performed. No reviewer is named. No approval date exists.**

This protocol defines what a real, authorized reviewer must decide before any adaptation may be
implemented. It is a *request specification*, not a record of review.

---

## 1. Four independent decisions

These must never be conflated, and passing one does not imply another:

```text
1 Source authenticity      is this really the issuing authority's text?
2 Legal / content review   is the content correct and applicable to this case type?
3 Engineering acceptance   does the code behave as specified?
4 Release approval         may it ship?
```

A passing validator or a green CI run is evidence for (3) only. A Git commit is not legal approval.

---

## 2. Review domains

### 2.1 Source authenticity

- Issuing authority and exact official source.
- Source document identity (title, version identity if any appears in the file).
- Content hash of the retrieved bytes.
- Publication / effective information **where actually verified** — never inferred from a URL path.
- Whether a later applicable version exists.

### 2.2 Mapping applicability

- Correct case category for each candidate form.
- Correct document type (complaint vs evidence list vs service address).
- Whether the application's scope matches the official scope (see the `contract` variant and
  `divorce` combined-scope questions).
- Conditional and optional elements: which are genuinely required.
- Whether the candidate form suits the procedural posture (mandatory for `labor`).

### 2.3 Legal / content correctness

- Claims and remedies permitted for the category.
- Legal references: who supplies them, and whether they may be auto-inserted (currently: no).
- Procedural prerequisites (notably labour arbitration).
- Monetary calculation assumptions (interest basis, penalty basis, support).
- Unsupported factual assertions and conditional disclosure.
- User guidance and warnings.

### 2.4 Document structure

- Whether a narrative, element-based or hybrid presentation is appropriate for the category, the
  filing channel and the court.

### 2.5 Rights and redistribution

- Development-time inspection of the source.
- Extraction of field labels.
- Adaptation of structure.
- Reproduction of substantive text.
- Redistribution with the application installer.
- Attribution requirements.
- Version replacement and withdrawal.

---

## 3. Review evidence contract

A real review decision must record **all** of the following. None may be fabricated.

```text
review_package_id
source_id
source_sha256
case_type
document_type
affected_gap_ids
affected_crosswalk_ids
reviewer_identity_or_authorized_role
review_date
review_scope
evidence_reviewed
findings
unresolved_issues
decision
decision_evidence
```

The governance policy keeps four evidence strings distinct and they must not be merged:

```text
content_review_evidence
mapping_review_evidence
legal_content_review_evidence
approval_evidence
```

---

## 4. Current state

```text
Source legal review:        NOT_REVIEWED
Governance approvals:       NOT_REQUESTED
Analytical route approvals: NOT_REQUESTED
Rights review:              NOT_REVIEWED
Reviewer identity:          NOT_RECORDED (no review occurred)
Approval date:              NOT_RECORDED (no approval occurred)
```

Every route in `route-readiness.json` carries `legal_content_review_state = NOT_REQUESTED`.

---

## 5. Human approval rules

1. Approval must be independently documented and bound to its exact scope.
2. Approval for one category does **not** approve another category.
3. Approval for a complaint does **not** approve its evidence list or service-address form.
4. Approval for a source does **not** approve its adaptation or its distribution.
5. A broad statement such as "the planning phase is complete" is **not** an authorization.

---

## 6. Required review packages (proposed)

| Package | Case | Document | Blocking question |
|---|---|---|---|
| `rp-loan-complaint` | loan | complaint | interest basis, agreed-vs-provided principal, repayment history |
| `rp-contract-complaint` | contract | complaint | generic vs 房屋买卖 variant, demand element, penalty type |
| `rp-property-complaint` | property | complaint | fee-collection scope, arrears period vs service term |
| `rp-labor-complaint` | labor | complaint | arbitration vs litigation posture, double-wage/overtime detail |
| `rp-divorce-complaint` | divorce | complaint | combined relief scope, visitation, compensation |
| `rp-*-evidence` | all | evidence list | standalone equivalence to the official embedded section |
| `rp-*-address` | all | service address | existence and authority of any official counterpart |
| `rp-source-rights` | all | all | redistribution and attribution position |

Each package is `NOT_REQUESTED`.
