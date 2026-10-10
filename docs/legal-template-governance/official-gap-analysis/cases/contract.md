# 买卖合同纠纷 — `contract` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `contract` — 买卖合同纠纷
- Official candidate: 民事起诉状（买卖合同纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **41**; crosswalk records: **44**; case-scoped complaint gaps: **27**

Gap records are scoped to this case's own official form. A shared application limitation (for example, the shared party page) is recorded separately for each case type rather than borrowed from another case's gap record.

## 2. Verified PDF page range

- Blank 民事起诉状 form: **physical pages p71–p76** (printed pages 55–60), 1-based physical PDF pages.
- Answer form, example pages and the following category were excluded from the blank-form inventory.

## 3. Official form structure

- 当事人信息（原告/被告自然人/被告单位/第三人）
- 委托诉讼代理人
- 诉讼请求（给付价款、迟延利息/违约金、卖方违约损失、瑕疵责任、继续履行或解除、担保、实现债权费用、诉讼费、其他、标的总额）
- 约定管辖和诉前保全
- 事实与理由（合同签订、主体、标的物、价格与支付、交货、质量、违约金/定金、支付与交付情况、迟延、催告、质量争议、协商）
- 证据清单
- 对纠纷解决方式的意愿
- 落款

## 4. Current application structure

叙事式：当事人栏 → 诉讼请求（货款本金/违约金/诉讼费）→ 事实与理由（合同、交货三态、签收三态、欠款）→ 此致/落款。

## 5. Element-level mapping summary

| Coverage status | Count |
|---|---|
| `DIRECT_MATCH` | 6 |
| `PARTIAL_MATCH` | 13 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 20 |
| `APPLICATION_ONLY_ELEMENT` | 3 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Mechanism | Note |
|---|---|---|---|
| `contract.party.plaintiff.name` | `shared.party.plaintiff.name` | `USER_INPUT_FIELD` | 均为原告姓名。 |
| `contract.party.plaintiff.phone` | `shared.party.plaintiff.phone` | `USER_INPUT_FIELD` | 均为联系电话。 |
| `contract.party.plaintiff.domicile` | `shared.party.plaintiff.address` | `USER_INPUT_FIELD` | 官方为住所地，应用为住址。 |
| `contract.closing.signature` | — | `STATIC_RENDERING` | 均为具状人签署栏。 |
| `contract.closing.date` | — | `STATIC_RENDERING` | 均为落款日期。 |
| `contract.claim.price` | `contract.unpaid_amount` | `USER_INPUT_FIELD` | 均为给付价款/货款主张。 |

## 7. Partial matches

| Official element | Application field(s) | Gap(s) | Note |
|---|---|---|---|
| `contract.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | `GAP-CONTRACT-ID-TYPE` | 官方区分证件类型与号码，应用仅有号码。 |
| `contract.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | `GAP-CONTRACT-PARTY-IDENTITY-DETAILS` | 被告自然人与原告使用同一套字段。 |
| `contract.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | `GAP-CONTRACT-ORG-REGISTRATION` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `contract.evidence.list` | `shared.evidence.rows` | `GAP-CONTRACT-EVIDENCE-STANDALONE` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `contract.claim.delay_interest` | `contract.penalty_amount`, `contract.penalty_calc_standard`, `contract.penalty_start_date` | `GAP-CONTRACT-AMOUNT-ASOF` | 应用主张违约金/逾期利息；官方区分利息与违约金。 |
| `contract.fact.contract_formation` | `contract.contract_name`, `contract.contract_date` | `GAP-CONTRACT-FORMATION` | 应用采集合同名称与签订日期；官方另要编号、地点与无书面合同情形。 |
| `contract.fact.contracting_parties` | `shared.party.plaintiff.name` | `GAP-ROLE-LABELLING` | 官方区分业主/建设单位与物业服务人。 |
| `contract.fact.subject_matter` | `contract.product_name` | `GAP-CONTRACT-SUBJECT` | 应用为单一产品文本；官方要求名称/规格/质量/数量。 |
| `contract.fact.price_payment_terms` | `contract.total_amount` | `GAP-CONTRACT-PAYMENT-TERMS` | 应用仅有总金额；官方要求单价与支付方式。 |
| `contract.fact.delivery_terms` | `contract.delivery_date`, `contract.is_delivered` | `GAP-CONTRACT-DELIVERY-TERMS` | 应用有交货日期与三态状态；官方要求地点/方式/风险/验收。 |
| `contract.fact.penalty_terms` | `contract.penalty_amount`, `contract.penalty_calc_standard` | `GAP-CONTRACT-PENALTY-TERMS` | 应用有违约金金额与计算标准；官方另要定金与迟延履行违约金标准。 |
| `contract.fact.payment_delivery_status` | `contract.unpaid_amount`, `contract.is_delivered`, `contract.is_signed` | `GAP-CONTRACT-DELIVERY-TERMS` | 应用有欠款与三态交货/签收；官方按按期/逾期分列金额与件数。 |
| `contract.fact.delay` | `contract.penalty_start_date` | `GAP-CONTRACT-DELAY` | 应用以逾期起算日近似表示迟延；不单独采集迟延履行事实状态。 |

## 7b. Semantic and conditional mismatches

- `contract.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 8. Missing application inputs

