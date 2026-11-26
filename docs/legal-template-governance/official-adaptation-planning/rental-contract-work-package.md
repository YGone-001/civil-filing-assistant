# 租赁合同纠纷 — Governance Work Package

> **Status: OPEN / SCOPED_FIX_IMPLEMENTED / NO-GO.** This is a post-baseline governance addendum
> only. A candidate official rental complaint has been identified, its file verified, and a
> documentary comparison with 35 open gaps recorded. The mapping review is complete: three
> unapproved rental entries were added to the central mapping registry. A non-signatory preflight
> covering all 21 questions is complete and recommends modification and recheck. A scoped
> engineering authorization fixed only PF-01 (payment-status wording) and PF-02 (multiple-defendant
> attribution); both await recheck. PF-03 and PF-04 remain open. No reviewer has been assigned and
> no formal legal review has occurred. No mapping is legally reviewed or approved, and the overall
> implementation remains unauthorized. No release is authorized.
> The existing rental output is a project-authored software baseline, not an official template.

- Work package: `wp-rental-source-discovery`
- Case type: `rental`
- Current stage: `LEGAL_CONTENT_REVIEW`
- Baseline commit: `1cb15822aa50f3b9708e649c212057b327c2ed6d`
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

The engineering path is implemented and tested, but the legal-template governance path is still
at its earliest stages. `case-template-mapping.json` now includes three unapproved rental entries
added by the mapping review. Adding those entries without source evidence, a written comparison
and review evidence would have created false governance coverage. This package records the missing
work from the first stage: **source discovery**. Source discovery, file-level verification, the
documentary comparison and the mapping review are complete; legal/content review is the next
stage.

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
| Governance status | REGISTERED_UNAPPROVED (3 rental entries; legal review packet prepared, no reviewer assigned) |

Current fields include property address, contract date, lease term, monthly rent, payment cycle,
arrears period and amount, late fee, demand history, contract status, termination date, whether
the premises were returned, court name, and optional user-supplied claims/facts.

Current claims cover termination when requested, arrears, late fees, return of premises in
termination/requested-termination cases, and litigation costs. The model does not claim to cover
every rental dispute type.

---

## 3. Explicit non-claims

This package does **not** claim:

- that the candidate official rental complaint has been selected, mapped or approved;
- that any current rental output conforms to an official template;
- that the text and structure comparison is a legal review, mapping decision or approval;
- that the legal review packet is a legal review, legal opinion or approval;
- that the current narrative output must be replaced by the official element table;
- that any source may be adapted or redistributed;
- that any legal/content review has occurred;
- that any mapping is approved;
- that the current rental implementation is authorized by this package;
- that engineering tests are legal approval or release approval.

The absence of a rental entry in the frozen five-case analysis is **not** evidence that no
official rental template exists. It only records the scope of that earlier audit.

---

## 4. Source discovery and verification result

The first two tasks are complete. The inspected source is:

| Item | Value |
|---|---|
| Source | `spc-2025-notice-pdf` |
| Official URL | `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf` |
| Source level / type | A / `OFFICIAL_TEMPLATE` |
| Verification status | `SOURCE_FILE_VERIFIED` |
| Re-retrieved | 2026-11-26 |
| File size | 6,832,359 bytes |
| Page count | 975 |
| SHA-256 | `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` |
| Local artifact | `NOT_STORED_IN_REPOSITORY` |

File verification means only that the file's identity matched the existing registry record. It
does not establish legal applicability, content correctness or approval.

### Counterpart assessment (limited to this source)

| Document type | Classification | Evidence |
|---|---|---|
| Civil complaint | `CANDIDATE_OFFICIAL_COMPLAINT` | `民事起诉状（房屋租赁合同纠纷）` blank form at PDF pages 171–176 (printed 155–160); filled instance at PDF pages 181–186 (printed 165–170) |
| Evidence list | `OFFICIAL_SECTION_ONLY` | The official rental complaint contains an `证据清单` section at PDF pages 175/185; no standalone official evidence-list document was identified in this PDF |
| Service address confirmation | `NO_COUNTERPART_IDENTIFIED_IN_INSPECTED_SOURCE` | No service-address confirmation form was found in the inspected rental pages; this statement is limited to this source |

Current discovery state:

```text
candidate_source_ids: ["spc-2025-notice-pdf"]
selected_source_id:   null
official_counterpart: CANDIDATE_OFFICIAL_COMPLAINT
status:               CANDIDATE_IDENTIFIED
```

The page ranges are evidence for the comparison and mapping review. They are not a mapping, an
applicability decision or an approval. The absence of a service-address form in this PDF does not establish that no such
official document exists.

### 4.1 Text and structure comparison result

