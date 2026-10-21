# Annotation Guidelines — UBWSet (Ugly But It Works)

This is an English translation of the guidelines used by the three human annotators.
The original Portuguese document is included unchanged as `ANNOTATION_GUIDELINE.pt.md`.

The decision criteria (Sections 2 to 6 below) are translated faithfully. The original
document also described the broader UBW project, which covered commit messages, issues,
and pull requests and planned an LLM pre-screening step. Those parts did not apply to this
release and are replaced by the summary in Section 1. Examples for other artifact types are
kept because the annotators read them, but this release contains only code comments.

---

## 1. How the guidelines were applied in this release

- **Calibration (200 items).** The three annotators labeled the items independently and
  then discussed disagreements together to align their reading of the criteria. Because
  the discussion breaks independence, calibration items are excluded from all agreement
  and precision figures.
- **Evaluation (379 code comments).** Each of the three annotators labeled every item
  independently, without consulting the others. The final label is the majority of the
  three votes. The sample combines 110 code comments from an earlier annotation round and
  269 newly drawn code comments, all randomly selected.
- **Labels.** Each annotator recorded `is_ubw` (true/false) and a confidence level
  (`certain`, `likely`, `uncertain`). Only the `is_ubw` votes are published.
- **Rule on independence.** Annotators never changed a label after seeing another
  annotator's label, except during the collective calibration discussion.

The lexicon category of each expression (A, B, or C) is lexicon provenance metadata,
**not an annotation task**: annotators did not assign or confirm categories.

These guidelines do not replace human judgment with mechanical rules. The rules reduce
arbitrary disagreement between annotators; they do not remove the need to read the context.

---

## 2. General operational definition of UBW

An item is `is_ubw = True` **only if all** of the following conditions hold:

1. **Self-admission.** The author is talking about a decision of their *own* (or of their
   team, in the same repository), not describing a general software engineering practice
   in the abstract or someone else's decision.
2. **Explicit trade-off between form and function.** The text contrasts, implicitly or
   explicitly, the quality of the solution ("ugly", "hack", "workaround", "not ideal",
   "temporary") with the fact that it works, solves the problem, or will be left as is.
   Admitting that the code is bad is not enough: the same passage must show the resignation
   to keep it that way.

   **A purely temporal marker satisfies this condition.** A passage such as "temporary fix
   for X" or "temp fix", with no other quality judgment, already expresses the trade-off:
   the author admits the solution is not the final one and introduces it anyway because it
   solves the problem now. This decision was recorded on 2026-08-19, after observing that
   it was the reading consistently practiced by the three annotators in the official sample
   (92.2% prevalence of `True`, including items with only a temporal marker). This note
   resolves the divergence between the original wording of this condition, which was
   stricter and required explicit resignation beyond the temporal marker, and the
   annotation practice already carried out.
3. **Concrete reference to real code or design in this repository.** There must be a
   deictic reference (this method, this function, here, this line, this PR) linking the
   statement to an actual piece of code, not a generic reflection about the profession.
4. **No negation.** "This is NOT a dirty hack" is not UBW; it is the opposite.
5. **Not lexical-match noise.** The expression is not inside a test string literal,
   fixture, third-party docstring, quotation, variable or function name, or an ironic
   comment unrelated to the actual code.

If any of these conditions fails, `is_ubw = False`.

---

## 3. Background: how the lexicon categories arose (reference only)

> **IMPORTANT:** Categories A, B, and C below are **not an annotation task**. They exist in
> the lexicon because they helped organize its construction. The category column is
> metadata; the annotator neither confirms nor assigns a category. This section is for
> reference only, to help you understand what the matched expression tries to capture.
>
> The criterion is the **dominant trait of the author's argument**, not only which lexicon
> word triggered the collection.

### Category A — Aesthetic judgment and explicit hacks
**Dominant trait:** the criticism concerns the *form* of the code (ugly, hack, messy),
without relevant emphasis on time pressure or on uncertainty about the system.

- Operational test: if you rewrote the sentence replacing the aesthetic adjective with
  "this is ugly", the meaning stays almost intact → probably A.

### Category B — Workarounds and urgency
**Dominant trait:** the solution is framed as *temporary, emergency, or palliative*. It
addresses the symptom, not the root cause, with a signal that "this should be revisited
later" (even if it never is).

- Operational test: the sentence contains, explicitly or implicitly, a reference to time or
  urgency ("for now", "so as not to block the release", "I'll fix it later", "kludge",
  "patch") → probably B.