- **GAP-CONTRACT-JURISDICTION-CLAUSE** (MEDIUM): 缺少管辖约定字段。
- **GAP-CONTRACT-PARTY-IDENTITY-DETAILS** (MEDIUM): 当事人身份细节字段在应用中没有对应输入。
- **GAP-CONTRACT-QUALITY** (MEDIUM): 质量相关要素全部缺失。
- **GAP-CONTRACT-REPRESENTATIVE** (MEDIUM): 缺少代理人信息。
- **GAP-CONTRACT-SECURITY** (MEDIUM): 担保事实与担保权利主张均未采集。
- **GAP-CONTRACT-THIRD-PARTY** (MEDIUM): 缺少第三人建模。
- **GAP-CONTRACT-DEMAND** (LOW): 官方有催告要素，应用无对应输入，故不输出催告。
- **GAP-CONTRACT-FORMATION** (LOW): 合同编号/地点/无书面合同情形未采集。
- **GAP-CONTRACT-OTHER-CLAIMS** (LOW): 缺少其他请求入口。
- **GAP-CONTRACT-PARTY-RESIDENCE** (LOW): 缺少经常居住地字段。
- **GAP-CONTRACT-PRESERVATION** (LOW): 缺少保全信息。

## 9. Missing application outputs / partial coverage

- **GAP-CONTRACT-AMOUNT-ASOF** (MEDIUM, PARTIAL_FIELD_COVERAGE): 金额基准日与“至实际清偿之日”选项不完整。
- **GAP-CONTRACT-BUYER-CLAIMS** (MEDIUM, MISSING_OUTPUT): 买方视角请求未覆盖。
- **GAP-CONTRACT-DELIVERY-TERMS** (MEDIUM, PARTIAL_FIELD_COVERAGE): 地点/方式/风险/验收未采集。
- **GAP-CONTRACT-EVIDENCE-STANDALONE** (MEDIUM, EVIDENCE_PRESENTATION): 官方为起诉状内嵌章节，应用为独立文档；两者是否等价未经核实。
- **GAP-CONTRACT-LEGAL-BASIS** (MEDIUM, MISSING_OUTPUT): 缺少法律依据输出。
- **GAP-CONTRACT-PAYMENT-TERMS** (MEDIUM, PARTIAL_FIELD_COVERAGE): 单价与支付方式未采集。
- **GAP-CONTRACT-SUBJECT** (MEDIUM, PARTIAL_FIELD_COVERAGE): 规格与质量未结构化采集。
- **GAP-CONTRACT-COURT-FEE-CONDITIONAL** (LOW, CONDITIONALITY_DIFFERENCE): 条件性不同：应用总是主张，官方允许不主张。
- **GAP-CONTRACT-DELAY** (LOW, PARTIAL_FIELD_COVERAGE): 迟延履行的事实状态未结构化采集。
- **GAP-CONTRACT-ENFORCEMENT-COST** (LOW, MISSING_OUTPUT): 该请求未实现。
- **GAP-CONTRACT-ID-TYPE** (LOW, PARTIAL_FIELD_COVERAGE): 缺少证件类型。
- **GAP-CONTRACT-MEDIATION-PREFERENCE** (LOW, PROCEDURAL_APPLICABILITY): 缺少调解意愿字段。
- **GAP-CONTRACT-ORG-REGISTRATION** (LOW, PARTIAL_FIELD_COVERAGE): 企业登记细节不完整。
- **GAP-CONTRACT-PENALTY-TERMS** (LOW, PARTIAL_FIELD_COVERAGE): 违约金类型未区分。
- **GAP-CONTRACT-TOTAL-AMOUNT** (LOW, MISSING_OUTPUT): 缺少标的总额输出。
- **GAP-ROLE-LABELLING** (LOW, SEMANTIC_DIFFERENCE): 角色标签语义不同。

## 10. Application-only content (reverse coverage)

