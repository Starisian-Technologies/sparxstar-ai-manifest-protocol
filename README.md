# spx-protocol

A deterministic, closed-vocabulary execution protocol.

## Purpose

SPX Protocol enforces a strict, machine-readable naming system for PHP classes, namespaces, and functions.
Every identifier must be composed of terms that exist in the vocabulary file.
This eliminates ambiguity, prevents informal naming, and makes the codebase machine-auditable.

## Vocabulary Authority

`system/spx-vocab.json` is the single source of truth.
It defines the permitted protocol coordinates for `authority`, `system`, `product`, optional `subsystem`, optional `execution`, and `synonyms`.
No term may be used in any identifier unless it is listed there and used in the correct protocol position.

## Naming Rules

All identifiers follow the Two-Group Model:

**Group 1 — Structure Path (WHERE):** `authority`, `system`, `product`, `[subsystem]`

**Group 2 — Function Signature (WHAT + HOW):** `domain`, `entity`, `action`, `[execution]`

| Element | Pattern |
|---|---|
| PHP namespace | `SPX\{Authority}\{System}\{Product}\{Domain}\{Entity}` |
| PHP class | `{Action}[{Execution}]Service` |
| PHP function | `spx_{authority}_{system}_{product}_{domain}_{entity}_{action}[_{execution}]` |
| File path | `src/{Authority}/{System}/{Product}/{Domain}/{Entity}/{Action}[{Execution}]Service.php` |

With optional subsystem:

| Element | Pattern |
|---|---|
| PHP namespace | `SPX\{Authority}\{System}\{Product}\{Subsystem}\{Domain}\{Entity}` |
| PHP function | `spx_{authority}_{system}_{product}_{subsystem}_{domain}_{entity}_{action}` |
| File path | `src/{Authority}/{System}/{Product}/{Subsystem}/{Domain}/{Entity}/{Action}Service.php` |

Legacy 3-coordinate format (`spx_{domain}_{entity}_{action}`) is accepted for backward compatibility.

All required coordinates must match terms in `system/spx-vocab.json`, and optional `subsystem` / `execution` coordinates may only be used where permitted by the protocol authority.

## CI Enforcement

`.github/workflows/spx-standards.yml` runs `tools/spx-validator.php` on every pull request and push to `main`.
The validator reads `system/spx-vocab.json`, scans `src/`, and exits with code `1` on any violation.
A failing run blocks merge.

## Contract

`system/CONTRACT.md` describes the full protocol rules in human-readable form.

## Attribution

Copyright © Max Barrett / Starisian Technologies. All rights reserved.
