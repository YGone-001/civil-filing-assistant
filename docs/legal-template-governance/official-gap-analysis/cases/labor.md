# 劳动争议纠纷 — `labor` — Official Element Gap Analysis

> **Not approved.** This report is analysis only. No legal review has occurred, no official template has been adopted, and no implementation is authorised.

## 1. Category and source identity

- Case type: `labor` — 劳动争议纠纷
- Official candidate: 民事起诉状（劳动争议纠纷）
- Source: `spc-2025-notice-pdf` — `https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf`
- Verified SHA-256: `07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88` (`SOURCE_HASH_MATCH = PASS`)
- Analyzed revision: `639179933c51f111ea43060157e897fa0a1e4d30`
- Official elements recorded: **34**; crosswalk records: **36**; gaps: **5**

## 2. Verified PDF page range

- Blank 民事起诉状 form: **physical pages p248–p251** (printed pages 232–235), 1-based physical PDF pages.
- Answer form, example pages and the following category were excluded from the blank-form inventory.

## 3. Official form structure

- 当事人信息（原告自然人/被告单位）
- 委托诉讼代理人
- 诉讼请求（工资、二倍工资、加班费、年休假、社保损失、解除补偿、违法解除赔偿金、诉讼费、其他、标的总额）
- 诉前保全
- 事实与理由（合同签订、履行情况、解除或终止、工伤、劳动仲裁、其他、诉请依据）
- 证据清单
- 对纠纷解决方式的意愿
- 落款

## 4. Current application structure

叙事式：当事人栏 → 诉讼请求（欠薪/加班费/二倍工资/诉讼费）→ 事实与理由（入职、岗位、工资、欠薪区间、加班、未签合同）→ 此致/落款。

## 5. Element-level mapping summary

| Coverage status | Count |
|---|---|
| `DIRECT_MATCH` | 5 |
| `PARTIAL_MATCH` | 11 |
| `CONDITIONAL_MISMATCH` | 1 |
| `NO_CURRENT_APPLICATION_FIELD` | 16 |
| `APPLICATION_ONLY_ELEMENT` | 2 |
| `NOT_APPLICABLE` | 1 |

## 6. Direct matches

| Official element | Application field(s) | Note |
|---|---|---|
| `labor.party.plaintiff.name` | `shared.party.plaintiff.name` | 均为原告姓名。 |
| `labor.party.plaintiff.phone` | `shared.party.plaintiff.phone` | 均为联系电话。 |
| `labor.party.plaintiff.domicile` | `shared.party.plaintiff.address` | 官方为住所地，应用为住址。 |
| `labor.closing.signature` | — | 均为具状人签署栏。 |
| `labor.closing.date` | — | 均为落款日期。 |

## 7. Partial matches (incl. semantic/conditional mismatches)

| Official element | Application field(s) | Note |
|---|---|---|
| `labor.party.plaintiff.id_document` | `shared.party.plaintiff.id_number` | 官方区分证件类型与号码，应用仅有号码。 |
| `labor.party.defendant.natural` | `shared.party.plaintiff.name`, `shared.party.plaintiff.id_number`, `shared.party.plaintiff.address`, `shared.party.plaintiff.phone` | 被告自然人与原告使用同一套字段。 |
| `labor.party.defendant.organization` | `shared.party.company_fields`, `shared.party.plaintiff.name`, `shared.party.plaintiff.address` | 应用支持企业名称/信用代码/法定代表人/住所地。 |
| `labor.evidence.list` | `shared.evidence.rows` | 官方为起诉状内嵌章节，应用为独立文档。 |
| `labor.claim.wages` | `labor.unpaid_months`, `labor.monthly_salary` | 均为工资主张；官方要求截至日期。 |
| `labor.claim.double_wage` | `labor.is_no_contract` | 应用在未签劳动合同时主张二倍工资差额。 |
| `labor.claim.overtime` | `labor.overtime` | 均为加班费主张。 |
| `labor.claim.social_insurance_loss` | `labor.social_sec_info` | 应用记录社保信息但不生成请求。 |
| `labor.fact.contract_formation` | `labor.is_no_contract` | 应用以三态表示是否未签书面劳动合同。 |
| `labor.fact.performance` | `labor.emp_join_date`, `labor.job_title`, `labor.monthly_salary` | 应用采集入职/岗位/工资；官方另要工作地点、工资构成、社保、加班基数与年休假。 |
| `labor.fact.termination` | `labor.emp_term_date` | 应用仅有离职日期；官方要求原因与补偿数额。 |

