# 物业服务合同纠纷 — `property` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `property` — 物业服务合同纠纷
- Official candidate: 民事起诉状（物业服务合同纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **34**; crosswalk records: **36**; case-scoped complaint gaps: **22**

Gap records are scoped to this case's own official form. A shared application limitation (for example, the shared party page) is recorded separately for each case type rather than borrowed from another case's gap record.

## 2. Verified PDF page range

- Blank 民事起诉状 form: **physical pages p233–p236** (printed pages 217–220), 1-based physical PDF pages.
- Answer form, example pages and the following category were excluded from the blank-form inventory.

## 3. Official form structure

- 当事人信息（原告/被告自然人/第三人）
- 委托诉讼代理人
- 诉讼请求（物业费、违约金、诉讼费、其他、标的总额）
- 约定管辖和诉前保全
- 事实与理由（合同签订、主体、项目、费标准、服务期限、支付方式、违约金标准、欠费数额、违约金数额、催缴、其他、请求依据）
- 证据清单
- 对纠纷解决方式的意愿
- 落款

## 4. Current application structure

叙事式：当事人栏 → 诉讼请求（物业费/违约金/诉讼费）→ 事实与理由（服务主张、待核对身份、费标准、欠费、催缴）→ 此致/落款。

## 5. Element-level mapping summary

| Coverage status | Count |
|---|---|
| `DIRECT_MATCH` | 8 |
| `PARTIAL_MATCH` | 9 |
| `SEMANTIC_MISMATCH` | 1 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 14 |
| `APPLICATION_ONLY_ELEMENT` | 2 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Mechanism | Note |
|---|---|---|---|
| `property.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` | 均为原告姓名。 |
| `property.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` | 均为联系电话。 |
| `property.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` | 官方为住所地，应用为住址。 |
| `property.closing.signature` | — | `STATIC_RENDERING` | 均为具状人签署栏。 |
| `property.closing.date` | — | `STATIC_RENDERING` | 均为落款日期。 |
| `property.claim.fee` | `property.total_input`, `property.house_area`, `property.fee_rate` | `USER_INPUT_FIELD` | 均为物业费主张。 |
| `property.fact.fee_standard` | `property.fee_rate` | `USER_INPUT_FIELD` | 均为物业费标准。 |
| `property.fact.demand` | `property.demand_record` | `USER_INPUT_FIELD` | 均为催缴情况。 |

## 7. Partial matches

| Official element | Application field(s) | Gap(s) | Note |
|---|---|---|---|
| `property.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-PROPERTY-ID-TYPE` | 官方区分证件类型与号码，应用仅有号码。 |
| `property.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-PROPERTY-PARTY-IDENTITY-DETAILS` | 被告自然人与原告使用同一套字段。 |
| `property.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-PROPERTY-ORG-REGISTRATION` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `property.evidence.list` | `shared.evidence.rows` | `GAP-PROPERTY-EVIDENCE-STANDALONE` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `property.claim.penalty` | `property.late_fee_logic` | `GAP-PROPERTY-PENALTY-AMOUNT` | 应用以自由文本表示违约金计算方式。 |
| `property.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-PROPERTY-ROLE-LABELLING` | 官方区分业主/建设单位与物业服务人。 |
| `property.fact.project` | `property.property_addr`, `property.house_area` | `GAP-PROPERTY-OWNER` | 应用有地址与面积；官方另有所有权人。 |
| `property.fact.penalty_standard` | `property.late_fee_logic` | `GAP-PROPERTY-PENALTY-AMOUNT` | 应用以自由文本表示违约金标准。 |
| `property.fact.arrears_amount` | `property.total_input`, `property.house_area`, `property.fee_rate` | `GAP-PROPERTY-AMOUNT-ASOF` | 应用给出欠费金额；官方要求数额与计算方式。 |

## 7b. Semantic and conditional mismatches

