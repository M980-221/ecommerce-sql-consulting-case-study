# Tableau workbook schema

`twb_2026.1.0.xsd` is an unchanged copy of Tableau's public workbook schema, pinned to commit [`f4bce1eb55f0c1c010c0ef826cf531528d5910eb`](https://github.com/tableau/tableau-document-schemas/tree/f4bce1eb55f0c1c010c0ef826cf531528d5910eb). The upstream Apache 2.0 license is included as `LICENSE`. Exact source URLs, byte counts and SHA-256 hashes are recorded in `provenance.json` and checked by the validator.

The public schema imports Tableau's `user` extension namespace and the standard XML namespace without schema locations. `scripts/validate_tableau.py` supplies those two declarations in memory so libxml2 can compile the schema offline. This follows Tableau's own workbook validator; its exact source blob and hash are recorded in `provenance.json`. The user namespace permits extension attributes, while XML attributes retain their standard types. No workbook rules are deleted or validation errors suppressed, and the stored schema is never rewritten.

Run from the repository root:

```bash
python scripts/validate_tableau.py
```

The script checks the packaged workbook against the schema, verifies field references and portable file paths, and compares calculations made from the packaged CSVs with SQLite. These are offline checks. The schema does not compile Tableau expressions or render dashboards; opening the workbook in Tableau is still needed to confirm application compatibility and layout.