## 7b. Semantic and conditional mismatches

- `labor.procedure.court_fee` → `CONDITIONAL_MISMATCH`: 应用无条件主张诉讼费。

## 8. Missing application inputs

- **GAP-LABOR-WORK-INJURY** (LOW): 工伤要素缺失。

## 9. Missing application outputs / partial coverage

- **GAP-LABOR-CLAIM-SCOPE** (MEDIUM, MISSING_OUTPUT): 四类请求未实现。
- **GAP-LABOR-PERFORMANCE-DETAIL** (MEDIUM, PARTIAL_FIELD_COVERAGE): 履行细节不完整。
- **GAP-LABOR-TERMINATION** (LOW, PARTIAL_FIELD_COVERAGE): 解除原因未采集。

## 10. Application-only content (reverse coverage)

| Official element | Application field(s) | Note |
|---|---|---|
| `None` | `shared.court_name` | 应用输出“此致 <法院>”，官方空白表格正文未设法院名称栏（由受理法院确定）。 |
| `None` | `labor.social_sec_info` | 应用记录社保缴纳情况但不生成请求；官方以“未依法缴纳社会保险费造成的经济损失”请求要素承载。 |

## 11. Conditionality and factual-integrity risks

加班仅在工时与金额同时填写时输出；未签劳动合同时才主张二倍工资（默认否）；欠薪区间无法解析时使用人工确认占位而不编造金额。

No official example assertion is proposed as unconditional static text. The tri-state contract (`UNKNOWN` / `CONFIRMED_TRUE` / `CONFIRMED_FALSE`) is preserved.

## 12. Procedure-specific questions

应用通过界面提示告知劳动仲裁前置程序，但不采集仲裁申请时间/请求/结果；官方表格要求填写劳动仲裁相关情况。仲裁与诉讼的适用关系未决。

## 13. Evidence-section findings

- The official 劳动争议纠纷 complaint form contains a `证据清单（可另附页）` **section**.
- No standalone official evidence-list document was found in the 975-page source.
- The application emits an independent four-column evidence table; standalone equivalence is **unverified**.

## 14. Formatting observations

- The official form is element/checkbox based; the application output is narrative.
- The application's SimSun/SimHei/FangSong_GB2312 sizes, 2.54/3.17 cm margins and 28 pt line spacing are **project conventions**; no inspected source mandates them.
- No typography or layout change is proposed.

## 15. Prioritized review items

- **GAP-LABOR-ARBITRATION** — HIGH / PROCEDURAL_APPLICABILITY — 必须经法律审查确认程序适用性；本阶段不实现。
- **GAP-LABOR-CLAIM-SCOPE** — MEDIUM / MISSING_OUTPUT — 评估是否扩展；属产品范围变更，须单独授权。
- **GAP-LABOR-PERFORMANCE-DETAIL** — MEDIUM / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-LABOR-TERMINATION** — LOW / PARTIAL_FIELD_COVERAGE — 评估是否新增。
- **GAP-LABOR-WORK-INJURY** — LOW / MISSING_INPUT — 评估是否新增。

## 16. Explicit non-approval statement

> The `labor` analysis is **not approved**. It records differences between the application and one inspected official source. Applicability, required adaptation and any legal conclusion remain subject to legal/content review. `approval_status = NOT_REQUESTED`; `review_status = NOT_REQUESTED`.
