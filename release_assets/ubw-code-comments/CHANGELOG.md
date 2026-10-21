# Dataset changelog

## {{RELEASE_VERSION}} — 2026-10-21

- Restored the line breaks of `code_context`. The original collection stored the context window without line separators; each window was rebuilt from the file at the introduction commit, centered on the recorded line. Contexts that could not be rebuilt keep the previous text and are counted in `manifest.json`.
- Translated `data_dictionary.csv` and the annotation guidelines into English; the original Portuguese guidelines ship as `ANNOTATION_GUIDELINE.pt.md`.
- Renamed the `sample_origin` values to English (`earlier_round`, `new_draw`).
- Documented branch-level, rename, and repeated-expression limitations of the temporal fields.
- Recomputed all right-censored `lifetime_days` values against the single cutoff {{COLLECTION_CUTOFF}}.
- Declared the exact UTC cutoff in the release manifest and documentation.
- Replaced the private absolute source path in the manifest with a neutral source filename.
- Updated the dataset title and citation metadata.
- Added field definitions for `lexicon.csv` to the data dictionary.
- Added a dependency-free usage example and automated release validation.

One record was added: with its line breaks restored, the context of `ethyca/fides` `tests/core/test_api.py` (*temporary fix*) shows the matched expression, so it is no longer excluded (6 exclusions instead of 7; 26,030 records instead of 26,029). Personal-information masking, truncation, and context hashes were recomputed on the restored contexts, which changes their counts in `manifest.json`. No record was removed. The identifiers, introduction commits, timestamps, lifetimes, and human votes of the 26,029 records of version 1.0.0 are unchanged.
- Documented source licenses and how maintainers can request the removal of records.
- Added David Candeia Medeiros Maia as a creator.

## 1.0.0 — 2026-09-15

Initial public release.