### Category C — Functional resignation and uncertainty
**Dominant trait:** vague acceptance of a suboptimal solution, often linked to **not fully
understanding the system** or to **fear of causing a regression** by changing it. It is
not necessarily a specific aesthetic criticism nor a claim of urgency.

- Operational test: the sentence could be summarized as "I don't know why this works / I'm
  afraid to touch it / it's not ideal, but I won't risk changing it" → probably C.

### Summary table

| | A — Aesthetics | B — Workaround/urgency | C — Uncertainty/resignation |
|---|---|---|---|
| Emphasis | Form of the code | Time / provisional nature | Understanding / risk |
| Typical verb | "it's ugly, it's a hack" | "solves it for now" | "not sure why, don't touch" |
| Anchor expressions | `dirty hack`, `this is a hack`, `messy but works` | `band-aid fix`, `quick and dirty`, `duct tape fix` | `magic number` ⚠, `don't touch` ⚠, `hope everything will work` |
| False-positive risk | Low | Medium | High |

`magic number` and `don't touch` belonged to an earlier version of the lexicon and are not
among the 25 expressions of this release.

---

## 4. Examples by category and artifact type

Each block shows a **positive** example (`is_ubw = True`) and a **negative** near-miss
(`is_ubw = False`) to illustrate the decision boundary. The negative almost always contains
the same lexicon expression, to force a judgment based on context.

### 4.1 Category A

**`code_comment` — positive**
```python
# ugly but it works: parsing manually because the XML library hangs on
# latin-1 encoding and we are not switching libraries now.
def parse_legacy_xml(raw: bytes) -> dict:
    ...
```
→ `is_ubw=True`, `confidence=certain`
(context: Category A lexicon expression, aesthetic form, but you do not record this)

**`code_comment` — negative (test string)**
```python
def test_error_message_for_bad_config():
    with pytest.raises(ConfigError) as exc:
        load_config("bad.yaml")
    assert str(exc.value) == "this is a hack, please fix your config"
```
→ `is_ubw=False` (the expression is the *content* of a tested error message, not an
admission by the author about their own code) — `confidence=certain`

**`commit_message` — positive**
```
fix(auth): dirty hack to bypass token refresh race condition

Not proud of this, but it stops the 500s in prod. Will revisit after
the SSO migration.
```
→ `is_ubw=True`, `confidence=certain`
(context: the lexicon marks it as Category A, but it also has traits of B; you do not
resolve this)

**`issue_body` — negative (third-party quotation)**
```
The reviewer commented on PR #482 that the previous implementation was "a dirty
hack", so we asked to reopen this issue and redo it from scratch.
```
→ `is_ubw=False` (the expression describes a solution that is being **rejected and
replaced**, not kept; condition 2 of Section 2 fails: there is no resignation, there is
active correction)

### 4.2 Category B

**`pr_body` — positive**
```
## What this PR does
Applies a band-aid fix to the shipping calculation: when the postal code is
not found, we use the national average shipping cost instead of failing checkout.

I know this is just a workaround; the real fix is to review the whole
integration with the postal service, which does not fit in this sprint.
```
→ `is_ubw=True`, `confidence=certain`
(context: the lexicon marks it as Category B, urgency/temporary)

