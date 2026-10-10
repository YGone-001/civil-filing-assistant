# 劳动争议纠纷 — `labor` — Adaptation Blueprint

> **Planning only. NOT_AUTHORIZED. No implementation, no legal review, no approval.**

## 1. Official candidate template

- 民事起诉状（劳动争议纠纷） — candidate only (`CANDIDATE_OFFICIAL_COMPLAINT`).
- Governance mapping: `map-labor-complaint` (`mapping_status = CANDIDATE_SOURCE_IDENTIFIED`).
- This blueprint does not assert that the application output conforms to it.

## 2. Source identity, hash and verified page range

- Source: `spc-2025-notice-pdf`, level A, `OFFICIAL_TEMPLATE`, `SOURCE_FILE_VERIFIED`.
- SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88`.
- Blank complaint form: physical pages **p248–p251** (printed 232–235).
- `SOURCE_FILE_VERIFIED` is a precondition, not an approval. No rights decision exists.

## 3. Existing application behaviour

叙事式：当事人栏 → 诉讼请求（欠薪/加班费/二倍工资/诉讼费）→ 事实与理由（入职、岗位、工资、欠薪区间、加班、未签合同）→ 此致/落款。

The complaint renderer is shared by all five categories; only the claim list and the facts narrative differ.

## 4. Relevant crosswalk IDs (36)

`cw-0116-labor`, `cw-0117-labor`, `cw-0118-labor`, `cw-0119-labor`, `cw-0120-labor`, `cw-0121-labor`, `cw-0122-labor`, `cw-0123-labor`, `cw-0124-labor`, `cw-0125-labor`, `cw-0126-labor`, `cw-0127-labor`, `cw-0128-labor`, `cw-0129-labor`, `cw-0130-labor`, `cw-0131-labor`, `cw-0132-labor`, `cw-0133-labor`, `cw-0134-labor`, `cw-0135-labor`, `cw-0136-labor`, `cw-0137-labor`, `cw-0138-labor`, `cw-0139-labor`, `cw-0140-labor`, `cw-0141-labor`, `cw-0142-labor`, `cw-0143-labor`, `cw-0144-labor`, `cw-0145-labor`, `cw-0146-labor`, `cw-0147-labor`, `cw-0148-labor`, `cw-0149-labor`, `cw-0189-labor`, `cw-0198-labor`

## 5. Linked gap IDs (24)

| Gap | Severity | Priority | Category |
|---|---|---|---|
| `GAP-LABOR-ARBITRATION` | HIGH | P0 | PROCEDURAL_APPLICABILITY |
| `GAP-LABOR-AMOUNT-ASOF` | MEDIUM | P0 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-CLAIM-SCOPE` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-LABOR-CONTRACT-FORMATION` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-DOUBLE-WAGE` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-EVIDENCE-STANDALONE` | MEDIUM | P2 | EVIDENCE_PRESENTATION |
| `GAP-LABOR-JURISDICTION-CLAUSE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LABOR-LEGAL-BASIS` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-LABOR-PARTY-IDENTITY-DETAILS` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LABOR-PERFORMANCE-DETAIL` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-REPRESENTATIVE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LABOR-THIRD-PARTY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LABOR-COURT-FEE-CONDITIONAL` | LOW | P2 | CONDITIONALITY_DIFFERENCE |
| `GAP-LABOR-ID-TYPE` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-MEDIATION-PREFERENCE` | LOW | P3 | PROCEDURAL_APPLICABILITY |
| `GAP-LABOR-ORG-REGISTRATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-OTHER-CLAIMS` | LOW | P3 | MISSING_INPUT |
| `GAP-LABOR-OVERTIME` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-PARTY-RESIDENCE` | LOW | P2 | MISSING_INPUT |
| `GAP-LABOR-PRESERVATION` | LOW | P2 | MISSING_INPUT |
| `GAP-LABOR-TERMINATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-LABOR-TOTAL-AMOUNT` | LOW | P2 | MISSING_OUTPUT |
| `GAP-LABOR-WORK-INJURY` | LOW | P3 | MISSING_INPUT |
| `GAP-LABOR-OTHER-FACTS` | INFORMATIONAL | P3 | PROCEDURAL_APPLICABILITY |

## 6. Existing confirmed direct matches

| Official element | Application field(s) | Mechanism |
|---|---|---|
| `labor.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` |
| `labor.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` |
| `labor.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` |
| `labor.closing.signature` | — | `STATIC_RENDERING` |
| `labor.closing.date` | — | `STATIC_RENDERING` |

## 7. Missing fields (16 elements with no application counterpart)

