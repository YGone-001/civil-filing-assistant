# Source Version and Rights Authorization Gate

**Gate state: `NOT_CLEARED`**

No source is approved for adaptation. No rights decision has been made. This document defines the
prerequisites; it does not satisfy any of them.

---

## 1. Source of record

```text
source_id          : spc-2025-notice-pdf
source_type        : OFFICIAL_TEMPLATE
source_level       : A
official_url       : https://www.court.gov.cn/upload/file/2025/06/22/17/43/202506221742_01.pdf
verification_status: SOURCE_FILE_VERIFIED
content_hash       : sha256:07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88
local_artifact     : NOT_STORED_IN_REPOSITORY
rights_review      : NOT_REVIEWED
```

Related official pages recorded in the registry (announcement and explanation) are
`ANNOUNCEMENT_VERIFIED` only. **Verifying an announcement does not verify any individual template.**

---

## 2. What `SOURCE_FILE_VERIFIED` does and does not mean

| It means | It does **not** mean |
|---|---|
| The file was retrieved and hashed | That the content was legally reviewed |
| The file has the expected structure and page count | That the mapping to a case type is correct |
| Per-category complaint pages were located | That the text may be redistributed |
| — | That the source is `APPROVED_FOR_ADAPTATION` |

Verification states are ordered and not interchangeable:

```text
DISCOVERED → ANNOUNCEMENT_VERIFIED → SOURCE_FILE_VERIFIED → CONTENT_REVIEWED
          → MAPPING_REVIEWED → APPROVED_FOR_ADAPTATION
```

The current state is `SOURCE_FILE_VERIFIED`, which is **two** states short of eligibility.

---

## 3. Required additional checks before implementation eligibility

```text
[ ] issuing authority independently confirmed for the specific category form
[ ] exact version or defensible source identity recorded (no invented version number)
[ ] content hash re-verified against the retrieved bytes
[ ] relevant pages / element scope recorded per case and document type
[ ] verification evidence recorded per case and document type
[ ] applicability review completed and documented
[ ] content review completed and documented
[ ] mapping review completed and documented
[ ] legal / content review completed and documented
[ ] rights review completed and documented
```

An internal project revision must be labelled as internal and never presented as an official version.

---

## 4. Version decision

The registry records no separately identifiable later authoritative revision. Two questions are
explicitly **unresolved**:

- whether the uploaded file has been replaced in place without a URL change;
- whether provincial reproductions differ from the central file.

If a materially different official version is discovered later, the correct action is to record a
**source-version decision blocker** and re-run the ledger — never to silently substitute the new
content. No source version or hash may be changed by this planning task.

---

## 5. Rights decisions required

Distinguish these decisions; they are independent:

```text
1  internal source inspection            (performed at development time, documented)
2  storage of local temporary copies     (outside the repository; documented)
3  storage in the repository             (NOT performed; third-party binaries prohibited)
4  embedding in the application          (NOT decided)
5  redistributing adapted templates      (NOT decided)
6  attribution                           (NOT decided)
7  withdrawal or replacement             (procedure required)
```

**Government publication does not automatically grant unrestricted redistribution rights.** No such
assumption may be made, and none is made here.

Unresolved rights questions that must be answered by an authorized reviewer:

- May extracted field labels be stored in the repository?
- May the application reproduce the official form's structure in a generated document?
- May adapted templates be redistributed with the installer?
- What attribution, if any, is required?
- What is the withdrawal procedure if a rights concern is raised?

---

## 6. Current result

```text
SOURCE_VERSION_GATE:  NOT_CLEARED
RIGHTS_GATE:          NOT_CLEARED
```

Consequences enforced by this plan and by the validator:

- No planning record may claim `APPROVED_FOR_ADAPTATION`.
- No work package may be authorized.
- No source approval may be inferred from `SOURCE_FILE_VERIFIED`.
- No official PDF, page image, extracted bulk text or third-party DOCX may be committed.

If a rights concern is raised later, the affected source record is marked `REJECTED` and dependent
mappings revert to `UNVERIFIED` (governance §8).
