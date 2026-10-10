# Legal Template Governance Policy

**Status:** governance contract (documentation only). This policy does **not** implement any
runtime template behaviour. Production template migration is **not authorized**.

- Repository: `YGone-001/civil-filing-assistant`
- Established at revision: `eb23e3e8c8ae080d7185309bf69b3e41681a904e`
- Date: 2026-10-10

---

## 1. Purpose

Every future change that affects the content of a generated legal document must have:

1. an identifiable source,
2. a verifiable version,
3. an explicit applicability decision, and
4. review evidence

**before** it can reach a generated document.

An announcement that official templates exist is not proof that an individual template has
been acquired, verified, or correctly mapped. The distinct states are:

```text
official policy announcement
  ≠ downloaded official template
  ≠ independently verified template content
  ≠ candidate case-type mapping
  ≠ legally reviewed mapping
  ≠ approved application template
  ≠ deployed runtime template
```

Never report a candidate as approved.

---

## 2. Source-of-truth hierarchy (§7.1)

| Rank | Source class | Authority |
|---|---|---|
| 1 | Verified issuing-authority text (Level A) | Highest |
| 2 | Verified official reproduction (Level B) | High, if the issuing document is identifiable |
| 3 | Project interpretation and mapping records (this directory) | Internal; not legal authority |
| 4 | Existing legacy application output | Software baseline only; **not** an official authority |
| 5 | Unverified candidate sources (Level C) | Discovery only; never establishes authenticity |

Level C material (commentary, media, unofficial repositories) may assist discovery and must
never independently establish an official template's authenticity.

**The existing application output is a software baseline, not an official legal authority.**

---

## 3. Source record contract (§7.1 / §5.3)

Each record in `source-registry.json` carries:

```text
source_id, title, issuing_authority, source_type, official_url,
publication_date, document_date, retrieval_or_review_date, source_level,
verification_status, verification_evidence, local_artifact_status,
content_hash_if_verified, legal_or_copyright_review_status, notes
```

Rules:

- Unestablished attributes are recorded as explicit `null`. **Never** invent a date, hash,
  identifier or version.
- A hash may only be recorded after the file has actually been retrieved and hashed.
- An inaccessible attachment is recorded as `UNAVAILABLE` with the blocker — never silently
  replaced by an unofficial copy.
- Verifying an announcement does **not** verify any individual template.

### Source types

`OFFICIAL_NOTICE`, `OFFICIAL_TEMPLATE`, `OFFICIAL_GUIDANCE`, `OFFICIAL_EXPLANATION`,
`REPRODUCED_OFFICIAL_SOURCE`, `SECONDARY_REFERENCE`, `CURRENT_APPLICATION_OUTPUT`.

### Verification states (ordered; not interchangeable)

```text
DISCOVERED → ANNOUNCEMENT_VERIFIED → SOURCE_FILE_VERIFIED → CONTENT_REVIEWED
          → MAPPING_REVIEWED → APPROVED_FOR_ADAPTATION
```

plus the terminal states `REJECTED` and `UNAVAILABLE`.

A source must **not** advance to `APPROVED_FOR_ADAPTATION` without a documented approval
decision (see §5).

---

## 4. Template version contract (§7.2)

Metadata for any future template version:

```text
template_id
source_id
source_version
internal_revision
case_type
document_type
effective_or_publication_date
applicability_scope
change_summary
review_status
approved_by_or_review_role
approval_date
supersedes
```

Rules:

- `source_version` may only be an identifier that appears in the verified source. **Do not
  fabricate official version numbers.**
- `internal_revision` is the project's own revision counter and must be labelled as an internal
  project revision, never as an official version.
- A calendar year is never sufficient evidence of a template version.
- `supersedes` links to a previous `template_id` or is `null`.

---

## 5. Change-control lifecycle (§7.3 / §7.4)

```text
1 Source discovery
2 Source verification
3 Text and structure comparison
4 Case mapping review
5 Legal / content review
6 Engineering implementation
7 DOCX regression validation
8 Release approval
```

