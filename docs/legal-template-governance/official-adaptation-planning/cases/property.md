# 物业服务合同纠纷 — `property` — Adaptation Blueprint

> **Planning only. NOT_AUTHORIZED. No implementation, no legal review, no approval.**

## 1. Official candidate template

- 民事起诉状（物业服务合同纠纷） — candidate only (`CANDIDATE_OFFICIAL_COMPLAINT`).
- Governance mapping: `map-property-complaint` (`mapping_status = CANDIDATE_SOURCE_IDENTIFIED`).
- This blueprint does not assert that the application output conforms to it.

## 2. Source identity, hash and verified page range

- Source: `spc-2025-notice-pdf`, level A, `OFFICIAL_TEMPLATE`, `SOURCE_FILE_VERIFIED`.
- SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88`.
- Blank complaint form: physical pages **p233–p236** (printed 217–220).
- `SOURCE_FILE_VERIFIED` is a precondition, not an approval. No rights decision exists.

## 3. Existing application behaviour

叙事式：当事人栏 → 诉讼请求（物业费/违约金/诉讼费）→ 事实与理由（服务主张、待核对身份、费标准、欠费、催缴）→ 此致/落款。

The complaint renderer is shared by all five categories; only the claim list and the facts narrative differ.

## 4. Relevant crosswalk IDs (36)

`cw-0082-property`, `cw-0083-property`, `cw-0084-property`, `cw-0085-property`, `cw-0086-property`, `cw-0087-property`, `cw-0088-property`, `cw-0089-property`, `cw-0090-property`, `cw-0091-property`, `cw-0092-property`, `cw-0093-property`, `cw-0094-property`, `cw-0095-property`, `cw-0096-property`, `cw-0097-property`, `cw-0098-property`, `cw-0099-property`, `cw-0100-property`, `cw-0101-property`, `cw-0102-property`, `cw-0103-property`, `cw-0104-property`, `cw-0105-property`, `cw-0106-property`, `cw-0107-property`, `cw-0108-property`, `cw-0109-property`, `cw-0110-property`, `cw-0111-property`, `cw-0112-property`, `cw-0113-property`, `cw-0114-property`, `cw-0115-property`, `cw-0188-property`, `cw-0197-property`

## 5. Linked gap IDs (22)

| Gap | Severity | Priority | Category |
|---|---|---|---|
| `GAP-PROPERTY-AMOUNT-ASOF` | MEDIUM | P0 | PARTIAL_FIELD_COVERAGE |
| `GAP-PROPERTY-EVIDENCE-STANDALONE` | MEDIUM | P2 | EVIDENCE_PRESENTATION |
| `GAP-PROPERTY-JURISDICTION-CLAUSE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PROPERTY-OWNER` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PROPERTY-PARTY-IDENTITY-DETAILS` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PROPERTY-PENALTY-AMOUNT` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-PROPERTY-REPRESENTATIVE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PROPERTY-TERM-SEMANTICS` | MEDIUM | P2 | SEMANTIC_DIFFERENCE |
| `GAP-PROPERTY-THIRD-PARTY` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-PROPERTY-CONTRACT-FORMATION` | LOW | P2 | MISSING_INPUT |
| `GAP-PROPERTY-COURT-FEE-CONDITIONAL` | LOW | P2 | CONDITIONALITY_DIFFERENCE |
| `GAP-PROPERTY-ID-TYPE` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-PROPERTY-LEGAL-BASIS` | LOW | P2 | MISSING_OUTPUT |
| `GAP-PROPERTY-MEDIATION-PREFERENCE` | LOW | P3 | PROCEDURAL_APPLICABILITY |
| `GAP-PROPERTY-ORG-REGISTRATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-PROPERTY-OTHER-CLAIMS` | LOW | P3 | MISSING_INPUT |
| `GAP-PROPERTY-PARTY-RESIDENCE` | LOW | P2 | MISSING_INPUT |
| `GAP-PROPERTY-PAYMENT-METHOD` | LOW | P2 | MISSING_INPUT |
| `GAP-PROPERTY-PRESERVATION` | LOW | P2 | MISSING_INPUT |
| `GAP-PROPERTY-ROLE-LABELLING` | LOW | P3 | SEMANTIC_DIFFERENCE |
| `GAP-PROPERTY-TOTAL-AMOUNT` | LOW | P2 | MISSING_OUTPUT |
| `GAP-PROPERTY-SCOPE` | INFORMATIONAL | P3 | PROCEDURAL_APPLICABILITY |

## 6. Existing confirmed direct matches

| Official element | Application field(s) | Mechanism |
|---|---|---|
| `property.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` |
| `property.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` |
| `property.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` |
| `property.closing.signature` | — | `STATIC_RENDERING` |
| `property.closing.date` | — | `STATIC_RENDERING` |
| `property.claim.fee` | `property.total_input`, `property.house_area`, `property.fee_rate` | `USER_INPUT_FIELD` |
| `property.fact.fee_standard` | `property.fee_rate` | `USER_INPUT_FIELD` |
| `property.fact.demand` | `property.demand_record` | `USER_INPUT_FIELD` |

