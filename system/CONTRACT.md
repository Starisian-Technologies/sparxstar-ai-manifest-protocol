# SPX Protocol Contract

Status: Authoritative human-readable contract
Machine authority: spx-vocab.json + composition rules + CI validator

This repository uses a deterministic closed-vocabulary execution protocol.

The purpose of this contract is to ensure that humans, AI agents, validators, and CI systems all produce the same execution coordinates, names, classes, and routes from the same intent.

This contract is not advisory. It is binding.

## 1. Core Principle

Determinism does not come from intelligence. It comes from fully specified rules.

No agent, developer, or tool may guess, infer beyond the defined protocol, or invent alternate naming structures.

If an intent cannot be mapped using the defined vocabulary and normalization rules, it must fail explicitly.

## 2. Authority Stack

The system authority is ordered as follows:

1. spx-vocab.json
2. Composition rules
3. CI validator
4. This CONTRACT.md

This file explains the system. It does not override the machine-readable protocol.

If this file conflicts with spx-vocab.json or the validator, the machine-readable protocol wins.

## 3. Closed Vocabulary Protocol

All executable naming must be derived from exactly three coordinates:

- domain
- entity
- action

Only one domain, one entity, and one action may be selected for a single valid mapping.

No extra coordinates may be inserted.
No coordinate may be omitted.

## 4. Allowed Values

The allowed values are defined in spx-vocab.json.

**Domains:**

- artifact
- lexicon
- context
- wallet

**Entities:**

- audio
- word
- session
- transaction

**Actions:**

- create
- read
- update
- delete
- transcribe
- validate
- resolve

These values are closed.

## 5. Normalization Rules

Normalization MUST use the synonym map from spx-vocab.json.

If a token is not in allowed values and not mapped → INVALID.

Example:

```
speech → audio
store → create
retrieve → read
```

## 6. Selection Rules

After normalization:

- domain must be in allowed domains
- entity must be in allowed entities
- action must be in allowed actions

Else → FAIL

## 7. Single Intent Rule

Multiple intents → INVALID

Example:
"validate audio and resolve transaction" → FAIL

## 8. Failure Rule

System MUST:

- fail explicitly
- identify unmappable token

System MUST NOT:

- guess
- partially map
- invent

## 9. Composition Rules (MANDATORY)

These are NOT invention. They are deterministic outputs.

**Function:**

```
spx_{domain}_{entity}_{action}
```

**Class:**

```
SPX\{DomainPascal}\{EntityPascal}\{ActionPascal}Service
```

**Route:**

```
/{domain}/{entity}/{action}
```

**Namespace:**

```
SPX\{DomainPascal}\{EntityPascal}
```

**File:**

```
/src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

## 10. String Rules

**Internal:**

- lowercase
- trimmed

**Function:**

- snake_case

**Namespace/Class:**

- PascalCase

**Route:**

- lowercase path

## 11. Casing

All inputs must be normalized to lowercase BEFORE composition.

## 12. Pluralization

No automatic singularization.

Plural handling must exist in the synonym map.

## 13. Authority

Authority is runtime ONLY.

Authority must never appear in:

- namespace
- class
- function
- route

## 14. Filesystem

```
/src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

## 15. Namespace

```
SPX\{DomainPascal}\{EntityPascal}
```

## 16. Class Type (STRICT)

Only allowed:

- Service

Everything else → FAIL

Forbidden:
Manager, Engine, Processor, Handler, Pipeline, etc.

## 17. Output Format (STRICT)

```
domain:
entity:
action:
function:
class:
route:
```

Example:

```
domain: artifact
entity: audio
action: transcribe
function: spx_artifact_audio_transcribe
class: SPX\Artifact\Audio\TranscribeService
route: /artifact/audio/transcribe
```

## 18. CI Rules

Validator MUST enforce:

- vocab membership
- normalization
- single intent
- composition correctness
- casing
- namespace
- file structure
- output format

Fail on ANY violation.

## 19. Final Rule

Same input + same vocab = SAME output

If not → protocol incomplete
