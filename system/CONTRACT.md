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

## 3. Coordinate Protocol — Two-Group Model

All executable naming is derived from two groups:

**Group 1 — Structure Path (WHERE)**
- authority
- system
- product
- subsystem (optional)

**Group 2 — Function Signature (WHAT + HOW)**
- domain
- entity
- action
- execution (optional)

Only one value per coordinate may be selected for a single valid mapping.

No coordinate may be omitted except optional `subsystem` and optional `execution`.

No coordinate may be invented outside the defined vocabulary.

## 4. Allowed Values

The allowed values are defined in spx-vocab.json.

**Structure Path — Group 1:**

Authorities:
- personal
- group
- brain

Systems:
- sparxstar
- aiwa

Products:
- player
- editor
- archive
- marketplace
- ingestion

Subsystems (optional):
- streaming
- governance
- discovery
- ingestion

**Function Signature — Group 2:**

Domains:
- artifact
- lexicon
- context
- wallet

Entities:
- audio
- word
- session
- transaction

Actions:
- create
- read
- update
- delete
- transcribe
- translate
- validate
- resolve
- archive
- execute
- publish

Executions (optional):
- stream
- batch
- sync
- async
- queue

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

**Function (without execution):**
```
spx_{authority}_{system}_{product}_{domain}_{entity}_{action}
```

**Function (with optional subsystem):**
```
spx_{authority}_{system}_{product}_{subsystem}_{domain}_{entity}_{action}
```

**Function (with optional execution):**
```
spx_{authority}_{system}_{product}_{domain}_{entity}_{action}_{execution}
```

**Class:**
```
SPX\{AuthorityPascal}\{SystemPascal}\{ProductPascal}\{DomainPascal}\{EntityPascal}\{ActionPascal}Service
```

**Class (with optional execution):**
```
SPX\{AuthorityPascal}\{SystemPascal}\{ProductPascal}\{DomainPascal}\{EntityPascal}\{ActionPascal}{ExecutionPascal}Service
```

**Route:**
```
/{authority}/{system}/{product}/{domain}/{entity}/{action}
```

**Namespace:**
```
SPX\{AuthorityPascal}\{SystemPascal}\{ProductPascal}\{DomainPascal}\{EntityPascal}
```

**File:**
```
/src/{AuthorityPascal}/{SystemPascal}/{ProductPascal}/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
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

## 13. Structure Path

Structure Path coordinates (authority, system, product, subsystem) are first-class coordinates that appear in all output identifiers as Group 1.

Structure coordinates MUST appear in:
- namespace (first three segments after `SPX\`)
- function name (positions 2–4 after `spx_`)
- class (first three PascalCase segments after `SPX\`)
- route (first three path segments)
- file path (first three directory segments under `/src/`)

**Valid function:**
```
spx_brain_sparxstar_player_artifact_audio_transcribe
```

**Valid namespace:**
```
SPX\Brain\Sparxstar\Player\Artifact\Audio
```

**Invalid (structure coordinates missing):**
```
spx_artifact_audio_transcribe
SPX\Artifact\Audio\TranscribeService
```

## 14. Filesystem

```
/src/{AuthorityPascal}/{SystemPascal}/{ProductPascal}/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

With optional subsystem:
```
/src/{AuthorityPascal}/{SystemPascal}/{ProductPascal}/{SubsystemPascal}/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

No additional structural hierarchy may be introduced unless formally defined by protocol amendment.

## 15. Namespace

```
SPX\{AuthorityPascal}\{SystemPascal}\{ProductPascal}\{DomainPascal}\{EntityPascal}
```

No extra namespace layers for environment or runtime context.

Protocol-internal infrastructure classes (e.g. `SPX\Protocol\Validator`) are excluded from domain-enforcement scans.

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
authority:
system:
product:
domain:
entity:
action:
function:
class:
route:
namespace:
file:
```

Example:
```
authority: brain
system:    sparxstar
product:   player
domain:    artifact
entity:    audio
action:    transcribe
function:  spx_brain_sparxstar_player_artifact_audio_transcribe
class:     SPX\Brain\Sparxstar\Player\Artifact\Audio\TranscribeService
route:     /brain/sparxstar/player/artifact/audio/transcribe
namespace: SPX\Brain\Sparxstar\Player\Artifact\Audio
file:      /src/Brain/Sparxstar/Player/Artifact/Audio/TranscribeService.php
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
