# SPX Protocol Contract

## Authority

`system/spx-vocab.json` is the single source of truth for all vocabulary.
No name, identifier, class, function, or route may be introduced outside of the terms defined in that file.

## Vocabulary Structure

The vocab file defines four top-level keys:

- `domains` — the top-level organisational scope (e.g. `artifact`, `lexicon`)
- `entities` — the subject of an operation (e.g. `audio`, `word`)
- `actions` — the operation being performed (e.g. `transcribe`, `resolve`)
- `synonyms` — canonical normalisations that map alternate words onto approved terms

Any term not present in `domains`, `entities`, or `actions` is forbidden.
Any synonym maps an informal word onto its canonical equivalent before validation.

## Naming Rules

### PHP Namespace

```
SPX\{Domain}\{Entity}
```

- `{Domain}` and `{Entity}` are PascalCase versions of values in `domains` and `entities`.

### PHP Class Name

```
{Action}Service
```

- `{Action}` is the PascalCase version of a value in `actions`.

### PHP Function Name

```
spx_{domain}_{entity}_{action}
```

- All lowercase.
- All three segments must exist in the vocab.

### File Path

```
/src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
```

- The file path must match the namespace and class name exactly.

## Forbidden Words

The following words are forbidden in any class name, function name, or namespace segment:

`Manager`, `Engine`, `Processor`, `Handler`, `Pipeline`, `Controller`, `Helper`, `Util`, `Utils`, `Base`, `Abstract`, `Factory`, `Builder`, `Registry`, `Repository`, `Facade`, `Adapter`, `Proxy`, `Decorator`, `Observer`, `Listener`, `Emitter`

## Enforcement

- The validator (`tools/spx-validator.php`) reads `system/spx-vocab.json` and scans `src/`.
- Any violation causes the validator to exit with code `1` and print the expected vs. actual values.
- The CI workflow (`.github/workflows/spx-standards.yml`) runs the validator on every pull request and push to `main`.
- A failing validator blocks merge.

## Compliance Criteria

A file is compliant when ALL of the following are true:

1. Namespace matches `SPX\{Domain}\{Entity}` using valid vocab terms.
2. Class name matches `{Action}Service` using a valid vocab action.
3. At least one function follows `spx_{domain}_{entity}_{action}` with valid vocab terms.
4. No forbidden words appear in any identifier.
5. File path matches `/src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php`.

## Immutability

This contract may only be changed through a deliberate protocol revision that also updates `system/spx-vocab.json` and all affected source files.
No individual implementation file may override or extend this contract.
