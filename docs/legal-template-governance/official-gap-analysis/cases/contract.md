# 买卖合同纠纷 — `contract` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `contract` — 买卖合同纠纷
- Official candidate: 民事起诉状（买卖合同纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **41**; crosswalk records: **44**; gaps: **8**

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
| `DIRECT_MATCH` | 7 |
| `PARTIAL_MATCH` | 13 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 19 |
| `APPLICATION_ONLY_ELEMENT` | 3 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Note |
|---|---|---|
| `contract.party.plaintiff.name` | `shared.party.plaintiff.name` | 均为原告姓名。 |
| `contract.party.plaintiff.phone` | `shared.party.plaintiff.phone` | 均为联系电话。 |
| `contract.party.plaintiff.domicile` | `shared.party.plaintiff.address` | 官方为住所地，应用为住址。 |
| `contract.closing.signature` | — | 均为具状人签署栏。 |
| `contract.closing.date` | — | 均为落款日期。 |
| `contract.claim.price` | `contract.unpaid_amount` | 均为给付价款/货款主张。 |
| `contract.fact.demand` | `property.demand_record` | 均为催缴情况。 |

## 7. Partial matches (incl. semantic/conditional mismatches)

| Official element | Application field(s) | Note |
|---|---|---|
| `contract.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | 官方区分证件类型与号码，应用仅有号码。 |
| `contract.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | 被告自然人与原告使用同一套字段。 |
| `contract.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `contract.evidence.list` | `shared.evidence.rows` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `contract.claim.delay_interest` | `contract.penalty_amount`, `contract.penalty_calc_standard`, `contract.penalty_start_date` | 应用主张违约金/逾期利息；官方区分利息与违约金。 |
| `contract.fact.contract_formation` | `labor.is_no_contract` | 应用以三态表示是否未签书面劳动合同。 |
| `contract.fact.contracting_parties` | `shared.party.plaintiff.name`, `shared.party.plaintiff.name` | 官方区分业主/建设单位与物业服务人。 |
| `contract.fact.subject_matter` | `contract.product_name` | 应用为单一产品文本；官方要求名称/规格/质量/数量。 |
| `contract.fact.price_payment_terms` | `contract.total_amount` | 应用仅有总金额；官方要求单价与支付方式。 |
| `contract.fact.delivery_terms` | `contract.delivery_date`, `contract.is_delivered` | 应用有交货日期与三态状态；官方要求地点/方式/风险/验收。 |
| `contract.fact.penalty_terms` | `contract.penalty_amount`, `contract.penalty_calc_standard` | 应用有违约金金额与计算标准；官方另要定金与日万分比。 |
| `contract.fact.payment_delivery_status` | `contract.unpaid_amount`, `contract.is_delivered`, `contract.is_signed` | 应用有欠款与三态交货/签收；官方按按期/逾期分列金额与件数。 |
| `contract.fact.delay` | `contract.penalty_start_date` | 应用以逾期起算日近似表示迟延。 |

## 7b. Semantic and conditional mismatches

- `contract.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 8. Missing application inputs

- **GAP-CONTRACT-FORMATION** (LOW): 合同编号/地点/无书面合同情形未采集。
- **GAP-CONTRACT-DEMAND** (LOW): 官方有催告要素，应用无对应输入，故不输出催告。
- **GAP-CONTRACT-QUALITY** (MEDIUM): 质量相关要素全部缺失。

## 9. Missing application outputs / partial coverage

- **GAP-CONTRACT-SUBJECT** (MEDIUM, PARTIAL_FIELD_COVERAGE): 规格与质量未结构化采集。
- **GAP-CONTRACT-PAYMENT-TERMS** (MEDIUM, PARTIAL_FIELD_COVERAGE): 单价与支付方式未采集。
- **GAP-CONTRACT-DELIVERY-TERMS** (MEDIUM, PARTIAL_FIELD_COVERAGE): 地点/方式/风险/验收未采集。
- **GAP-CONTRACT-BUYER-CLAIMS** (MEDIUM, MISSING_OUTPUT): 买方视角请求未覆盖。

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

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative.
- The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them.
- No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-CONTRACT-SUBJECT** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-PAYMENT-TERMS** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-DELIVERY-TERMS** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-CONTRACT-QUALITY** — MEDIUM / MISSING_INPUT — 评估是否新增。
- **GAP-CONTRACT-BUYER-CLAIMS** — MEDIUM / MISSING_OUTPUT — 评估是否扩展；属产品范围变更，须单独授权。
- **GAP-CONTRACT-FORMATION** — LOW / MISSING_INPUT — 评估是否新增。
- **GAP-ROLE-LABELLING** — LOW / SEMANTIC_DIFFERENCE — 评估是否补充买卖方向表述；不得改变当事人事实。
- **GAP-CONTRACT-DEMAND** — LOW / MISSING_INPUT — 保持现状；新增须以用户确认为前提。

## 16. Explicit non-approval statement

> The `contract` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
