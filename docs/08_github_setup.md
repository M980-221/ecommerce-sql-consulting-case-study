# Repository workflow

Repository: https://github.com/M980-221/ecommerce-sql-consulting-case-study

The public repository contains the business brief, completed database setup, import code and verification evidence. Cleaning and analysis stages are in progress.

## Local setup

```bash
git clone https://github.com/M980-221/ecommerce-sql-consulting-case-study.git
cd ecommerce-sql-consulting-case-study
```

Download the source files according to `data/README.md`, then build with `python3 scripts/build_database.py`.

## Tracking changes

Commit completed SQL, scripts, documentation and small verification outputs. Raw CSVs, local databases, credentials and temporary files are excluded by `.gitignore`. GitHub browser uploads do not apply these ignore rules, so use Git or GitHub Desktop for normal updates.

Each stage should update its scripts, supporting evidence, validation log and README status together. Keep pending work clearly identified until it is implemented and checked.

## Later deliverables

The remaining portfolio outputs are cleaned-data rules, analysis queries, reporting views, a dashboard, recommendations and presentation files. Their results should be traceable to SQL outputs and documented populations.
