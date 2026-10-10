# Final Decision Request

**CURRENT DECISION: `IMPLEMENTATION: NO-GO`**

This is the decision package for the human authority that would have to authorize any production
change. It states exactly what is requested, what is unknown, and what is blocked.

---

## 1. What is being asked

Nothing is being requested *now*. This package records the decisions that would be required before any
production document could change, and the evidence each decision would need.

```text
Requested today          : none
Implementation           : NO-GO
Authorization state      : NOT_AUTHORIZED
Default on missing input : DENY
```

---

## 2. Recommended first review target (proposal only)

```text
recommended_first_review_target : property
recommended_first_work_package  : wp-property-complaint
linked route                    : route-property-civil-complaint
linked governance mapping       : map-property-complaint
status                          : PROPOSED / NOT_AUTHORIZED
```

**No pilot is implementation-ready.** Every category carries a blocking source or legal question, and
no review has been performed. If the reviewer concludes that `property` is not the right starting
point, the plan supports any other ordering without change to the frozen records.

---

## 3. Proposed change scope (for that package only)

```text
case_type      : property
document_type  : civil_complaint
linked gaps    : the 22 frozen property complaint gaps
source         : spc-2025-notice-pdf, sha256 07fc626a…f9fd11b88 (frozen; not re-verified here)
strategy       : C — explicitly reviewed hybrid (see adaptation-strategy.md)
```

Any authorization must be bound to exactly this scope, with the explicit gap ID list, the source hash
and the selected strategy. It would not authorize the other 14 routes.

---

## 4. Known unresolved legal questions

| # | Question | Affects | Owner |
|---|---|---|---|
| 1 | Does the official 物业服务合同纠纷 element set cover a pure fee-collection claim? | property | legal/content reviewer |
| 2 | May the arrears period stand in for the agreed service term? (`GAP-PROPERTY-TERM-SEMANTICS`) | property | legal/content reviewer |
| 3 | Is the generic `买卖合同纠纷` form the right counterpart, or is `房屋买卖合同纠纷` required? | contract | legal/content reviewer |
| 4 | Which labour procedural posture applies, and is the located litigation form the correct counterpart? | labor | legal/content reviewer |
| 5 | Does one official divorce form cover the combined relief? | divorce | legal/content reviewer |
| 6 | Must interest basis, period unit and "至实际清偿之日" be captured, and is the current estimate acceptable? | loan | legal/content reviewer |
| 7 | How must partial repayment be captured so no full-amount claim is asserted by default? | loan | legal/content reviewer |
| 8 | Is the standalone evidence list equivalent to the official embedded section? | all | legal/content reviewer |
| 9 | Does an official service-address confirmation form exist elsewhere? | all | source verification + legal |
| 10 | Are the fixed font/margin/spacing constants acceptable, or are they court requirements? | all | source verification |

None of these is answered by this plan.

---

## 5. Source-version uncertainty

- The source of record is `spc-2025-notice-pdf` at `SOURCE_FILE_VERIFIED`.
- It has **not** reached `CONTENT_REVIEWED`, `MAPPING_REVIEWED` or `APPROVED_FOR_ADAPTATION`.
- Whether a later authoritative revision exists is unresolved.
- Whether the uploaded file has been replaced in place is unresolved.
- No source version or hash is changed by this plan.

## 6. Rights-review uncertainty

- `legal_or_copyright_review_status = NOT_REVIEWED` for every source.
- Redistribution, attribution and derivative-adaptation positions are undecided.
- No third-party binary is committed and none may be committed before a rights review.

## 7. Required actual reviewer decisions

Each must be made by a named, authorized reviewer and recorded with the evidence contract in
`legal-review-protocol.md` §3:

```text
[ ] source authenticity and applicability for the scoped category
[ ] mapping applicability for the scoped category and document type
[ ] legal / content correctness of the scoped change
[ ] rights and redistribution position
[ ] scoped engineering authorization
[ ] release approval (after implementation, separately)
```

## 8. Required regression criteria

```text
[ ] all existing tests pass unchanged
[ ] new tests cover every new field and every tri-state path
[ ] DOCX integrity check passes
[ ] visual inspection of the generated DOCX per the regression plan
[ ] offline behaviour verifiably intact
```

## 9. Required rollback conditions

```text
[ ] the legacy document path remains available until release approval
[ ] rollback is possible per case and per document
[ ] user inputs survive a rollback
[ ] source and approval audit evidence remains valid after rollback
```

## 10. Decision

```text
IMPLEMENTATION: NO-GO
```

Reason: the required source, mapping, legal/content and rights reviews have not been completed, no
reviewer has been named, and no authorization exists. A green test suite, a clean CI run and a
complete planning package are **not** substitutes for those reviews.
