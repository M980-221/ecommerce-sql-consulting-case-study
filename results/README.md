# Verification results

## Part 2

| File | Contents |
|---|---|
| [part2_import_log.csv](part2_import_log.csv) | Source/import counts, rejected records, source and row digests, environment and import time |
| [part2_verification.json](part2_verification.json) | Field preservation, integrity and source totals |
| [part2_validation.txt](part2_validation.txt) | Result sets from the import checks |

## Part 3

| File | Contents |
|---|---|
| [part3_profile.json](part3_profile.json) | Missingness and distinct counts for all 47 fields, exact duplicates and date ranges |
| [part3_validation.json](part3_validation.json) | 62 checks, source fingerprints, script hashes, keys, joins, exceptions and metric populations |
| [part3_validation.txt](part3_validation.txt) | Human-readable check results and the observed SQL outputs |
| [part3_tests.txt](part3_tests.txt) | Output from 14 small automated tests |

The import and Part 3 gates pass. Source exceptions remain documented, including missing dates/categories and payment differences; passing checks do not erase those limitations. The business analysis and dashboard are later stages.

Reproduce Part 3 with `python3 scripts/prepare_part3.py`. To keep another evidence snapshot, use `--results-dir results/rebuilt/part3`. Rerunning unchanged SQL on the same source produces the same profile and validation results. Import timestamps and database hashes in a new Part 2 rebuild can differ.
