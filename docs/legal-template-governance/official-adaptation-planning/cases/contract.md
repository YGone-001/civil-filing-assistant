# 买卖合同纠纷 — `contract` — Adaptation Blueprint

> **Planning only. NOT_AUTHORIZED. No implementation, no legal review, no approval.**

## 1. Official candidate template

- 民事起诉状（买卖合同纠纷） — candidate only (`CANDIDATE_OFFICIAL_COMPLAINT`).
- Governance mapping: `map-contract-complaint` (`mapping_status = CANDIDATE_SOURCE_IDENTIFIED`).
- This blueprint does not assert that the application output conforms to it.

## 2. Source identity, hash and verified page range

- Source: `spc-2025-notice-pdf`, level A, `OFFICIAL_TEMPLATE`, `SOURCE_FILE_VERIFIED`.
- SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88`.
- Blank complaint form: physical pages **p71–p76** (printed 55–60).
- `SOURCE_FILE_VERIFIED` is a precondition, not an approval. No rights decision exists.

## 3. Existing application behaviour

叙事式：当事人栏 → 诉讼请求（货款本金/违约金/诉讼费）→ 事实与理由（合同、交货三态、签收三态、欠款）→ 此致/落款。

The complaint renderer is shared by all five categories; only the claim list and the facts narrative differ.

## 4. Relevant crosswalk IDs (44)

`cw-0041-contract`, `cw-0042-contract`, `cw-0043-contract`, `cw-0044-contract`, `cw-0045-contract`, `cw-0046-contract`, `cw-0047-contract`, `cw-0048-contract`, `cw-0049-contract`, `cw-0050-contract`, `cw-0051-contract`, `cw-0052-contract`, `cw-0053-contract`, `cw-0054-contract`, `cw-0055-contract`, `cw-0056-contract`, `cw-0057-contract`, `cw-0058-contract`, `cw-0059-contract`, `cw-0060-contract`, `cw-0061-contract`, `cw-0062-contract`, `cw-0063-contract`, `cw-0064-contract`, `cw-0065-contract`, `cw-0066-contract`, `cw-0067-contract`, `cw-0068-contract`, `cw-0069-contract`, `cw-0070-contract`, `cw-0071-contract`, `cw-0072-contract`, `cw-0073-contract`, `cw-0074-contract`, `cw-0075-contract`, `cw-0076-contract`, `cw-0077-contract`, `cw-0078-contract`, `cw-0079-contract`, `cw-0080-contract`, `cw-0081-contract`, `cw-0187-contract`, `cw-0195-contract`, `cw-0196-contract`

## 5. Linked gap IDs (27)

| Gap | Severity | Priority | Category |
|---|---|---|---|
| `GAP-CONTRACT-AMOUNT-ASOF` | MEDIUM | P0 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-BUYER-CLAIMS` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-CONTRACT-DELIVERY-TERMS` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-EVIDENCE-STANDALONE` | MEDIUM | P2 | EVIDENCE_PRESENTATION |
| `GAP-CONTRACT-JURISDICTION-CLAUSE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-LEGAL-BASIS` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-CONTRACT-PARTY-IDENTITY-DETAILS` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-PAYMENT-TERMS` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-QUALITY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-REPRESENTATIVE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-SECURITY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-SUBJECT` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-THIRD-PARTY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-CONTRACT-COURT-FEE-CONDITIONAL` | LOW | P2 | CONDITIONALITY_DIFFERENCE |
| `GAP-CONTRACT-DELAY` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-DEMAND` | LOW | P2 | MISSING_INPUT |
| `GAP-CONTRACT-ENFORCEMENT-COST` | LOW | P3 | MISSING_OUTPUT |
| `GAP-CONTRACT-FORMATION` | LOW | P2 | MISSING_INPUT |
| `GAP-CONTRACT-ID-TYPE` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-MEDIATION-PREFERENCE` | LOW | P3 | PROCEDURAL_APPLICABILITY |
| `GAP-CONTRACT-ORG-REGISTRATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-OTHER-CLAIMS` | LOW | P3 | MISSING_INPUT |
| `GAP-CONTRACT-PARTY-RESIDENCE` | LOW | P2 | MISSING_INPUT |
| `GAP-CONTRACT-PENALTY-TERMS` | LOW | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-CONTRACT-PRESERVATION` | LOW | P2 | MISSING_INPUT |
| `GAP-CONTRACT-TOTAL-AMOUNT` | LOW | P2 | MISSING_OUTPUT |
| `GAP-ROLE-LABELLING` | LOW | P3 | SEMANTIC_DIFFERENCE |

## 6. Existing confirmed direct matches

| Official element | Application field(s) | Mechanism |
|---|---|---|
| `contract.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` |
| `contract.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` |
| `contract.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` |
| `contract.closing.signature` | — | `STATIC_RENDERING` |
| `contract.closing.date` | — | `STATIC_RENDERING` |
| `contract.claim.price` | `contract.unpaid_amount` | `USER_INPUT_FIELD` |

## 7. Missing fields (20 elements with no application counterpart)

- `contract.party.plaintiff.identity_details` — 原告性别/出生日期/民族/工作单位/职务
- `contract.party.plaintiff.residence` — 原告经常居住地
- `contract.party.plaintiff.agent` — 委托诉讼代理人有无及姓名/单位/职务/电话/代理权限
- `contract.party.third_party` — 第三人（自然人/法人、非法人组织）身份与登记信息
- `contract.procedure.jurisdiction_agreement` — 有无仲裁或法院管辖约定及条款内容
- `contract.procedure.preservation` — 是否已经诉前保全及保全法院/时间/案号
- `contract.procedure.other_claims` — 其他请求（自由表述）
- `contract.procedure.total_amount` — 标的总额
- `contract.closing.legal_basis` — 请求依据（写明法律及司法解释具体条文）
- `contract.mediation.preference` — 调解认知、先行调解好处认知、是否考虑先行调解
- `contract.claim.seller_breach` — 赔偿因卖方违约所受的损失（买方请求）
- `contract.claim.defect_liability` — 是否对标的物的瑕疵承担责任（修理/重作/更换/退货/减价）
- `contract.claim.performance_or_termination` — 要求继续履行或者解除合同
- `contract.claim.security` — 是否主张担保权利
- `contract.claim.enforcement_cost` — 是否主张实现债权的费用
- `contract.fact.quality_terms` — 合同约定的质量标准及检验方式、质量异议期限
- `contract.fact.demand` — 是否催促过履行及催促时间与方式
- `contract.fact.quality_dispute` — 标的物有无质量争议
- `contract.fact.nonconformity` — 质量规格或履行方式是否存在不符合约定的情况
- `contract.fact.negotiation` — 是否曾就标的物质量问题进行协商

## 8. Partial mappings (13)

| Official element | Application field(s) | Gap(s) |
|---|---|---|
| `contract.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-CONTRACT-ID-TYPE` |
| `contract.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-CONTRACT-PARTY-IDENTITY-DETAILS` |
| `contract.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-CONTRACT-ORG-REGISTRATION` |
| `contract.evidence.list` | `shared.evidence.rows` | `GAP-CONTRACT-EVIDENCE-STANDALONE` |
| `contract.claim.delay_interest` | `contract.penalty_amount`, `contract.penalty_calc_standard`, `contract.penalty_start_date` | `GAP-CONTRACT-AMOUNT-ASOF` |
| `contract.fact.contract_formation` | `contract.contract_name`, `contract.contract_date` | `GAP-CONTRACT-FORMATION` |
| `contract.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-ROLE-LABELLING` |
| `contract.fact.subject_matter` | `contract.product_name` | `GAP-CONTRACT-SUBJECT` |
| `contract.fact.price_payment_terms` | `contract.total_amount` | `GAP-CONTRACT-PAYMENT-TERMS` |
| `contract.fact.delivery_terms` | `contract.delivery_date`, `contract.is_delivered` | `GAP-CONTRACT-DELIVERY-TERMS` |
| `contract.fact.penalty_terms` | `contract.penalty_amount`, `contract.penalty_calc_standard` | `GAP-CONTRACT-PENALTY-TERMS` |
| `contract.fact.payment_delivery_status` | `contract.unpaid_amount`, `contract.is_delivered`, `contract.is_signed` | `GAP-CONTRACT-DELIVERY-TERMS` |
| `contract.fact.delay` | `contract.penalty_start_date` | `GAP-CONTRACT-DELAY` |

## 9. Semantic and conditional mismatches

- `contract.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 10. Required legal review

