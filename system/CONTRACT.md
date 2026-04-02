MACHINE PROTOCOL — AUTHORITATIVE

This document defines deterministic execution rules.
It is not descriptive prose.
It must be executed as a specification.

Do not summarize.
Do not improve.
Do not reinterpret.
Execute exactly as written.

---

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
- speech → audio
- store → create
- retrieve → read
- token → word
- voice → audio
- save → create
- get → read
- fetch → read
- text → word

The machine-readable synonym map is the source of truth.

No agent may invent a synonym that is not present in that map.

## 6. Selection Rules

After normalization:

- domain must be in allowed domains
- entity must be in allowed entities
- action must be in allowed actions

Else → FAIL

## 7. Single Intent Rule

Multiple intents → INVALID

Example: "validate audio and resolve transaction" → FAIL

No agent may silently choose one action and discard the other.

## 8. Failure Rule

System MUST:
- fail explicitly
- identify unmappable token

System MUST NOT:
- guess
- partially map
- invent
- substitute a close enough value
- collapse multiple intents into one

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

Composition is mandatory. Composition is not invention.

## 10. String Rules

**Internal coordinates:**
- lowercase
- trimmed

**Function:**
- lowercase snake_case
- exact pattern: spx_{domain}_{entity}_{action}

**Namespace/Class:**
- PascalCase segments

**Route:**
- lowercase path
- exact pattern: /{domain}/{entity}/{action}

## 11. Casing

All inputs must be normalized to lowercase BEFORE composition.

PascalCase is then applied deterministically during composition only.

Any other casing is invalid.

## 12. Pluralization

No automatic singularization.

Plural handling must exist in the synonym map.

Example: if token → word, then tokens → word must also be explicitly mapped.

No agent may assume singularization unless the protocol declares it.

## 13. Authority

Authority is runtime ONLY.

Authority must never appear in:
- namespace
- class
- function
- route
- file path

**Valid:**
```
context['authority'] = 'aqua_caliente'
```

**Invalid:**
```
AquaCaliente\SPX\Artifact\Audio\TranscribeService
/aqua-caliente/artifact/audio/transcribe
spx_aqua_caliente_artifact_audio_transcribe
```

## 14. Filesystem

```
/src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

No additional structural hierarchy may be introduced unless formally defined by protocol amendment.

## 15. Namespace

```
SPX\{DomainPascal}\{EntityPascal}
```

No extra namespace layers for company, brand, product, authority, or environment.

## 16. Class Type (STRICT)

Only allowed:
- Service

Everything else → FAIL

Forbidden:
- Manager
- Engine
- Processor
- Handler
- Pipeline
- Coordinator
- Helper
- Utility
- Controller (until formally added by protocol amendment)
- Repository (until formally added by protocol amendment)

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
domain:   artifact
entity:   audio
action:   transcribe
function: spx_artifact_audio_transcribe
class:    SPX\Artifact\Audio\TranscribeService
route:    /artifact/audio/transcribe
```

Any alternate output format is invalid unless explicitly requested by a separate protocol.

## 18. CI Rules

Validator MUST enforce:
- vocab membership
- normalization against synonym map
- single intent compliance
- composition correctness
- casing correctness
- namespace correctness
- file path correctness
- output format correctness
- explicit failure when unmappable

Fail on ANY violation.

## 19. Agent Behavior Rule

AI agents must behave as protocol executors, not creative interpreters.

Agents must:
- normalize only through declared mappings
- compose only through declared formulas
- fail explicitly when unmappable
- never rely on common sense outside the protocol

Passing behavior is rule-following, not helpful improvisation.

## 20. Amendment Rule

Any change to allowed domains, entities, actions, synonym mappings, composition rules, output format, class suffixes, or multi-intent behavior must be treated as a protocol amendment.

Protocol amendments must update:
1. spx-vocab.json
2. validator logic
3. this CONTRACT.md if explanatory changes are needed

No silent drift is allowed.

## 21. Final Rule

Same input + same vocab = SAME output.

If not → protocol incomplete.