The documentary comparison is complete. It compares the official blank form and instance with a
fictional current rental output and the current field, claim and fact code paths. Full detail is in
[`rental-text-and-structure-comparison.md`](rental-text-and-structure-comparison.md).

Key findings:

- The current output is a narrative, lessor-oriented complaint; the official text is an element
  table with separate lessor and lessee claim branches.
- Core arrears claims and facts are covered.
- 35 open gaps are recorded (RCS-01 to RCS-35), covering party detail, claim items, jurisdiction
  and preservation, fact elements, mediation preference and format.
- The comparison does not decide applicability, legal sufficiency or approval.

The highest-priority open questions are: whether the product remains lessor-only or also supports
a lessee plaintiff; whether an already-terminated lease needs a confirmation claim; whether return
of the premises and damages are separate claims; and whether to adopt the official element-table
style.

### 4.2 Case mapping review result

The mapping review is complete. Three unapproved entries were added to
`docs/legal-template-governance/case-template-mapping.json`:

| Document type | Mapping ID | Mapping status | Decision |
|---|---|---|---|
| Civil complaint | `map-rental-complaint` | `CANDIDATE_SOURCE_IDENTIFIED` | The official rental complaint is the documentary counterpart; legal applicability is not reviewed |
| Evidence list | `map-rental-evidence` | `UNVERIFIED` | Only an official evidence-list section exists; no standalone official document was identified |
| Service address confirmation | `map-rental-address` | `NO_OFFICIAL_SOURCE_IDENTIFIED` | No counterpart was found in the inspected source |

All three entries remain `approval_status: NOT_REQUESTED`. The mapping review does not approve any
mapping or legal conclusion. The central registry now has 18 entries (15 original + 3 rental); the
frozen five-case planning counts remain 15.

### 4.3 Legal content review status

The legal/content review has **not** been performed. A review packet was prepared at
[`rental-legal-content-review-packet.md`](rental-legal-content-review-packet.md) with 21 questions
(LRQ-01 to LRQ-21), and a session agenda is at
[`rental-legal-review-agenda.md`](rental-legal-review-agenda.md). No reviewer has been assigned;
reviewer identity, qualification, review date and per-question decisions remain blank.

The [non-signatory preflight](rental-legal-content-preflight.md) records recommendations for all
21 questions, the applicable national sources, and findings from two fictional export sets. Its
overall recommendation is **MODIFY_AND_RECHECK**. Court-specific applicability is **undetermined**
because the target court and filing channel have not been specified.

| Finding | Issue | Affected document |
|---|---|---|
| PF-01 | Partial payment is followed by a blanket "至今未支付" statement | Civil complaint |
| PF-02 | Multiple defendants' signing capacity and payment obligations are not separated | Civil complaint |
| PF-03 | Default evidence suggestions are exported as confirmed evidence with "原件核对" | Evidence list |
| PF-04 | Service-address form covers multiple parties but has one signature block | Service-address confirmation |

```text
preflight_status:    PREFLIGHT_COMPLETE
overall_recommendation: MODIFY_AND_RECHECK
court_specific:      UNDETERMINED_TARGET_COURT_AND_CHANNEL_NOT_SPECIFIED
formal_review_status: NOT_PERFORMED
review_performed:    false
reviewer_assigned:   false
review_date:         null
legal_review_status: NOT_REQUESTED
```

The preflight is not a formal legal review and has no reviewer signature. The four findings are
triage records; PF-01 and PF-02 are covered by the separate scoped authorization below, while
PF-03 and PF-04 remain open and do not authorize implementation.

Candidate reviewer: **YGone** (name supplied by the project owner on 2026-11-26). Qualification,
independence and consent to review are not confirmed, so this is **not** an assignment. If YGone is
the project author, the governance policy prohibits self-review as the independent legal reviewer.

Blocking reason: no qualified legal reviewer has been assigned. The project cannot self-certify
legal content, and tests, documentation or commits are not legal review. The stage remains
`NOT_STARTED`; no legal conclusion or approval exists.

### 4.4 Scoped engineering authorization result

A scoped authorization covers **only** PF-01 and PF-02. It does not authorize template
adaptation, mapping approval, rights review or release.

| Finding | Status | Change summary |
|---|---|---|
| PF-01 | `FIXED_PENDING_RECHECK` | Rental payment status is now required; partial payment emits "已支付部分租金，尚欠上述金额" and never "至今未支付"; unknown uses a neutral reconciliation sentence. |
| PF-02 | `FIXED_PENDING_RECHECK` | Multiple defendants use obligation-based claims and facts; the rental page requires a per-defendant signing-role and payment-obligation description. |
| PF-03 | `OPEN` | Evidence-suggestion and "原件核对" issue remains out of scope. |
| PF-04 | `OPEN` | Service-address signature-block issue remains out of scope. |