- Whether the generic 买卖合同纠纷 form is the correct counterpart or 房屋买卖合同纠纷 applies.
- Whether the demand (催告) element must be captured, and how it stays user-confirmed.
- Whether the penalty type (定金 vs 迟延履行违约金) must be distinguished.
- Whether contract-formation particulars (number, place, no-written-contract) are required.

## 11. Required source / version review

- Confirm which of the two sale-contract categories is the correct counterpart.
- Re-verify the hash and the per-category page range.
- Confirm whether a later authoritative revision exists.

## 12. Required rights review

- Whether form structure may be reproduced.
- Whether labels may be stored.
- Whether adapted material may be redistributed.

## 13. Potential UI changes (design input only)

- Add an optional demand-history group (date + method), never pre-filled.
- Add an optional explicit delay indicator, defaulting to UNKNOWN.
- Add optional contract-formation particulars (number, place, no-written-contract).
- Add an optional penalty-type selector.

## 14. Potential Model changes (design input only)

- Attributes for demand history, delay state and formation particulars.
- Preserve the delivery/receipt tri-state exactly as implemented.

## 15. Potential Presenter changes (design input only)

- Map the new optional fields; change nothing existing.

## 16. Potential DOCX structure changes (design input only)

- Keep the narrative layout; extend the facts paragraph only with user-supplied facts.

## 17. Calculation impacts

Penalty basis stays user-supplied; no calculation change is proposed.

## 18. Factual-integrity safeguards

- Do not restore the previously rejected unconditional demand assertion.
- Delivery and receipt stay tri-state; contradiction still blocks export.
- No official example text is emitted.

## 19. Required new test categories

- Demand supplied/absent; delay UNKNOWN/TRUE/FALSE.
- Delivery/receipt contradiction still blocks export.
- Penalty with/without basis.

## 20. Pilot suitability

- Ranking: 2nd of 5 — no HIGH gap, but the source-variant question is a source-selection risk.
- See `../pilot-selection.md`. No pilot is implementation-ready.

## 21. Implementation blockers

- The generic vs 房屋买卖 variant question is unresolved and could invalidate the mapping.
- No legal, mapping, source or rights review has been performed.
- Readiness classification: `LEGAL_REVIEW_REQUIRED`.
- Recommended next action: Resolve the generic 买卖合同纠纷 vs 房屋买卖合同纠纷 variant question and review the element set before any engineering design.

## 22. Explicit no-authorization statement

> The `contract` adaptation blueprint is **NOT_AUTHORIZED**. Every proposed change above is a
> design input for a future, separately reviewed decision. No source, mapping, legal or rights
> approval exists, and no production document may change on the basis of this document.
