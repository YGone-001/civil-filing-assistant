# Review Queue

**Status vocabulary:** every item below is `NOT_REQUESTED`. No reviewer has been named and no
approval date is recorded, because no review has occurred. Nothing here authorises implementation.

**Readiness vocabulary:** `ENGINEERING_DETAIL_AVAILABLE`, `LEGAL_REVIEW_REQUIRED`,
`SOURCE_VERIFICATION_REQUIRED`, `PROCEDURAL_SCOPE_UNRESOLVED`. Even an
`ENGINEERING_DETAIL_AVAILABLE` item remains blocked until the governance approval requirements in
`../governance.md` are satisfied.

---

## 1. Source verification questions

| ID | Case | Doc | Gap IDs | Source evidence | Application evidence | Proposed investigation | Review role | Prerequisites | Status | Readiness |
|---|---|---|---|---|---|---|---|---|---|---|
| RQ-01 | all | all | GAP-SOURCE-VERSION | notice 468671 + PDF hash PASS | — | Periodically re-check the issuing authority for a revised demonstration-text release; if the uploaded file changes, re-verify the hash and re-issue the ledger | Source verification | none | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |
| RQ-02 | all | all | GAP-ROUTE-ADDRESS-NO-COUNTERPART | `送达地址` = 0/975 pages | address form generator | Retrieve and verify other official materials (court service practice documents) with independent provenance before any equivalence claim | Source verification + legal | rights review | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |
| RQ-03 | all | all | GAP-ROUTE-EVIDENCE-STANDALONE | `证据清单` = 211 pages, section only | evidence-list generator | Determine whether an official standalone evidence-list document exists elsewhere | Source verification + legal | rights review | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |

## 2. Legal / content applicability questions

| ID | Case | Doc | Gap IDs | Proposed investigation | Review role | Status | Readiness |
|---|---|---|---|---|---|---|---|
| RQ-10 | loan | complaint | GAP-LOAN-INTEREST-BASIS, GAP-LOAN-ASOF-DATE | Whether the interest basis, period unit and "至实际清偿之日" option must be captured; whether the current estimate is acceptable | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-11 | contract | complaint | GAP-ROLE-LABELLING, GAP-CONTRACT-BUYER-CLAIMS | Whether seller/buyer role labelling and buyer-side claims are required for the generic sales scenario | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-12 | property | complaint | GAP-PROPERTY-TERM-SEMANTICS, GAP-PROPERTY-SCOPE | Whether the arrears period may stand in for the agreed service term; which official elements apply to a pure fee-collection claim | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-13 | divorce | complaint | GAP-DIVORCE-COMBINED-SCOPE, GAP-DIVORCE-DAMAGES, GAP-DIVORCE-VISITATION, GAP-DIVORCE-DEBT | Whether one official divorce form covers the combined relief, or whether variants are needed | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-14 | all | complaint | GAP-LEGAL-BASIS | Whether the complaint must cite specific statutory provisions, and who supplies them | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-15 | all | complaint | GAP-EVIDENCE-STANDALONE | Whether the standalone evidence list is acceptable to filing courts | Legal/content | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |

## 3. Missing UI inputs (candidate only — no implementation authorised)

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-20 | all | GAP-PARTY-IDENTITY-DETAILS, GAP-PARTY-RESIDENCE, GAP-ID-TYPE, GAP-REPRESENTATIVE | Assess whether gender/DOB/ethnicity/work unit/position/habitual residence/ID type/representative need capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-21 | all | GAP-THIRD-PARTY | Assess whether third-party modelling is required | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-22 | all | GAP-JURISDICTION-CLAUSE, GAP-PRESERVATION, GAP-MEDIATION-PREFERENCE, GAP-OTHER-CLAIMS | Assess procedural-preference capture | NOT_REQUESTED | PROCEDURAL_SCOPE_UNRESOLVED |
| RQ-23 | loan | GAP-LOAN-TERM, GAP-LOAN-REPAYMENT-METHOD, GAP-LOAN-REPAYMENT-STATUS, GAP-LOAN-OVERDUE, GAP-LOAN-SECURITY | Assess loan-term/repayment/security capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-24 | contract | GAP-CONTRACT-FORMATION, GAP-CONTRACT-SUBJECT, GAP-CONTRACT-PAYMENT-TERMS, GAP-CONTRACT-DELIVERY-TERMS, GAP-CONTRACT-QUALITY | Assess contract-detail and quality capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-25 | property | GAP-PROPERTY-OWNER, GAP-PROPERTY-PAYMENT-METHOD, GAP-PROPERTY-PENALTY-AMOUNT | Assess owner/payment/penalty capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-26 | labor | GAP-LABOR-PERFORMANCE-DETAIL, GAP-LABOR-TERMINATION, GAP-LABOR-WORK-INJURY | Assess employment-detail capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-27 | divorce | GAP-DIVORCE-MARRIAGE-FACTS, GAP-DIVORCE-PROPERTY-STRUCTURE | Assess marriage-fact and structured-property capture | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |

