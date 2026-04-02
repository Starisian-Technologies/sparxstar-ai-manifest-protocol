# spx-protocol

A deterministic, closed-vocabulary execution protocol.

## Purpose

SPX Protocol enforces a strict, machine-readable naming system for PHP classes, namespaces, and functions.
Every identifier must be composed of terms that exist in the vocabulary file.
This eliminates ambiguity, prevents informal naming, and makes the codebase machine-auditable.

## Vocabulary Authority

`system/spx-vocab.json` is the single source of truth.
It defines the permitted `domains`, `entities`, `actions`, and `synonyms`.
No term may be used in any identifier unless it is listed there.

## Naming Rules

| Element | Pattern |
|---|---|
| PHP namespace | `SPX\{Domain}\{Entity}` |
| PHP class | `{Action}Service` |
| PHP function | `spx_{domain}_{entity}_{action}` |
| File path | `src/{Domain}/{Entity}/{Action}Service.php` |

All segments must match terms in `system/spx-vocab.json`.

## CI Enforcement

`.github/workflows/spx-standards.yml` runs `tools/spx-validator.php` on every pull request and push to `main`.
The validator reads `system/spx-vocab.json`, scans `src/`, and exits with code `1` on any violation.
A failing run blocks merge.

## Contract

`system/CONTRACT.md` describes the full protocol rules in human-readable form.