## 7. Missing fields (14 elements with no application counterpart)

- `property.party.plaintiff.identity_details` — 原告性别/出生日期/民族/工作单位/职务
- `property.party.plaintiff.residence` — 原告经常居住地
- `property.party.plaintiff.agent` — 委托诉讼代理人有无及姓名/单位/职务/电话/代理权限
- `property.party.third_party` — 第三人（自然人/法人、非法人组织）身份与登记信息
- `property.procedure.jurisdiction_agreement` — 有无仲裁或法院管辖约定及条款内容
- `property.procedure.preservation` — 是否已经诉前保全及保全法院/时间/案号
- `property.procedure.other_claims` — 其他请求（自由表述）
- `property.procedure.total_amount` — 标的总额
- `property.closing.legal_basis` — 请求依据（写明法律及司法解释具体条文）
- `property.mediation.preference` — 调解认知、先行调解好处认知、是否考虑先行调解
- `property.fact.contract_formation` — 物业服务合同或前期物业服务合同签订情况
- `property.fact.payment_method` — 约定的物业费支付方式
- `property.fact.penalty_amount` — 被告应付违约金数额及计算方式
- `property.fact.other` — 其他需要说明的内容

## 8. Partial mappings (9)

| Official element | Application field(s) | Gap(s) |
|---|---|---|
| `property.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-PROPERTY-ID-TYPE` |
| `property.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-PROPERTY-PARTY-IDENTITY-DETAILS` |
| `property.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-PROPERTY-ORG-REGISTRATION` |
| `property.evidence.list` | `shared.evidence.rows` | `GAP-PROPERTY-EVIDENCE-STANDALONE` |
| `property.claim.penalty` | `property.late_fee_logic` | `GAP-PROPERTY-PENALTY-AMOUNT` |
| `property.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-PROPERTY-ROLE-LABELLING` |
| `property.fact.project` | `property.property_addr`, `property.house_area` | `GAP-PROPERTY-OWNER` |
| `property.fact.penalty_standard` | `property.late_fee_logic` | `GAP-PROPERTY-PENALTY-AMOUNT` |
| `property.fact.arrears_amount` | `property.total_input`, `property.house_area`, `property.fee_rate` | `GAP-PROPERTY-AMOUNT-ASOF` |

## 9. Semantic and conditional mismatches

- `property.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。
- `property.fact.service_term` → `SEMANTIC_MISMATCH`: 应用起止日期为欠费期间；官方为约定的服务期限。

## 10. Required legal review

- Whether the official element set covers a pure fee-collection claim.
- Whether the arrears period may stand in for the agreed service term.
- Whether the owner/occupier identity must be captured or may stay a claimed relationship.
- Whether a penalty amount (not just a formula) must be captured.

## 11. Required source / version review

- Re-verify the hash and the per-category page range.
- Confirm the category is a single unambiguous form (no competing variant).
- Confirm whether a later authoritative revision exists.

## 12. Required rights review

- Whether form structure may be reproduced.
- Whether labels may be stored.
- Whether adapted material may be redistributed.

## 13. Potential UI changes (design input only)

- Add an optional property-service contract formation group (name, number, dates).
- Add an optional ownership/occupancy detail group, kept as a claimed relationship.
- Add an optional payment-method field.
- Add an optional penalty amount field.

## 14. Potential Model changes (design input only)

- Attributes for formation particulars, ownership detail, payment method and penalty amount.
- Keep the area × rate × whole-month model unchanged, including the partial-period warning.

## 15. Potential Presenter changes (design input only)

- Map the new optional fields; change nothing existing.

## 16. Potential DOCX structure changes (design input only)

- Keep the narrative layout; preserve the existing “人工核对” framing.

## 17. Calculation impacts

No calculation change; the partial-period warning and the user-total precedence stay intact.

## 18. Factual-integrity safeguards

- The service relationship stays a claim, not an established fact.
- No demand frequency or bad-faith assertion is fabricated.
- A user-entered total is never silently overwritten.

## 19. Required new test categories

- Formation particulars present/absent; payment method present/absent.
- Penalty formula vs amount; partial-period warning still emitted.
- Ownership detail remains a claimed relationship.

## 20. Pilot suitability

- Ranking: 1st of 5 — unambiguous single category, no HIGH gap, narrow claim scope.
- See `../pilot-selection.md`. No pilot is implementation-ready.

## 21. Implementation blockers

- The fee-collection scope question is unresolved.
- No legal, mapping, source or rights review has been performed.
- Readiness classification: `LEGAL_REVIEW_REQUIRED`.
- Recommended next action: Review whether the official element set covers a pure fee-collection claim and whether the arrears period may stand in for the service term.

## 22. Explicit no-authorization statement

> The `property` adaptation blueprint is **NOT_AUTHORIZED**. Every proposed change above is a
> design input for a future, separately reviewed decision. No source, mapping, legal or rights
> approval exists, and no production document may change on the basis of this document.
