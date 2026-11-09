# gh-satd-miner

English | [Português](README.pt.md)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23537045.svg)](https://doi.org/10.5281/zenodo.23537045)

Mining infrastructure for the empirical study of **UBW ("Ugly But It Works")**
comments, developed in a master's research project at PPGCC/UFCG (advisor:
Prof. João Arthur Brunet Monteiro; with Prof. David Candeia Medeiros Maia,
IFPB). UBW comments record pragmatic acceptance: the developer admits that a
solution is ugly or a hack but keeps it because it works. The lexicon is mined
from four GitHub artifact types: code comments, commit messages, issue bodies,
and pull request bodies.

This tool has a broader scope than the first version of **UBWSet**. The
published dataset contains code comments only; the miner keeps support for all
four artifact types to enable new collections and later studies. The dataset
and the software have separate citations and persistent identifiers.

UBWSet v1.0.1, the version described in the paper submitted to MSR 2027, is
available at [10.5281/zenodo.23366779](https://doi.org/10.5281/zenodo.23366779);
v1.0.0 remains at
[10.5281/zenodo.22775107](https://doi.org/10.5281/zenodo.22775107). The
dataset's concept DOI, which always resolves to its latest version, is
[10.5281/zenodo.22775104](https://doi.org/10.5281/zenodo.22775104).

Version 1.0.1 contains 26,030 records from 9,584 repositories: code contexts
regained their line breaks, the data dictionary and annotation guidelines were
translated into English, and one previously excluded record has its expression
visible again. The package is built as `release/ubw-code-comments-v1.0.1.zip`
by scripts `22`, `24`, and `25`.

To cite the latest archived version of the software, use the DOI of version
1.0.2, which was used to build UBWSet 1.0.1:
[10.5281/zenodo.23537045](https://doi.org/10.5281/zenodo.23537045).
The software's concept DOI, which always resolves to its latest version, is
[10.5281/zenodo.22861636](https://doi.org/10.5281/zenodo.22861636).

Software version 1.0.2 fixes a single collection cutoff date across resumed
runs, restores line breaks in code contexts, and adds reproducible generation,
validation, and packaging of UBWSet 1.0.1.

## Licenses of code excerpts and removal requests

UBWSet code excerpts remain subject to the licenses of their source
repositories; being public on GitHub does not, by itself, grant redistribution
rights. Maintainers who want records from their repositories removed from
future dataset versions can open an
[issue](https://github.com/wendell-rafael/dataset_ugly_but_works/issues)
with the repository name. Removed records are listed in the changelog of the
following version.

This README covers the software infrastructure (collection, resilience,
performance). The scientific methodology (inclusion criteria, lexicon, research
questions) is in [`plano.md`](plano.md), in Portuguese; the change history is
in [`CHANGELOG.md`](CHANGELOG.md).

## What the infrastructure handles

Mining tens of thousands of repositories across four artifact types runs into
rate limits, timeouts, and unstable third-party services. The following was
implemented to deal with them.

Rotation of multiple GitHub tokens (`ubw/github_api.py`), round-robin, each
token with its own rate-limit state. This multiplies throughput without
exceeding the limit of any single token.

The Search API accepts multiple `repo:` qualifiers in one query (OR semantics,
verified empirically). Collection groups repositories into batches per query,
within the 256-character limit of the `q` parameter, which cut the API search
phase from about 5.8 h to about 48 min on a corpus of 784 repositories. When a
common expression exceeds the Search API's 1,000-result ceiling within a
batch, collection detects it and repeats the search per repository so that
recall is not lost.

Incremental checkpoints in every long stage (screening, collection, LLM
pre-triage, pattern mining): the output file itself acts as the checkpoint, so
an interruption (crash, machine restart, rate limit) does not discard
completed work. See `CHANGELOG.md` for the runs lost before this was in place.

A circuit breaker in the HTTP client (`ubw/github_api.py`) detects sustained
GitHub outages and fails fast instead of running a full retry-and-backoff cycle
on every call. A dead letter queue (`ubw/dlq.py`) records repositories that
repeatedly fail in `code_comment` (clone impossible, repository deleted) and
stops retrying them after N attempts, instead of leaving them pending on every
resume.

The screening service (SEART-GHS) has two TLS problems on its side: it does not
send the intermediate certificate in the handshake, and its certificate expired
in July 2026. `ubw/tls_fix.py` completes the chain through AIA, as a browser
does, and uses SHA-256 fingerprint pinning to tolerate the expired certificate
without disabling TLS verification in general.

Repositories renamed between SEART-GHS indexing and collection break the
Search API `repo:` qualifier (HTTP 422) and can duplicate corpus entries.
`scripts/05_canonicalize_repos.py` resolves the current name through the REST
API redirect before collection.

Precision filters came from real false positives found during mining: vendored
code (by path and by file name), bot authors, lexicon phrases spanning a line
break or list item, and normalized text matching (the Search API applies
stemming and returns false positives).

Each record keeps the raw identifiers available for the introducing author
(name, login, or e-mail, depending on the channel) plus a SHA-256 hash, so that
authors can be contacted for a future survey without exposing raw data when the
dataset is published.

## Repository structure

```
ubw/                         support package shared by all scripts
├── schema.py                collection schema (columns, inclusion criteria, author hash)
├── lexicon.py               closed lexicon of expressions + precision filters
├── patterns.py              exploratory structural patterns (regex)
├── github_api.py            HTTP client with token rotation, rate limiting, and circuit breaker
├── dlq.py                   dead letter queue for persistent repository failures
├── tls_fix.py               TLS workarounds for SEART-GHS
└── envutil.py               .env loading utility

scripts/
├── 01_screening_seart.py         repository screening (SEART-GHS)
├── 05_canonicalize_repos.py      name canonicalization (pre-collection step)
├── 02_collect_multiartifact.py   multi-artifact lexicon collection
├── 03_metrics_llm_triage.py      sampling, LLM pre-triage, agreement metrics
├── 04_pattern_mining.py          exploratory mining of new expressions
└── generate_report_figures.py    figures used in the reports

plano.md                     full scientific methodology (Portuguese)
LEXICO.md                    documentation of all expressions and patterns in use
validation/                  human-validation materials and votes
release_assets/              files shipped with the UBWSet package
tests/                       automated tests
```

## Installation

Requires Python 3.10 or later.

```bash
pip install -r requirements.txt
cp .env.example .env  # set GITHUB_TOKEN(S) and, optionally, ANTHROPIC_API_KEY/OPENROUTER_API_KEY
```

## Usage (typical pipeline order)

```bash
cd scripts

# 1. Screening: finds eligible repositories
python 01_screening_seart.py --out ../data/repos_to_mine.csv

# 2. Canonicalization: resolves renames before collection
python 05_canonicalize_repos.py --repos-csv ../data/repos_to_mine.csv \
    --out ../data/repos_to_mine_canonical.csv

# 3. Multi-artifact collection: applies the lexicon to the 4 artifact types
python 02_collect_multiartifact.py \
    --repos-csv ../data/repos_to_mine_canonical.csv --out-dir ../data \
    --collection-cutoff 2026-07-23T23:59:59Z

# 4. (optional) LLM pre-triage before human annotation
python 03_metrics_llm_triage.py llm-triage \
    --candidates ../data/ubw_collected_full.csv --out ../data/llm_triage_results.csv
```

On the first run, collection writes the cutoff date to
`OUT_DIR/COLLECTION_CUTOFF`. Every resume reuses that value. If a different
explicit date is given for the same directory, the process stops to avoid
incompatible censored durations.

## Building the UBWSet package

The published snapshot can be regenerated from the consolidated corpus without
changing version 1.0.0:

```bash
python scripts/22_prepare_code_comment_release.py \
    --release-version 1.0.1 \
    --collection-cutoff 2026-07-23T23:59:59Z
python scripts/24_validate_code_comment_release.py \
    release/ubw-code-comments-v1.0.1
python scripts/25_package_code_comment_release.py \
    release/ubw-code-comments-v1.0.1
```

The validator checks schema, keys, votes, counts, hashes, temporal
consistency, data-dictionary coverage, and the usage example. The generated
package is written to `release/ubw-code-comments-v1.0.1.zip`.

The local tests of the cutoff-date rule can be run with:

```bash
python -m unittest discover -s tests -v
```

All long-running scripts (1 to 4) support interruption and resumption: run
the same command again, with no special flag. The exception is
`01_screening_seart.py`, which accepts `--resume-from-page N` to resume
manually from a known page.

## Known limitations

- The current automated suite covers cutoff-date persistence and the temporal
  consistency of the release, but not the whole collection against GitHub and
  SEART-GHS. Changes to those paths also require smoke tests on small samples
  before a full-scale run.
- Coupled to this research (study schema, closed lexicon, SEART-GHS endpoint);
  it is not a general-purpose library, although `ubw/github_api.py` and the
  incremental checkpoint pattern can be reused elsewhere.
- The TLS certificate workaround (`ubw/tls_fix.py`) is temporary: remove it
  from normal use once SEART-GHS renews its certificate.
- Relative paths (`../data/...`) assume execution from `scripts/`.

## Authorship and citation

Developed by Wendell Rafael Oliveira Nascimento, João Arthur Brunet Monteiro,
and Fabio Jorge Almeida Morais as supporting infrastructure for research on the
UBW phenomenon. Licensed under MIT (see `LICENSE`).

When using the software, cite an archived version on Zenodo. Citation metadata
for version 1.0.2 (DOI
[10.5281/zenodo.23537045](https://doi.org/10.5281/zenodo.23537045)) are in
[`CITATION.cff`](CITATION.cff).
