# 民间借贷纠纷 — `loan` — Adaptation Blueprint

> **Planning only. NOT_AUTHORIZED. No implementation, no legal review, no approval.**

## 1. Official candidate template

- 民事起诉状（民间借贷纠纷） — candidate only (`CANDIDATE_OFFICIAL_COMPLAINT`).
- Governance mapping: `map-loan-complaint` (`mapping_status = CANDIDATE_SOURCE_IDENTIFIED`).
- This blueprint does not assert that the application output conforms to it.

## 2. Source identity, hash and verified page range

- Source: `spc-2025-notice-pdf`, level A, `OFFICIAL_TEMPLATE`, `SOURCE_FILE_VERIFIED`.
- SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88`.
- Blank complaint form: physical pages **p134–p139** (printed 118–123).
- `SOURCE_FILE_VERIFIED` is a precondition, not an approval. No rights decision exists.

## 3. Existing application behaviour

叙事式：当事人栏 → 诉讼请求（本金/利息/诉讼费）→ 事实与理由（借款发生、交付、借条三态、利率、催款）→ 此致/落款。

The complaint renderer is shared by all five categories; only the claim list and the facts narrative differ.

## 4. Relevant crosswalk IDs (45)

`cw-0001-loan`, `cw-0002-loan`, `cw-0003-loan`, `cw-0004-loan`, `cw-0005-loan`, `cw-0006-loan`, `cw-0007-loan`, `cw-0008-loan`, `cw-0009-loan`, `cw-0010-loan`, `cw-0011-loan`, `cw-0012-loan`, `cw-0013-loan`, `cw-0014-loan`, `cw-0015-loan`, `cw-0016-loan`, `cw-0017-loan`, `cw-0018-loan`, `cw-0019-loan`, `cw-0020-loan`, `cw-0021-loan`, `cw-0022-loan`, `cw-0023-loan`, `cw-0024-loan`, `cw-0025-loan`, `cw-0026-loan`, `cw-0027-loan`, `cw-0028-loan`, `cw-0029-loan`, `cw-0030-loan`, `cw-0031-loan`, `cw-0032-loan`, `cw-0033-loan`, `cw-0034-loan`, `cw-0035-loan`, `cw-0036-loan`, `cw-0037-loan`, `cw-0038-loan`, `cw-0039-loan`, `cw-0040-loan`, `cw-0186-loan`, `cw-0191-loan`, `cw-0192-loan`, `cw-0193-loan`, `cw-0194-loan`

## 5. Linked gap IDs (27)

| Gap | Severity | Priority | Category |
|---|---|---|---|
| `GAP-LOAN-INTEREST-BASIS` | HIGH | P0 | CALCULATION_RISK |
| `GAP-LOAN-REPAYMENT-STATUS` | HIGH | P0 | MISSING_INPUT |
| `GAP-EVIDENCE-STANDALONE` | MEDIUM | P2 | EVIDENCE_PRESENTATION |
| `GAP-JURISDICTION-CLAUSE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LEGAL-BASIS` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-LOAN-ACCELERATION` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LOAN-ASOF-DATE` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-LOAN-OVERDUE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LOAN-SECURITY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-LOAN-TERM` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PARTY-IDENTITY-DETAILS` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-REPRESENTATIVE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-THIRD-PARTY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-COURT-FEE-CONDITIONAL` | LOW | P2 | CONDITIONALITY_DIFFERENCE |
| `GAP-ENFORCEMENT-COST` | LOW | P3 | MISSING_OUTPUT |
| `GAP-ID-TYPE` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-LOAN-CONTRACT-FORMATION` | LOW | P2 | MISSING_INPUT |
| `GAP-LOAN-PRINCIPAL-AMOUNT` | LOW | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-LOAN-REPAYMENT-METHOD` | LOW | P2 | MISSING_INPUT |
| `GAP-LOAN-ROLE-LABELLING` | LOW | P3 | SEMANTIC_DIFFERENCE |
| `GAP-MEDIATION-PREFERENCE` | LOW | P3 | PROCEDURAL_APPLICABILITY |
| `GAP-ORG-REGISTRATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-OTHER-CLAIMS` | LOW | P3 | MISSING_INPUT |
| `GAP-PARTY-RESIDENCE` | LOW | P2 | MISSING_INPUT |
| `GAP-PRESERVATION` | LOW | P2 | MISSING_INPUT |
| `GAP-SOURCE-VERSION` | LOW | P3 | SOURCE_VERIFICATION_GAP |
| `GAP-TOTAL-AMOUNT` | LOW | P2 | MISSING_OUTPUT |

## 6. Existing confirmed direct matches

| Official element | Application field(s) | Mechanism |
|---|---|---|
| `loan.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` |
| `loan.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` |
| `loan.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` |
| `loan.closing.signature` | — | `STATIC_RENDERING` |
| `loan.closing.date` | — | `STATIC_RENDERING` |

## 7. Missing fields (23 elements with no application counterpart)