| Official element | Application field(s) | Note |
|---|---|---|
| `None` | `shared.court_name` | 应用输出“此致 <法院>”，官方空白表格正文未设法院名称栏（由受理法院确定）。 |
| `None` | `contract.is_delivered` | 应用输出三态交货事实；官方表格以“交付情况”要素承载，非独立状态栏。 |
| `None` | `contract.is_signed` | 应用输出三态签收事实；官方表格以“交付情况/验收”要素承载，无独立签收栏。 |

## 11. Conditionality and factual-integrity risks

交货与签收均为三态，未确认时不输出；已移除无条件催告表述；交货=False 且签收=True 时阻止导出。

No official example assertion is proposed as unconditional static text. The tri-state contract (`UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE`) is preserved.

## 12. Procedure-specific questions

无程序性采集；买卖方向（卖方/买方）在文中未明确。

## 13. Evidence-section findings

- The official 买卖合同纠纷 complaint form contains a `证据清单（可另附页）` **section**.
- No standalone official evidence-list document was found in the 975-page source.
- The application emits an independent four-column evidence table; standalone equivalence is **unverified**.
- Route ownership: the standalone evidence-list route carries this case's own evidence-list gap (`GAP-CONTRACT-ROUTE-EVIDENCE-STANDALONE` or the loan original); it does not inherit another case's gap record.

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative. The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them. No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-CONTRACT-AMOUNT-ASOF** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增基准日与选项；属计算口径变更，须单独授权。
- **GAP-CONTRACT-BUYER-CLAIMS** — MEDIUM / MISSING_OUTPUT — 评估是否扩展；属产品范围变更，须单独授权。
- **GAP-CONTRACT-DELIVERY-TERMS** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-EVIDENCE-STANDALONE** — MEDIUM / EVIDENCE_PRESENTATION — 保持独立文档现状；等价性须经法律/内容审查后再评估。
- **GAP-CONTRACT-JURISDICTION-CLAUSE** — MEDIUM / MISSING_INPUT — 评估是否新增；属程序事项，需人工核对。
- **GAP-CONTRACT-LEGAL-BASIS** — MEDIUM / MISSING_OUTPUT — 不得自动插入法律条文；须人工填写并复核。
- **GAP-CONTRACT-PARTY-IDENTITY-DETAILS** — MEDIUM / MISSING_INPUT — 在获得授权后再评估是否新增采集项；本阶段仅记录。
- **GAP-CONTRACT-PAYMENT-TERMS** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-QUALITY** — MEDIUM / MISSING_INPUT — 评估是否新增。
- **GAP-CONTRACT-REPRESENTATIVE** — MEDIUM / MISSING_INPUT — 评估是否新增；属当事人自主决定事项。
- **GAP-CONTRACT-SECURITY** — MEDIUM / MISSING_INPUT — 评估是否新增；属结构性扩展，须单独授权。
- **GAP-CONTRACT-SUBJECT** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-THIRD-PARTY** — MEDIUM / MISSING_INPUT — 评估是否支持第三人；属结构性变更，须单独授权。
- **GAP-CONTRACT-COURT-FEE-CONDITIONAL** — LOW / CONDITIONALITY_DIFFERENCE — 记录差异；不改变现有行为。
- **GAP-CONTRACT-DELAY** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增；须避免编造逾期事实。
- **GAP-CONTRACT-DEMAND** — LOW / MISSING_INPUT — 保持现状；新增须以用户确认为前提。
- **GAP-CONTRACT-ENFORCEMENT-COST** — LOW / MISSING_OUTPUT — 评估是否新增。
- **GAP-CONTRACT-FORMATION** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-CONTRACT-ID-TYPE** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增证件类型；本阶段不实现。
- **GAP-CONTRACT-MEDIATION-PREFERENCE** — LOW / PROCEDURAL_APPLICABILITY — 评估是否新增；属程序事项。
- **GAP-CONTRACT-ORG-REGISTRATION** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增；需与工商登记信息核对。
- **GAP-CONTRACT-OTHER-CLAIMS** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-CONTRACT-PARTY-RESIDENCE** — LOW / MISSING_INPUT — 评估是否新增；属送达相关事项，需人工核对。
- **GAP-CONTRACT-PENALTY-TERMS** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否补充类型；不得改变现有违约金计算。
- **GAP-CONTRACT-PRESERVATION** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-CONTRACT-TOTAL-AMOUNT** — LOW / MISSING_OUTPUT — 评估是否新增计算与输出；属计算变更，须单独授权。
- **GAP-ROLE-LABELLING** — LOW / SEMANTIC_DIFFERENCE — 评估是否补充买卖方向表述；不得改变当事人事实。

## 16. Explicit non-approval statement

> The `contract` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