- `labor.party.plaintiff.identity_details` — 原告性别/出生日期/民族/工作单位/职务
- `labor.party.plaintiff.residence` — 原告经常居住地
- `labor.party.plaintiff.agent` — 委托诉讼代理人有无及姓名/单位/职务/电话/代理权限
- `labor.party.third_party` — 第三人（自然人/法人、非法人组织）身份与登记信息
- `labor.procedure.jurisdiction_agreement` — 有无仲裁或法院管辖约定及条款内容
- `labor.procedure.preservation` — 是否已经诉前保全及保全法院/时间/案号
- `labor.procedure.other_claims` — 其他请求（自由表述）
- `labor.procedure.total_amount` — 标的总额
- `labor.closing.legal_basis` — 请求依据（写明法律及司法解释具体条文）
- `labor.mediation.preference` — 调解认知、先行调解好处认知、是否考虑先行调解
- `labor.claim.annual_leave` — 是否主张未休年休假工资及明细
- `labor.claim.termination_compensation` — 是否主张解除劳动合同经济补偿及明细
- `labor.claim.illegal_termination` — 是否主张违法解除劳动合同赔偿金及明细
- `labor.fact.work_injury` — 工伤情况（时间、认定、伤残等级、费用）
- `labor.fact.arbitration` — 劳动仲裁相关情况（申请时间、请求、仲裁文书、结果）
- `labor.fact.other` — 其他相关情况（如是否是农民工）

## 8. Partial mappings (11)

| Official element | Application field(s) | Gap(s) |
|---|---|---|
| `labor.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-LABOR-ID-TYPE` |
| `labor.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-LABOR-PARTY-IDENTITY-DETAILS` |
| `labor.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-LABOR-ORG-REGISTRATION` |
| `labor.evidence.list` | `shared.evidence.rows` | `GAP-LABOR-EVIDENCE-STANDALONE` |
| `labor.claim.wages` | `labor.unpaid_months`, `labor.monthly_salary` | `GAP-LABOR-AMOUNT-ASOF` |
| `labor.claim.double_wage` | `labor.is_no_contract` | `GAP-LABOR-DOUBLE-WAGE` |
| `labor.claim.overtime` | `labor.overtime` | `GAP-LABOR-OVERTIME` |
| `labor.claim.social_insurance_loss` | `labor.social_sec_info` | `GAP-LABOR-CLAIM-SCOPE` |
| `labor.fact.contract_formation` | `labor.is_no_contract` | `GAP-LABOR-CONTRACT-FORMATION` |
| `labor.fact.performance` | `labor.emp_join_date`, `labor.job_title`, `labor.monthly_salary` | `GAP-LABOR-PERFORMANCE-DETAIL` |
| `labor.fact.termination` | `labor.emp_term_date` | `GAP-LABOR-TERMINATION` |

## 9. Semantic and conditional mismatches

- `labor.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 10. Required legal review

- Which procedural posture applies: arbitration application, court complaint, or post-arbitration litigation.
- Whether the located litigation-stage form is the correct counterpart at all.
- Whether arbitration particulars (date, request, outcome) must be captured.
- Whether double-wage and overtime detail must be captured.
- Whether the four unimplemented claim types (annual leave, social-insurance loss, termination compensation, illegal-termination damages) are in scope.

## 11. Required source / version review

- Determine whether the correct counterpart is this form or another official document.
- Re-verify the hash and the per-category page range.
- Confirm whether a later authoritative revision exists.

## 12. Required rights review

- Whether form structure may be reproduced.
- Whether labels may be stored.
- Whether adapted material may be redistributed.

## 13. Potential UI changes (design input only)

- No UI change may be designed until the procedural posture is resolved.
- If litigation is confirmed: optional arbitration-particulars group.
- Optional employment-contract formation group; optional double-wage and overtime detail.

## 14. Potential Model changes (design input only)

- Attributes only after the posture decision; the whole-month salary model stays unchanged.

## 15. Potential Presenter changes (design input only)

- No change until the posture decision.

## 16. Potential DOCX structure changes (design input only)

- No change until the posture decision.

## 17. Calculation impacts

Wage and overtime models unchanged; no calculation change is proposed.

## 18. Factual-integrity safeguards

- Arbitration prerequisites must never be asserted by the application.
- Unparseable periods keep the manual-confirmation placeholder.
- Double-wage is claimed only when the user confirms it.

## 19. Required new test categories

- Posture-dependent tests only after the posture decision.
- Partial-period placeholder; double-wage UNKNOWN/TRUE/FALSE.

## 20. Pilot suitability

- Ranking: 5th of 5 — the procedural posture is unresolved, so the target form itself is uncertain.
- See `../pilot-selection.md`. No pilot is implementation-ready.

## 21. Implementation blockers

- GAP-LABOR-ARBITRATION is HIGH and unresolved.
- Do not choose a litigation template merely because the application exports a civil complaint.
- No legal, mapping, source or rights review has been performed.
- Readiness classification: `PROCEDURAL_REVIEW_REQUIRED`.
- Recommended next action: Determine the correct procedural posture (arbitration application vs court complaint vs post-arbitration litigation) before any engineering design.

## 22. Explicit no-authorization statement

> The `labor` adaptation blueprint is **NOT_AUTHORIZED**. Every proposed change above is a
> design input for a future, separately reviewed decision. No source, mapping, legal or rights
> approval exists, and no production document may change on the basis of this document.