## 4. Existing field semantics requiring clarification

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-30 | property | GAP-PROPERTY-TERM-SEMANTICS | Confirm that `period_start`/`period_end` mean the arrears period and must not be reused as the service term | NOT_REQUESTED | ENGINEERING_DETAIL_AVAILABLE |
| RQ-31 | all | GAP-COURT-FEE-CONDITIONAL | Decide whether the court-fee claim stays unconditional | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-32 | contract | GAP-CONTRACT-DEMAND | Confirm that the contract complaint must never re-introduce an unconditional demand statement | NOT_REQUESTED | ENGINEERING_DETAIL_AVAILABLE |

## 5. Conditional rendering changes (candidate only)

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-40 | all | GAP-COURT-FEE-CONDITIONAL | If a conditional court-fee claim is required, design the field without weakening current output | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-41 | loan/contract/property/labor | GAP-LOAN-ASOF-DATE | Assess an explicit "as of" basis date for monetary claims | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |

## 6. Calculations needing review

| ID | RQ | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-50 | loan | GAP-LOAN-INTEREST-BASIS | Review the annual-rate assumption, the 365-day basis and the manual-review fallback | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-51 | labor | — | Review the whole-month unpaid-salary model and the partial-period placeholder | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-52 | property | — | Review the area × rate × whole-month model and the partial-period warning | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-53 | all | GAP-TOTAL-AMOUNT | Assess whether a claim total is required and how it should be computed | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |

## 7. DOCX structural adaptation candidates

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-60 | all | — | Decide whether any official form structure should be adopted, given the narrative-vs-element-based difference | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-61 | all | — | Confirm that the current font/margin/spacing constants are project conventions and not court requirements | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |

## 8. Evidence-list questions

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-70 | all | GAP-ROUTE-EVIDENCE-STANDALONE | Determine whether the official embedded evidence section implies specific columns or numbering | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |

## 9. Service-address form questions

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-80 | all | GAP-ROUTE-ADDRESS-NO-COUNTERPART | Identify the actual authority for a service-address confirmation form | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |

## 10. Procedural and jurisdictional questions

| ID | Case | Gap IDs | Proposed investigation | Status | Readiness |
|---|---|---|---|---|---|
| RQ-90 | labor | GAP-LABOR-ARBITRATION | Determine whether the official civil complaint is appropriate for each labour-remuneration posture (arbitration application, court complaint, post-arbitration litigation) | NOT_REQUESTED | PROCEDURAL_SCOPE_UNRESOLVED |
| RQ-91 | contract | — | Determine whether the generic `买卖合同纠纷` or the `房屋买卖合同纠纷` variant applies to a generic goods sale | NOT_REQUESTED | LEGAL_REVIEW_REQUIRED |
| RQ-92 | all | — | Determine local-court/jurisdiction-specific filing expectations | NOT_REQUESTED | SOURCE_VERIFICATION_REQUIRED |

---

## Implementation readiness summary

| Readiness | Items |
|---|---|
| `ENGINEERING_DETAIL_AVAILABLE` | RQ-30, RQ-32 |
| `LEGAL_REVIEW_REQUIRED` | RQ-10–RQ-15, RQ-20, RQ-21, RQ-23–RQ-27, RQ-31, RQ-40, RQ-41, RQ-50–RQ-53, RQ-60, RQ-70, RQ-91 |
| `SOURCE_VERIFICATION_REQUIRED` | RQ-01, RQ-02, RQ-03, RQ-61, RQ-80, RQ-92 |
| `PROCEDURAL_SCOPE_UNRESOLVED` | RQ-22, RQ-90 |

**No item in this queue is authorised for implementation.** Phase 1-C has not begun.