- `loan.party.plaintiff.identity_details` — 原告性别/出生日期/民族/工作单位/职务
- `loan.party.plaintiff.residence` — 原告经常居住地
- `loan.party.plaintiff.agent` — 委托诉讼代理人有无及姓名/单位/职务/电话/代理权限
- `loan.party.third_party` — 第三人（自然人/法人、非法人组织）身份与登记信息
- `loan.procedure.jurisdiction_agreement` — 有无仲裁或法院管辖约定及条款内容
- `loan.procedure.preservation` — 是否已经诉前保全及保全法院/时间/案号
- `loan.procedure.other_claims` — 其他请求（自由表述）
- `loan.procedure.total_amount` — 标的总额
- `loan.closing.legal_basis` — 请求依据（写明法律及司法解释具体条文）
- `loan.mediation.preference` — 调解认知、先行调解好处认知、是否考虑先行调解
- `loan.claim.acceleration` — 是否要求提前还款（加速到期）或解除合同
- `loan.claim.security` — 是否主张担保权利
- `loan.claim.enforcement_cost` — 是否主张实现债权的费用
- `loan.fact.contract_formation` — 借款合同签订情况（名称、编号、时间、地点）
- `loan.fact.term` — 借款期限（是否到期、约定期限起止）
- `loan.fact.repayment_method` — 还款方式（到期一次性/按月/按季/按年计息等）
- `loan.fact.repayment_status` — 还款情况（已还本金、已还利息、还息至）
- `loan.fact.overdue` — 是否存在逾期还款及逾期时间
- `loan.fact.security_contract` — 是否签订物的担保（抵押、质押）合同
- `loan.fact.guarantor` — 担保人、担保物
- `loan.fact.max_security` — 是否最高额担保及担保债权确定时间/额度
- `loan.fact.registration` — 是否办理抵押、质押登记（正式/预告）
- `loan.fact.guarantee_contract` — 是否签订保证合同

## 8. Partial mappings (10)

| Official element | Application field(s) | Gap(s) |
|---|---|---|
| `loan.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-ID-TYPE` |
| `loan.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-PARTY-IDENTITY-DETAILS` |
| `loan.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-ORG-REGISTRATION` |
| `loan.evidence.list` | `shared.evidence.rows` | `GAP-EVIDENCE-STANDALONE` |
| `loan.claim.principal` | `loan.principal` | `GAP-LOAN-ASOF-DATE` |
| `loan.claim.interest` | `loan.interest_rate`, `loan.interest_start_date` | `GAP-LOAN-ASOF-DATE`, `GAP-LOAN-INTEREST-BASIS` |
| `loan.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-LOAN-ROLE-LABELLING` |
| `loan.fact.principal_amount` | `loan.principal`, `loan.payment_method` | `GAP-LOAN-PRINCIPAL-AMOUNT` |
| `loan.fact.interest_rate` | `loan.interest_rate` | `GAP-LOAN-INTEREST-BASIS` |
| `loan.fact.disbursement_time` | `loan.loan_date` | `GAP-LOAN-PRINCIPAL-AMOUNT` |

## 9. Semantic and conditional mismatches

- `loan.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 10. Required legal review

- Whether the interest basis, period unit and the “至实际清偿之日” option must be captured.
- Whether the current interest estimate is acceptable, and who verifies the rate.
- How partial repayment must be captured so a full-amount claim is never asserted by default.
- Whether an acceleration/termination request must be capturable.
- Whether loan contract-formation particulars (name, number, date, place) are required.

## 11. Required source / version review

- Re-verify the hash and the per-category page range.
- Confirm whether a later authoritative revision exists.
- Confirm the form is the correct counterpart for a generic private-lending claim.

## 12. Required rights review

- Whether the application may reproduce the official element structure at all.
- Whether extracted field labels may be stored in the repository.
- Whether adapted material may be redistributed with the installer.

## 13. Potential UI changes (design input only)

- Add an optional repayment-history group (amounts repaid, interest paid to a date).
- Separate agreed principal from actually provided principal (both optional).
- Add an optional loan-term group (due date or term).
- Add an optional overdue/acceleration indicator, defaulting to UNKNOWN.
- Add an optional security/guarantee group.

## 14. Potential Model changes (design input only)

- Attributes for repayment history, agreed vs provided principal, term, overdue state and security.
- No change to the existing interest computation; the basis remains review-only.

## 15. Potential Presenter changes (design input only)

- Map the new optional fields in build_case_model; keep preview and export on one model.
- Do not alter existing field mappings.

## 16. Potential DOCX structure changes (design input only)

- Keep the narrative layout; extend the facts paragraph with the newly captured facts.
- Do not insert any legal-basis text automatically.

## 17. Calculation impacts

Interest basis and repayment status are review blockers; no calculation change is proposed.

## 18. Factual-integrity safeguards

- Never infer “no repayment” from an empty repayment field.
- Interest stays an estimate with an explicit manual-verification note.
- IOU and demand remain conditional on user confirmation.

## 19. Required new test categories

- Repayment-history present/absent; partial repayment; zero repayment amount.
- Agreed vs provided principal mismatch.
- Interest with/without rate and start date.
- Acceleration flag UNKNOWN/TRUE/FALSE.

## 20. Pilot suitability

- Ranking: 5th of 5 — two HIGH gaps and the largest monetary-calculation surface.
- See `../pilot-selection.md`. No pilot is implementation-ready.

## 21. Implementation blockers

- GAP-LOAN-INTEREST-BASIS and GAP-LOAN-REPAYMENT-STATUS are HIGH and unresolved.
- The interest basis and the repayment-history model are unreviewed.
- No legal, mapping, source or rights review has been performed.
- Readiness classification: `LEGAL_REVIEW_REQUIRED`.
- Recommended next action: Complete a legal/content review of the 民间借贷纠纷 element set and of the interest-basis and repayment-history questions before any engineering design.

## 22. Explicit no-authorization statement

> The `loan` adaptation blueprint is **NOT_AUTHORIZED**. Every proposed change above is a
> design input for a future, separately reviewed decision. No source, mapping, legal or rights
> approval exists, and no production document may change on the basis of this document.