- `property.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。
- `property.fact.service_term` → `SEMANTIC_MISMATCH`: 应用起止日期为欠费期间；官方为约定的服务期限。

## 8. Missing application inputs

- **GAP-PROPERTY-JURISDICTION-CLAUSE** (MEDIUM): 缺少管辖约定字段。
- **GAP-PROPERTY-OWNER** (MEDIUM): 缺少所有权人字段。
- **GAP-PROPERTY-PARTY-IDENTITY-DETAILS** (MEDIUM): 当事人身份细节字段在应用中没有对应输入。
- **GAP-PROPERTY-REPRESENTATIVE** (MEDIUM): 缺少代理人信息。
- **GAP-PROPERTY-THIRD-PARTY** (MEDIUM): 缺少第三人建模。
- **GAP-PROPERTY-CONTRACT-FORMATION** (LOW): 物业服务合同签订要素未采集。
- **GAP-PROPERTY-OTHER-CLAIMS** (LOW): 缺少其他请求入口。
- **GAP-PROPERTY-PARTY-RESIDENCE** (LOW): 缺少经常居住地字段。
- **GAP-PROPERTY-PAYMENT-METHOD** (LOW): 缺少支付方式。
- **GAP-PROPERTY-PRESERVATION** (LOW): 缺少保全信息。

## 9. Missing application outputs / partial coverage

- **GAP-PROPERTY-AMOUNT-ASOF** (MEDIUM, PARTIAL_FIELD_COVERAGE): 金额基准日与“至实际清偿之日”选项不完整。
- **GAP-PROPERTY-EVIDENCE-STANDALONE** (MEDIUM, EVIDENCE_PRESENTATION): 官方为起诉状内嵌章节，应用为独立文档；两者是否等价未经核实。
- **GAP-PROPERTY-PENALTY-AMOUNT** (MEDIUM, PARTIAL_FIELD_COVERAGE): 缺少违约金数额字段。
- **GAP-PROPERTY-TERM-SEMANTICS** (MEDIUM, SEMANTIC_DIFFERENCE): 字段名相似但语义不同。
- **GAP-PROPERTY-COURT-FEE-CONDITIONAL** (LOW, CONDITIONALITY_DIFFERENCE): 条件性不同：应用总是主张，官方允许不主张。
- **GAP-PROPERTY-ID-TYPE** (LOW, PARTIAL_FIELD_COVERAGE): 缺少证件类型。
- **GAP-PROPERTY-LEGAL-BASIS** (LOW, MISSING_OUTPUT): 缺少依据输出。
- **GAP-PROPERTY-MEDIATION-PREFERENCE** (LOW, PROCEDURAL_APPLICABILITY): 缺少调解意愿字段。
- **GAP-PROPERTY-ORG-REGISTRATION** (LOW, PARTIAL_FIELD_COVERAGE): 企业登记细节不完整。
- **GAP-PROPERTY-ROLE-LABELLING** (LOW, SEMANTIC_DIFFERENCE): 角色标签语义不同。
- **GAP-PROPERTY-TOTAL-AMOUNT** (LOW, MISSING_OUTPUT): 缺少标的总额输出。
- **GAP-PROPERTY-SCOPE** (INFORMATIONAL, PROCEDURAL_APPLICABILITY): 应用范围窄于官方表格的全部要素。

## 10. Application-only content (reverse coverage)

| Official element | Application field(s) | Note |
|---|---|---|
| `None` | `shared.court_name` | 应用输出“此致 <法院>”，官方空白表格正文未设法院名称栏（由受理法院确定）。 |
| `None` | `property.total_input` | 应用允许用户自填物业费总额用于比对；官方表格无自填总额栏。 |

## 11. Conditionality and factual-integrity risks

业主/使用人身份已改为“主张…需人工核对”，不主张确定性所有权；无催缴记录时不输出催缴。

No official example assertion is proposed as unconditional static text. The tri-state contract (`UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE`) is preserved.

## 12. Procedure-specific questions

无程序性采集；应用范围聚焦物业费催收，窄于官方表格全部要素。

## 13. Evidence-section findings

- The official 物业服务合同纠纷 complaint form contains a `证据清单（可另附页）` **section**.
- No standalone official evidence-list document was found in the 975-page source.
- The application emits an independent four-column evidence table; standalone equivalence is **unverified**.
- Route ownership: the standalone evidence-list route carries this case's own evidence-list gap (`GAP-PROPERTY-ROUTE-EVIDENCE-STANDALONE` or the loan original); it does not inherit another case's gap record.

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative. The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them. No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-PROPERTY-AMOUNT-ASOF** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增基准日与选项；属计算口径变更，须单独授权。
- **GAP-PROPERTY-EVIDENCE-STANDALONE** — MEDIUM / EVIDENCE_PRESENTATION — 保持独立文档现状；等价性须经法律/内容审查后再评估。
- **GAP-PROPERTY-JURISDICTION-CLAUSE** — MEDIUM / MISSING_INPUT — 评估是否新增；属程序事项，需人工核对。
- **GAP-PROPERTY-OWNER** — MEDIUM / MISSING_INPUT — 保持现有“待人工核对”表述；新增字段须单独授权。
- **GAP-PROPERTY-PARTY-IDENTITY-DETAILS** — MEDIUM / MISSING_INPUT — 在获得授权后再评估是否新增采集项；本阶段仅记录。
- **GAP-PROPERTY-PENALTY-AMOUNT** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-PROPERTY-REPRESENTATIVE** — MEDIUM / MISSING_INPUT — 评估是否新增；属当事人自主决定事项。
- **GAP-PROPERTY-TERM-SEMANTICS** — MEDIUM / SEMANTIC_DIFFERENCE — 记录语义差异；不得复用现有字段表示不同含义。
- **GAP-PROPERTY-THIRD-PARTY** — MEDIUM / MISSING_INPUT — 评估是否支持第三人；属结构性变更，须单独授权。
- **GAP-PROPERTY-CONTRACT-FORMATION** — LOW / MISSING_INPUT — 评估是否新增；须避免编造合同签订事实。
- **GAP-PROPERTY-COURT-FEE-CONDITIONAL** — LOW / CONDITIONALITY_DIFFERENCE — 记录差异；不改变现有行为。
- **GAP-PROPERTY-ID-TYPE** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增证件类型；本阶段不实现。
- **GAP-PROPERTY-LEGAL-BASIS** — LOW / MISSING_OUTPUT — 不得自动生成法律依据。
- **GAP-PROPERTY-MEDIATION-PREFERENCE** — LOW / PROCEDURAL_APPLICABILITY — 评估是否新增；属程序事项。
- **GAP-PROPERTY-ORG-REGISTRATION** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增；需与工商登记信息核对。
- **GAP-PROPERTY-OTHER-CLAIMS** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-PROPERTY-PARTY-RESIDENCE** — LOW / MISSING_INPUT — 评估是否新增；属送达相关事项，需人工核对。
- **GAP-PROPERTY-PAYMENT-METHOD** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-PROPERTY-PRESERVATION** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-PROPERTY-ROLE-LABELLING** — LOW / SEMANTIC_DIFFERENCE — 评估是否补充角色表述；不得改变当事人事实。
- **GAP-PROPERTY-TOTAL-AMOUNT** — LOW / MISSING_OUTPUT — 评估是否新增计算与输出；属计算变更，须单独授权。
- **GAP-PROPERTY-SCOPE** — INFORMATIONAL / PROCEDURAL_APPLICABILITY — 记录为有意的范围限制；不扩展范围。

## 16. Explicit non-approval statement

> The `property` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
