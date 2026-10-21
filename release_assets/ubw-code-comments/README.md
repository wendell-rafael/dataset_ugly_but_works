# UBWSet: A Dataset of Ugly-But-It-Works Comments Mined from Git Histories

UBWSet contains 26,030 source-code comment records retrieved from the Git histories of 9,584 public GitHub repositories. The records were found with a 25-expression English lexicon designed to capture comments in which developers acknowledge a technically inadequate, improvised, or inelegant solution that has been retained for practical utility.

The corpus is a lexicon-mined dataset, not a set of 26,030 individually confirmed labels. Three annotators independently evaluated a random sample of 379 records (110 from an earlier annotation round and 269 newly drawn). Majority voting classified 351 records as UBW, yielding an estimated precision of 92.6% (95% Wilson confidence interval: 89.5%–94.8%). Use `human_validation_379.csv` when an analysis requires human-confirmed labels.

## Release

- Version: {{RELEASE_VERSION}}
- Collection cutoff: {{COLLECTION_CUTOFF}}
- Data license: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Dataset concept DOI: <https://doi.org/10.5281/zenodo.22775104>
- Mining software concept DOI (latest version): <https://doi.org/10.5281/zenodo.22861636>

The version-specific dataset DOI must be added to `CITATION.cff` and this README after the new Zenodo version is deposited.

## Files

- `ubw_code_comments.csv`: 26,030 records and 23 fields.
- `human_validation_379.csv`: three independent votes and the majority label for the validation sample.
- `lexicon.csv`: all 25 search expressions and their record counts. One expression has no published occurrence.
- `data_dictionary.csv`: field names, types, and descriptions for the three CSV files.
- `ANNOTATION_GUIDELINE.md`: English translation of the instructions used by the human annotators, with a summary of how they were applied in this release.
- `ANNOTATION_GUIDELINE.pt.md`: the original Portuguese instructions, unchanged.
- `sampling_manifest.json`: sampling design and exclusions from the earlier calibration set.
- `manifest.json`: provenance, counts, fixed cutoff, SHA-256 hashes, and release statistics.
- `example_usage.py`: dependency-free example that loads, joins, and summarizes the data.

## Temporal fields

`introduced_at` is the author date of the commit that introduced the matched expression. For records with an observed removal, `removed_at` stores the removal timestamp and `lifetime_days` is the elapsed number of complete days between the two events.

For a right-censored record, `removed_at` is empty and `is_censored` is `True`. This means that no removal was observed by the fixed collection cutoff. Its `lifetime_days` is measured from `introduced_at` to {{COLLECTION_CUTOFF}}. Right censoring does not mean that the comment will never be removed.

The disappearance of a comment does not, by itself, establish that the underlying technical debt was resolved. Occurrences are tracked per file path and expression across all references of the repository, which has three consequences:

- A removal may have happened on a branch other than the default branch.
- If a file is renamed or moved and the comment is removed afterwards, the removal is not linked to the original occurrence, which then appears as right-censored.
- When a file contains the same expression more than once, only the first occurrence is recorded.

## Quick start

Run the included example from this directory with Python 3.10 or newer:

```bash
python example_usage.py
```

The script uses only the Python standard library. It verifies the main counts, joins the validation votes through `record_id`, and reports observed removals separately from right-censored records.

Minimal join example:

```python
import csv

with open("human_validation_379.csv", encoding="utf-8", newline="") as stream:
    validation = {row["record_id"]: row for row in csv.DictReader(stream)}

with open("ubw_code_comments.csv", encoding="utf-8", newline="") as stream:
    validated = [row for row in csv.DictReader(stream) if row["record_id"] in validation]
```

## Provenance and construction

Repositories were selected through SEART-GHS and canonicalized to their current GitHub names. The code-comment miner cloned the repositories and used case-sensitive literal `git log --all -S <expression>` queries over 13 source-file extensions covering eight languages (Python, Java, JavaScript, TypeScript, C, C++, Go, and Ruby). `primary_language` is the repository-level language reported by GitHub and may differ from the language of the file that contains the comment. Normalized expression verification and the vendored/generated-file filters were applied after history retrieval. Consequently, punctuation, case, or spacing variants that do not pass the literal retrieval stage may be absent.

The original collection stored contexts without line separators. The release preparation step rebuilt each context window, with its line breaks, from the file at the introduction commit; `manifest.json` reports how many contexts could not be rebuilt and therefore remain without line breaks. It also reconstructed contexts in which the expression was missing, corrected confirmed line locations, masked personal information, excluded six contexts in which the trigger was no longer visible after masking, generated stable record identifiers, and recomputed every right-censored lifetime against one fixed UTC cutoff. The source-code context is limited to 2,000 characters.

## Source licenses and removal requests

Source-code excerpts remain subject to the licenses of their original repositories; public visibility on GitHub does not, by itself, grant the right to redistribute them. According to the screening metadata, 499 repositories (1,410 records) declare no license. Each record keeps its `repository` and `source_url`, so users who need a license-based subset can filter the corpus with the license reported by GitHub for each repository.

Maintainers who want records from their repositories removed from future versions can open an issue at <https://github.com/wendell-rafael/dataset_ugly_but_works/issues> with the repository name. Removed records will be listed in the changelog of the next version.

To regenerate and validate this release from the project workspace:

```bash
python scripts/22_prepare_code_comment_release.py \
  --release-version {{RELEASE_VERSION}} \
  --collection-cutoff {{COLLECTION_CUTOFF}}
python scripts/24_validate_code_comment_release.py \
  release/ubw-code-comments-v{{RELEASE_VERSION}}
```

Recreating the underlying collection is distinct from regenerating the frozen release. The former depends on mutable GitHub repositories and external services. The latter uses the archived collection source and produces deterministic temporal fields for the declared cutoff.

## Citation

Use the version-specific citation in `CITATION.cff` after the Zenodo deposit is finalized. Cite the mining software separately when discussing or reusing the collection pipeline.