**`pr_body` — negative (third-party workaround, outside the author's control)**
```
This PR updates the `libfoo` dependency to 3.2.1, which fixes the bug where
the library itself used an ugly workaround to handle time zones.
```
→ `is_ubw=False` (the "ugly workaround" is third-party code being **removed by the
update**; it is not the author's decision to keep something like it)

**`code_comment` — positive**
```java
// quick and dirty: in-memory cache without TTL. If the process restarts
// often, fine; if not, this becomes a memory leak. Acceptable for now.
private static final Map<String, Object> cache = new HashMap<>();
```
→ `is_ubw=True`, `confidence=certain`
(context: the lexicon marks it as Category B, urgency/temporary)

**`commit_message` — negative (negation)**
```
refactor(payments): remove duct tape fix from retry logic

This was never a real fix, just papering over a bug in the queue
consumer. Root cause fixed in #1204, so we can finally delete this.
```
→ `is_ubw=False`: the message is about **removing** the workaround, not introducing or
keeping it (condition 2 fails: there is no current resignation, there is resolution)

### 4.3 Category C (highest risk — strictest criterion)

**`code_comment` — positive**
```python
# not ideal but it works. This 30 s timeout was set by trial and
# error in 2019 and nobody can explain why it is not 15 s or 60 s.
# Do not touch without running the full load-test suite.
TIMEOUT_SECONDS = 30
```
→ `is_ubw=True`, `confidence=certain`
(context: the lexicon marks it as Category C, uncertainty/resignation)

**`code_comment` — positive (magic number ⚠, high-risk case correctly positive)**
```c
/* magic number, but it works: 0x4F2A is the header offset we found
 * empirically by reading the firmware. We do not have the vendor's official spec. */
#define HEADER_OFFSET 0x4F2A
```
→ `is_ubw=True`, `confidence=certain`
(context: Category C; the admission of uncertainty, "found empirically, we do not have the
spec", plus the resignation, "but it works", satisfy the conditions)

**`code_comment` — negative (magic number ⚠, high-risk case correctly negative)**
```python
MAX_RETRIES = 3  # extracted into a constant to avoid magic numbers
# scattered across the code (see style guide, section 4.2).
```
→ `is_ubw=False`: this is the **opposite** of UBW. The author is *avoiding* a magic number,
a good practice, not admitting to having accepted one. Reject whenever "magic number"
appears in a context of *prevention* rather than *resigned acceptance*.

**`code_comment` — negative (don't touch ⚠, tooling instruction, not resignation)**
```javascript
// AUTO-GENERATED FILE. Don't touch — changes will be overwritten by
// `npm run codegen`.
```
→ `is_ubw=False`: "don't touch" here is an operational instruction about code generation,
with no admission that the solution is bad or uncertain. Condition 2 fails.

**`code_comment` — positive (don't touch ⚠, correctly positive)**
```python
# don't touch this function. It's held together by three different
# hotfixes from 2021-2022 and nobody currently on the team fully
# understands the interaction between them. Hope everything will work.
def legacy_discount_calculator(cart):
    ...
```
→ `is_ubw=True`, `confidence=certain`
(context: Category C; combines fear of regression with uncertainty about the system, the
core of this category)

**`issue_body` — negative (non-technical / generic use)**
```
Title: Review onboarding process

The current onboarding process is not ideal, but it works; let's leave it
as is until next quarter and review it together with HR.
```
→ `is_ubw=False`: "not ideal, but it works" refers to an **organizational process**, not to
software code or design. Condition 3 fails (no reference to real code).

---

## 5. Borderline cases for `is_ubw`

**If `is_ubw` is in doubt**, apply the five conditions of Section 2 one by one, in writing,
in the observation field of the annotation sheet:

1. Self-admission: is it the author or their team deciding, not a third party?
2. Explicit trade-off: does it contrast poor quality with "but it works"?
3. Concrete reference to real code: is there a deictic reference (this function, this method)?
4. No negation: is it not a negated form ("this is not a hack")?
5. Not lexical noise: is it not inside a test string, fixture, or quotation?

If any condition remains ambiguous after this checklist, mark `confidence = uncertain`.
Do not default to `is_ubw = False`.

**High-risk expressions:** `magic number`, `don't touch`, `hope everything will work`.
They appear both in genuine positive contexts and in discardable ones. Always apply the
five conditions; do not rely on the isolated word.

**Items whose file, issue, or PR was removed:** annotate based on the text captured in the
dataset, which is the source of truth of the collection. There is no need to open the live
artifact on GitHub.

**Category context (reference only):** the category column shows which lexicon category
triggered the collection. It helps you understand the trait the expression tries to
capture (see Section 3), but **you neither confirm nor assign a category**.

---

## 6. Common mistakes to avoid

- **Do not classify by the isolated word.** "hack" or "workaround" often appear in neutral
  or even approving contexts ("clever hack that improves performance 10x", with no
  resignation about quality, is not UBW).
- **Do not confuse "describing a problem" with "admitting a bad solution".** An issue that
  *asks* someone to fix an existing "dirty hack" is not, by itself, a UBW instance by the
  issue author (they are reporting, not resigning themselves), unless the issue body also
  takes responsibility for introducing the hack and explains why it was kept.
- **Do not penalize informal tone or humor.** Irony and humor do not cancel a genuine
  admission ("lol this is held together by tape but don't you dare refactor it" is still
  `is_ubw=True`, Category B or C depending on the dominant trait).
- **A ±3-line context may not be enough** for code comments. If the captured context is
  insufficient to apply the five conditions of Section 2, mark `confidence = uncertain`
  instead of guessing.
