# 离婚纠纷 — `divorce` — Adaptation Blueprint

> **Planning only. NOT_AUTHORIZED. No implementation, no legal review, no approval.**

## 1. Official candidate template

- 民事起诉状（离婚纠纷） — candidate only (`CANDIDATE_OFFICIAL_COMPLAINT`).
- Governance mapping: `map-divorce-complaint` (`mapping_status = CANDIDATE_SOURCE_IDENTIFIED`).
- This blueprint does not assert that the application output conforms to it.

## 2. Source identity, hash and verified page range

- Source: `spc-2025-notice-pdf`, level A, `OFFICIAL_TEMPLATE`, `SOURCE_FILE_VERIFIED`.
- SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88`.
- Blank complaint form: physical pages **p57–p60** (printed 41–44).
- `SOURCE_FILE_VERIFIED` is a precondition, not an approval. No rights decision exists.

## 3. Existing application behaviour

叙事式：当事人栏 → 诉讼请求（离婚/抚养/抚养费/财产分割/诉讼费）→ 事实与理由（结婚、子女、分居、离婚事由、感情破裂）→ 此致/落款。

The complaint renderer is shared by all five categories; only the claim list and the facts narrative differ.

## 4. Relevant crosswalk IDs (38)

`cw-0150-divorce`, `cw-0151-divorce`, `cw-0152-divorce`, `cw-0153-divorce`, `cw-0154-divorce`, `cw-0155-divorce`, `cw-0156-divorce`, `cw-0157-divorce`, `cw-0158-divorce`, `cw-0159-divorce`, `cw-0160-divorce`, `cw-0161-divorce`, `cw-0162-divorce`, `cw-0163-divorce`, `cw-0164-divorce`, `cw-0165-divorce`, `cw-0166-divorce`, `cw-0167-divorce`, `cw-0168-divorce`, `cw-0169-divorce`, `cw-0170-divorce`, `cw-0171-divorce`, `cw-0172-divorce`, `cw-0173-divorce`, `cw-0174-divorce`, `cw-0175-divorce`, `cw-0176-divorce`, `cw-0177-divorce`, `cw-0178-divorce`, `cw-0179-divorce`, `cw-0180-divorce`, `cw-0181-divorce`, `cw-0182-divorce`, `cw-0183-divorce`, `cw-0184-divorce`, `cw-0185-divorce`, `cw-0190-divorce`, `cw-0199-divorce`

## 5. Linked gap IDs (21)

| Gap | Severity | Priority | Category |
|---|---|---|---|
| `GAP-DIVORCE-COMBINED-SCOPE` | HIGH | P0 | PROCEDURAL_APPLICABILITY |
| `GAP-DIVORCE-CUSTODY-SUPPORT-DETAIL` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-DIVORCE-DAMAGES` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-DEBT` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-EVIDENCE-STANDALONE` | MEDIUM | P2 | EVIDENCE_PRESENTATION |
| `GAP-DIVORCE-JURISDICTION-CLAUSE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-LEGAL-BASIS` | MEDIUM | P2 | MISSING_OUTPUT |
| `GAP-DIVORCE-MARRIAGE-FACTS` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-DIVORCE-PARTY-IDENTITY-DETAILS` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-PROPERTY-STRUCTURE` | MEDIUM | P1 | PARTIAL_FIELD_COVERAGE |
| `GAP-DIVORCE-REPRESENTATIVE` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-VISITATION` | MEDIUM | P1 | MISSING_INPUT |
| `GAP-DIVORCE-COURT-FEE-CONDITIONAL` | LOW | P2 | CONDITIONALITY_DIFFERENCE |
| `GAP-DIVORCE-ID-TYPE` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-DIVORCE-MEDIATION-PREFERENCE` | LOW | P3 | PROCEDURAL_APPLICABILITY |
| `GAP-DIVORCE-ORG-REGISTRATION` | LOW | P2 | PARTIAL_FIELD_COVERAGE |
| `GAP-DIVORCE-OTHER-CLAIMS` | LOW | P3 | MISSING_INPUT |
| `GAP-DIVORCE-PARTY-RESIDENCE` | LOW | P2 | MISSING_INPUT |
| `GAP-DIVORCE-PRESERVATION` | LOW | P2 | MISSING_INPUT |
| `GAP-DIVORCE-TOTAL-AMOUNT` | LOW | P2 | MISSING_OUTPUT |
| `GAP-DIVORCE-OTHER-FACTS` | INFORMATIONAL | P3 | PROCEDURAL_APPLICABILITY |

## 6. Existing confirmed direct matches

| Official element | Application field(s) | Mechanism |
|---|---|---|
| `divorce.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` |
| `divorce.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` |
| `divorce.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` |
| `divorce.closing.signature` | — | `STATIC_RENDERING` |
| `divorce.closing.date` | — | `STATIC_RENDERING` |
| `divorce.claim.dissolution` | `divorce.marriage_date` | `USER_INPUT_FIELD` |

## 7. Missing fields (17 elements with no application counterpart)

