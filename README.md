# SPARXSTAR AI Manifest Protocol

**Protocol Authority Repository** · Language-agnostic · Patent Pending

---

## What SPX Is and What Problem It Solves

AI code generators hallucinate API names. GPT-4o achieves only 38.58 % accuracy on low-frequency API calls, and API hallucinations account for up to 15 % of all LLM code errors. The root cause is structural: every programming language ships its own naming conventions, and AI agents generating code across repositories have no shared naming contract to anchor them.

**SPARXSTAR AI Manifest Protocol (SPX)** is a deterministic, closed-vocabulary naming protocol. It defines a single, machine-readable vocabulary of permitted terms and a composition grammar that converts intent into an unambiguous identifier — the same way, every time, in any language. Structural drift is not a style violation; it is an architectural signal. Validators catch it at CI time so it never reaches production.

---

## Patent Notice

> **Patent Pending.** Invention date: April 10, 2026.
> All rights reserved. Copyright © Max Barrett / Starisian Technologies.

---

## The Two-Group Model

Every SPX identifier is composed from exactly two groups:

### Group 1 — Structure Path (WHERE the code lives)

| Coordinate   | Required | Description                            |
|--------------|----------|----------------------------------------|
| `authority`  | yes      | Owning organisation or tenant          |
| `system`     | yes      | Top-level platform or product family   |
| `product`    | yes      | Specific product within the system     |
| `subsystem`  | optional | Sub-component within the product       |

### Group 2 — Function Signature (WHAT the code does + HOW it does it)

| Coordinate  | Required | Description                            |
|-------------|----------|----------------------------------------|
| `domain`    | yes      | Business domain (audio, artifact, …)   |
| `entity`    | yes      | Primary noun being acted on            |
| `action`    | yes      | Verb applied to the entity             |
| `execution` | optional | Execution strategy (sync, async, …)    |

**Full function name pattern:**
```
spx_{authority}_{system}_{product}_{domain}_{entity}_{action}[_{execution}]
```

With optional subsystem:
```
spx_{authority}_{system}_{product}_{subsystem}_{domain}_{entity}_{action}[_{execution}]
```

All coordinates must resolve to terms listed in `system/spx-vocab.json`. Unlisted terms are rejected by the validator.

---

## Protocol Authority Files

| File                    | Purpose                                                                                  |
|-------------------------|------------------------------------------------------------------------------------------|
| `system/spx-vocab.json` | Machine-readable vocabulary — the single source of truth for all terms                   |
| `system/CONTRACT.md`    | Human-readable protocol contract — normative naming rules for humans, AI, and CI systems |

### Consuming the Authority Files Directly

This repository publishes the protocol specification only. Runtime classes, package metadata,
and language-specific bindings belong in consuming implementation repositories, not here.
Reference the canonical files by tag in any implementation repo:

```
https://raw.githubusercontent.com/Starisian-Technologies/sparxstar-ai-manifest-protocol/v3.0.0/system/spx-vocab.json
https://raw.githubusercontent.com/Starisian-Technologies/sparxstar-ai-manifest-protocol/v3.0.0/system/CONTRACT.md
```

Or pin to `main` for always-latest (not recommended for production):

```
https://raw.githubusercontent.com/Starisian-Technologies/sparxstar-ai-manifest-protocol/main/system/spx-vocab.json
```

---

## Validators

| File / Mechanism                | Language | Purpose                                                    |
|---------------------------------|----------|------------------------------------------------------------|
| `tools/spx_validator.py`        | Python   | CI scanner — `validate_working_tree()` entry point         |
| Reusable GitHub Action          | YAML     | Consumer-facing CI enforcement wrapper for the Python validator |

The Python validator is the authoritative CI entry point used by `spx-enforce.yml`. It reads `system/spx-vocab.json`, walks `src/` in the consuming repository, and validates `*.php` files against the SPX naming rules. It is currently **PHP-specific**; non-PHP implementations should supply their own language-specific validator and consume the canonical `spx-vocab.json` and `CONTRACT.md` from this repository.

---

## Language Implementations

SPX is language-agnostic. The canonical protocol files in this repository are consumed by each implementation:

| Language | Repository                                                                                         | Status    |
|----------|----------------------------------------------------------------------------------------------------|-----------|
| PHP 8.2+ | [sparxstar-ai-manifest-protocol-php](https://github.com/Starisian-Technologies/sparxstar-ai-manifest-protocol-php) | Active    |

Future implementations (Go, TypeScript, Rust, etc.) follow the same pattern: consume `spx-vocab.json` and `CONTRACT.md` from this repository; publish a language-specific validator and runtime.

To add a new implementation, open an issue in this repository so it can be registered and included in the automated vocab-sync fan-out.

---

## CI Enforcement

`.github/workflows/spx-enforce.yml` validates `system/spx-vocab.json` structure and runs `tools/spx_validator.py` on every push and pull request.

Any consuming repository can enforce SPARXSTAR AI Manifest Protocol (SPX) naming rules using the reusable GitHub Action published from this repository. Add both steps to your workflow:

```yaml
- uses: actions/checkout@v4

- uses: Starisian-Technologies/sparxstar-ai-manifest-protocol@v3.0.0
  with:
    vocab-path: system/spx-vocab.json
```

---

## Vocab Sync

When `system/spx-vocab.json` changes on `main`, the `vocab-sync.yml` workflow automatically opens a pull request in each registered implementation repository. This is what makes SPX ubiquitous — one vocabulary change fans out to all implementations without manual coordination.

---

## License

Proprietary — All Rights Reserved. Copyright © 2026 Max Barrett / Starisian Technologies.
**Patent Pending** (provisional filed April 10, 2026). No licence is granted.
See the [`LICENSE.md`](LICENSE.md) file for the full terms.