| Transition | Entry condition | Exit condition |
|---|---|---|
| 1 → 2 | Source located with a URL | Source record created with explicit nulls for unknown attributes |
| 2 → 3 | Source level A/B and file retrieved | `verification_status ≥ SOURCE_FILE_VERIFIED`, hash recorded |
| 3 → 4 | Source text available | A written comparison exists (elements, sections, omissions) |
| 4 → 5 | Comparison complete | `case-template-mapping.json` entry updated with evidence |
| 5 → 6 | Mapping review recorded | A documented legal/content review decision exists |
| 6 → 7 | Legal review passed | Implementation merged and all tests green |
| 7 → 8 | DOCX regression suite passes | Release approval recorded |

**No phase is complete merely because documentation exists.**

### Approval separation (§7.4)

These are four independent approvals and must never be conflated:

1. **Source authenticity** — is this really the issuing authority's text?
2. **Legal/content review** — is the content correct and applicable?
3. **Engineering implementation acceptance** — does the code behave as specified?
4. **Release approval** — may it ship?

**Passing automated tests is not legal approval. A Git commit is not legal approval.** Do not
name a legal reviewer unless an actual review occurred.

---

## 6. User-fact integrity (§7.5) — non-negotiable

> **The application must never create factual allegations from absent or unconfirmed user
> input.**

Any future template adaptation must preserve the three-state contract where relevant:

```text
UNKNOWN           -> assert neither outcome
CONFIRMED_TRUE    -> may describe the positive fact
CONFIRMED_FALSE   -> may describe the negative fact
```

- A template's example sentence is **not** evidence that the user's case satisfies it.
- Externally supplied sample parties, dates, sums or events must **never** become application
  defaults.
- A template's static text must not be inserted where it would assert an unconfirmed event.

---

## 7. Legal content classification (§7.6)

Future document content must be attributable to exactly one class:

```text
USER_CONFIRMED_FACT
USER_CLAIM_OR_ALLEGATION
CALCULATED_VALUE
LEGAL_REFERENCE
TEMPLATE_STATIC_TEXT
REVIEW_REQUIRED_PLACEHOLDER
UNVERIFIED_SOURCE_CONTENT
```

This is a **documented contract only** — no runtime content engine is implemented in this
phase. `UNVERIFIED_SOURCE_CONTENT` must never be rendered into a user document.

---

## 8. Rights and redistribution (§7.7)

- Record provenance for every source.
- Check redistribution rights before storing any external document in the repository.
- Where attribution is required, record it.
- Limits on storing external material: the repository must not contain third-party template
  binaries without a completed rights review. The 6.8 MB official notice PDF inspected for
  this foundation is deliberately **not** stored in the repository.
- **Government publication does not automatically grant unrestricted redistribution rights.**
  No such assumption may be made.
- Disputed content must be withdrawable: if a rights concern is raised, the affected template
  or source record is marked `REJECTED` and any dependent mapping is reverted to `UNVERIFIED`.

---

## 9. Local applicability (§7.8)

Final filing requirements may depend on the court, the jurisdiction, the case category, the
filing channel, the procedural circumstances and updated official guidance. The project must
not implement court-specific legal rules without independently verified authority.

---

## 10. Offline and privacy guarantee (§7.9)

- Governance metadata is **separate** from user case data and must never contain user
  identities, real dispute narratives, personal contact details, filing credentials or private
  document content.
- The application must continue to operate **without network access**.
- No runtime network dependency, telemetry, dynamic legal-source fetching or online template
  lookup may be introduced.
- Source discovery and inspection happen at development time only.

---

## 11. Future source-update procedure

1. Detect a new or amended official source.
2. Create/update the `source-registry.json` record (explicit nulls where unknown).
3. Retrieve and verify the file; record the hash.
4. Compare text and structure against the currently mapped content.
5. Update `case-template-mapping.json` with the evidence and an honest status.
6. Route through the §5 lifecycle, including a documented legal/content review.
7. Implement only after approval; then run the full DOCX regression suite.
8. Record the release approval and update `supersedes`.

---

## 12. Enforcement

`tools/check_template_governance.py` validates the machine-readable registries against this
policy (missing fields, unknown enum values, duplicate IDs, dangling references, missing
case-document combinations, fabricated-looking approval claims, invalid dates/hashes). It is
deterministic, offline and dependency-free, and runs in CI.

The validator can prove that the records are **well-formed and internally consistent**. It
**cannot** prove that a source is authentic or that content is legally correct.