- `divorce.party.plaintiff.identity_details` — 原告性别/出生日期/民族/工作单位/职务
- `divorce.party.plaintiff.residence` — 原告经常居住地
- `divorce.party.plaintiff.agent` — 委托诉讼代理人有无及姓名/单位/职务/电话/代理权限
- `divorce.procedure.jurisdiction_agreement` — 有无仲裁或法院管辖约定及条款内容
- `divorce.procedure.preservation` — 是否已经诉前保全及保全法院/时间/案号
- `divorce.procedure.other_claims` — 其他请求（自由表述）
- `divorce.procedure.total_amount` — 标的总额
- `divorce.closing.legal_basis` — 请求依据（写明法律及司法解释具体条文）
- `divorce.mediation.preference` — 调解认知、先行调解好处认知、是否考虑先行调解
- `divorce.claim.debt` — 夫妻共同债务（无债务/有债务及承担主体）
- `divorce.claim.visitation` — 探望权（行使主体、行使方式）
- `divorce.claim.damages_compensation` — 离婚损害赔偿／离婚经济补偿／离婚经济帮助及金额
- `divorce.claim.preservation` — 诉前保全情况
- `divorce.fact.debt` — 夫妻共同债务情况
- `divorce.fact.visitation` — 子女探望权情况（是否享有及行使方式的事由）
- `divorce.fact.damages` — 赔偿／补偿／经济帮助相关情况
- `divorce.fact.other` — 其他

## 8. Partial mappings (11)

| Official element | Application field(s) | Gap(s) |
|---|---|---|
| `divorce.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-DIVORCE-ID-TYPE` |
| `divorce.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-DIVORCE-PARTY-IDENTITY-DETAILS` |
| `divorce.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-DIVORCE-ORG-REGISTRATION` |
| `divorce.evidence.list` | `shared.evidence.rows` | `GAP-DIVORCE-EVIDENCE-STANDALONE` |
| `divorce.claim.property` | `divorce.asset_description` | `GAP-DIVORCE-PROPERTY-STRUCTURE` |
| `divorce.claim.custody` | `divorce.child_name`, `divorce.custody_preference` | `GAP-DIVORCE-COMBINED-SCOPE` |
| `divorce.claim.support` | `divorce.support_monthly`, `divorce.child_name` | `GAP-DIVORCE-COMBINED-SCOPE` |
| `divorce.fact.marriage` | `divorce.marriage_date`, `divorce.divorce_reason`, `divorce.separation_start_date` | `GAP-DIVORCE-MARRIAGE-FACTS` |
| `divorce.fact.property` | `divorce.asset_description` | `GAP-DIVORCE-PROPERTY-STRUCTURE` |
| `divorce.fact.custody` | `divorce.custody_preference` | `GAP-DIVORCE-CUSTODY-SUPPORT-DETAIL` |
| `divorce.fact.support` | `divorce.support_monthly` | `GAP-DIVORCE-CUSTODY-SUPPORT-DETAIL` |

## 9. Semantic and conditional mismatches

- `divorce.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 10. Required legal review

- Whether one official divorce form covers the combined relief.
- Which optional claims (visitation, compensation, debt) must stay conditional.
- Whether a structured property schedule is required.
- Whether marriage-fact particulars (childbearing, prior divorce actions) are required.

## 11. Required source / version review

- Confirm that a single form covers the combined workflow, or identify the correct set.
- Re-verify the hash and the per-category page range.
- Confirm whether a later authoritative revision exists.

## 12. Required rights review

- Whether form structure may be reproduced.
- Whether labels may be stored.
- Whether adapted material may be redistributed.

## 13. Potential UI changes (design input only)

- Add optional custody/support grounds and payment-method fields.
- Add optional visitation, debt and compensation fields, each independently conditional.
- Add an optional structured property schedule alongside the free-text description.

## 14. Potential Model changes (design input only)

- Attributes for the new optional claims; each must default to “not claimed”.

## 15. Potential Presenter changes (design input only)

- Map the new optional fields; change nothing existing.

## 16. Potential DOCX structure changes (design input only)

- Keep the narrative layout; keep every optional claim suppressed unless supplied.

## 17. Calculation impacts

Support amounts stay user-supplied; no calculation change is proposed.

## 18. Factual-integrity safeguards

- No marital-fault or misconduct allegation without explicit user confirmation.
- Custody requires a named child; support requires a named child and an amount.
- Every optional claim stays independently conditional.

## 19. Required new test categories

- Custody without child; support without child; visitation present/absent.
- Property schedule present/absent; compensation present/absent.

## 20. Pilot suitability

- Ranking: 3rd of 5 — fewest gaps, but the combined-relief scope is unresolved and optional-claim conditionality is complex.
- See `../pilot-selection.md`. No pilot is implementation-ready.

## 21. Implementation blockers

- GAP-DIVORCE-COMBINED-SCOPE is HIGH and unresolved.
- Do not automatically expand claims.
- No legal, mapping, source or rights review has been performed.
- Readiness classification: `LEGAL_REVIEW_REQUIRED`.
- Recommended next action: Resolve whether one official divorce form covers the combined relief, and review which optional claims must stay conditional.

## 22. Explicit no-authorization statement

> The `divorce` adaptation blueprint is **NOT_AUTHORIZED**. Every proposed change above is a
> design input for a future, separately reviewed decision. No source, mapping, legal or rights
> approval exists, and no production document may change on the basis of this document.
