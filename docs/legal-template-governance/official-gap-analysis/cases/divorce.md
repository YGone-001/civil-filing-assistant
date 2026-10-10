# 离婚纠纷 — `divorce` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `divorce` — 离婚纠纷
- Official candidate: 民事起诉状（离婚纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **36**; crosswalk records: **38**; gaps: **6**

## 2. Verified PDF page range

- Blank 民事起诉状 form: **physical pages p57–p60** (printed pages 41–44), 1-based physical PDF pages.
- Answer form, example pages and the following category were excluded from the blank-form inventory.

## 3. Official form structure

- 当事人信息（原告/被告）
- 委托诉讼代理人
- 诉讼请求（解除婚姻关系、共同财产、共同债务、子女直接抚养、抚养费、探望权、损害赔偿/经济补偿/经济帮助、诉讼费用、其他请求、诉前保全）
- 事实与理由（婚姻关系基本情况、共同财产、共同债务、子女抚养、抚养费、探望权、赔偿/补偿、其他、请求依据）
- 证据清单
- 对纠纷解决方式的意愿
- 落款

## 4. Current application structure

叙事式：当事人栏 → 诉讼请求（离婚/抚养/抚养费/财产分割/诉讼费）→ 事实与理由（结婚、子女、分居、离婚事由、感情破裂）→ 此致/落款。

## 5. Element-level mapping summary

| Coverage status | Count |
|---|---|
| `DIRECT_MATCH` | 6 |
| `PARTIAL_MATCH` | 11 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 17 |
| `APPLICATION_ONLY_ELEMENT` | 2 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Note |
|---|---|---|
| `divorce.party.plaintiff.name` | `shared.party.plaintiff.name` | 均为原告姓名。 |
| `divorce.party.plaintiff.phone` | `shared.party.plaintiff.phone` | 均为联系电话。 |
| `divorce.party.plaintiff.domicile` | `shared.party.plaintiff.address` | 官方为住所地，应用为住址。 |
| `divorce.closing.signature` | — | 均为具状人签署栏。 |
| `divorce.closing.date` | — | 均为落款日期。 |
| `divorce.claim.dissolution` | `divorce.marriage_date` | 均为离婚请求。 |

## 7. Partial matches (incl. semantic/conditional mismatches)

| Official element | Application field(s) | Note |
|---|---|---|
| `divorce.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | 官方区分证件类型与号码，应用仅有号码。 |
| `divorce.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | 被告自然人与原告使用同一套字段。 |
| `divorce.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `divorce.evidence.list` | `shared.evidence.rows` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `divorce.claim.property` | `divorce.asset_description` | 应用以自由文本描述；官方按房屋/汽车/存款/其他分项。 |
| `divorce.claim.custody` | `divorce.child_name`, `divorce.custody_preference` | 均为子女直接抚养请求。 |
| `divorce.claim.support` | `divorce.support_monthly`, `divorce.child_name` | 均为抚养费请求。 |
| `divorce.fact.marriage` | `divorce.marriage_date`, `divorce.divorce_reason`, `divorce.separation_start_date` | 应用采集结婚日期/离婚原因/分居起始日。 |
| `divorce.fact.property` | `divorce.asset_description` | 应用为自由文本；官方为分项要素。 |
| `divorce.fact.custody` | `divorce.custody_preference` | 均为抚养权事由。 |
| `divorce.fact.support` | `divorce.support_monthly` | 均为抚养费事由。 |

## 7b. Semantic and conditional mismatches

- `divorce.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 8. Missing application inputs

- **GAP-DIVORCE-DEBT** (MEDIUM): 共同债务要素缺失。
- **GAP-DIVORCE-VISITATION** (MEDIUM): 探望权要素缺失。
- **GAP-DIVORCE-DAMAGES** (MEDIUM): 该三类请求缺失。

## 9. Missing application outputs / partial coverage

- **GAP-DIVORCE-PROPERTY-STRUCTURE** (MEDIUM, PARTIAL_FIELD_COVERAGE): 结构化程度不同。
- **GAP-DIVORCE-MARRIAGE-FACTS** (MEDIUM, PARTIAL_FIELD_COVERAGE): 若干婚姻关系要素未采集。

## 10. Application-only content (reverse coverage)

| Official element | Application field(s) | Note |
|---|---|---|
| `None` | `shared.court_name` | 应用输出“此致 <法院>”，官方空白表格正文未设法院名称栏（由受理法院确定）。 |
| `None` | `divorce.separation_start_date` | 应用输出分居起始日；官方以“双方生活情况”要素承载。 |

## 11. Conditionality and factual-integrity risks

离婚事由、分居、子女、财产均在用户填写时才输出；无子女时不输出抚养/抚养费；抚养费主张要求已填写子女姓名。

No official example assertion is proposed as unconditional static text. The tri-state contract (`UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE`) is preserved.

## 12. Procedure-specific questions

应用以单一类别覆盖离婚、抚养、抚养费与财产分割；官方表格将上述请求作为同一表格内的分项，但应用缺少探望权与离婚损害赔偿/经济补偿/经济帮助分项。

## 13. Evidence-section findings

- The official 离婚纠纷 complaint form contains a `证据清单（可另附页）` **section**.
- No standalone official evidence-list document was found in the 975-page source.
- The application emits an independent four-column evidence table; standalone equivalence is **unverified**.

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative.
- The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them.
- No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-DIVORCE-COMBINED-SCOPE** — HIGH / PROCEDURAL_APPLICABILITY — 须经法律审查确认范围对应关系。
- **GAP-DIVORCE-PROPERTY-STRUCTURE** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否结构化；须单独授权。
- **GAP-DIVORCE-DEBT** — MEDIUM / MISSING_INPUT — 评估是否新增。
- **GAP-DIVORCE-VISITATION** — MEDIUM / MISSING_INPUT — 评估是否新增。
- **GAP-DIVORCE-DAMAGES** — MEDIUM / MISSING_INPUT — 评估是否新增；须单独授权。
- **GAP-DIVORCE-MARRIAGE-FACTS** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增；不得编造婚姻破裂事由。

## 16. Explicit non-approval statement

> The `divorce` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