The fix updates `models/case_model.py`, `views/pages/rental.py`,
`presenters/model_builder.py`, `drafts/schema.py` (schema v6 with a v5 migration) and
`views/draft_io.py`, with regression tests. The overall `implementation_authorization` remains
`NOT_AUTHORIZED`. Recheck samples are generated in
`test_samples/rental-pf01-pf02-recheck-2026-11-26/` (git-ignored); text-level verification passes,
while WPS/Word inspection and formal reviewer recheck remain pending.

---

## 5. Known legal and procedural questions

- Is the correct counterpart a generic lease dispute, a residential lease, a commercial lease,
  or another variant?
- Should the product remain a lessor-only arrears template, or also support a lessee plaintiff
  claiming delivery of the premises or return of the deposit?
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
| `SOURCE_DISCOVERY` | Locate candidate sources | `COMPLETE` | Source record with official URL and explicit nulls |
| `SOURCE_VERIFICATION` | Verify identity, version, hash and artifact | `COMPLETE` | `SOURCE_FILE_VERIFIED` with evidence |
| `TEXT_AND_STRUCTURE_COMPARISON` | Compare official elements with rental fields | `COMPLETE` | Written comparison of elements/sections/omissions |
| `CASE_MAPPING_REVIEW` | Decide counterpart mapping | `COMPLETE` | Mapping entries added only after source evidence |
| `LEGAL_CONTENT_REVIEW` | Review claims, facts and procedure (packet prepared) | `NOT_STARTED` | Documented legal/content decision |
| `RIGHTS_AND_REDISTRIBUTION_REVIEW` | Decide adaptation/redistribution rights | `BLOCKED` | Separate rights decision |
| `ENGINEERING_IMPLEMENTATION` | Implement scoped changes only (PF-01/PF-02 scoped fix implemented; overall implementation not authorized) | `NOT_AUTHORIZED` | Scoped engineering authorization |
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

The current stage is `LEGAL_CONTENT_REVIEW`. Three unapproved rental mapping entries exist; a legal
review packet is prepared, but no reviewer is assigned and no legal/content or rights review has
been performed. A scoped PF-01/PF-02 fix is implemented pending recheck; it does not complete the
legal review, approve a mapping or authorize further changes.

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

1. The central mapping now contains three unapproved rental entries; keep them
   `approval_status = NOT_REQUESTED` until legal/content and rights review are complete.
2. Keep the frozen five-case gap analysis, crosswalk and adaptation-plan counts unchanged.
3. Do not treat the existing rental implementation as legally reviewed because tests pass.
4. Treat `rental-text-and-structure-comparison.md` as evidence for mapping review, not as a mapping
   decision or legal approval.
5. Do not mark any rental mapping `MAPPING_REVIEWED` or `APPROVED` without a documented legal/content
   review and the required review evidence.
6. Do not implement any RCS gap without scoped engineering authorization.
7. Do not add an `APPROVED` mapping without a separately approved source, legal review and rights
   review.
8. Do not change rental document text under this package without scoped engineering authorization.
9. Record reviewer roles only when actual reviewers are assigned; do not invent names or dates.
10. Do not fill reviewer identity, qualification, date or per-question decisions in the legal review
    packet without an assigned qualified reviewer.
11. Preflight findings PF-01 to PF-04 are triage records, not legal review; do not implement them
    without scoped engineering authorization.
12. The scoped authorization covers only PF-01 and PF-02; do not extend it to PF-03, PF-04 or any
    other template change.

---

## 9. Related files

- `models/case_model.py` — `RentalCaseModel`
- `views/pages/rental.py` — rental wizard page
- `presenters/model_builder.py` — rental model assembly
- `drafts/schema.py` — rental draft fields and flags (schema v6)
- `views/draft_io.py` — draft capture/restore
- `utils/doc_generator.py` — shared DOCX renderer
- `utils/evidence_library.py` — rental evidence suggestions
- `utils/facts_examples.py` — rental fact exemplars
- `tests/test_rental_case.py` — rental engineering tests
- `rental-text-and-structure-comparison.md` — official/current element comparison and gap register
- `rental-legal-content-review-packet.md` — legal/content review packet (no reviewer assigned)
- `rental-legal-review-agenda.md` — reviewer agenda and blank decision checklist (no reviewer assigned)
- `rental-legal-content-preflight.md` — non-signatory preflight over 21 questions and four output findings
- `docs/legal-template-governance/case-template-mapping.json` — central registry (15 original + 3 unapproved rental entries)
- `docs/legal-template-governance/governance.md` — change-control lifecycle and approval rules
- `docs/legal-template-governance/official-adaptation-planning/approval-gates.md` — gate sequence
