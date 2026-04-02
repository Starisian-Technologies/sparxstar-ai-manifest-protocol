#!/usr/bin/env python3
"""
SPX Protocol Validator
Authority: spx-vocab.json
Contract:  CONTRACT.md
Rule:      Same input + same vocab = SAME output. If not, protocol is incomplete.
"""

import json
import sys
import os


def load_vocab(vocab_path="system/spx-vocab.json"):
    if not os.path.exists(vocab_path):
        _fail(f"PROTOCOL ERROR: vocab file not found at '{vocab_path}'")
    with open(vocab_path, "r") as f:
        return json.load(f)


def _fail(message):
    print(f"CI FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def _pascal(value):
    return "".join(part.capitalize() for part in value.strip().split("_"))


def normalize(token, vocab):
    token = token.strip().lower()
    synonyms = vocab.get("synonyms", {})
    if token in vocab["domains"] or token in vocab["entities"] or token in vocab["actions"]:
        return token
    if token in synonyms:
        return synonyms[token]
    return None


def resolve_coordinates(domain_raw, entity_raw, action_raw, vocab):
    errors = []

    domain = normalize(domain_raw, vocab)
    entity = normalize(entity_raw, vocab)
    action = normalize(action_raw, vocab)

    if domain is None or domain not in vocab["domains"]:
        errors.append(f"domain '{domain_raw}' is not in allowed domains and has no synonym mapping")
    if entity is None or entity not in vocab["entities"]:
        errors.append(f"entity '{entity_raw}' is not in allowed entities and has no synonym mapping")
    if action is None or action not in vocab["actions"]:
        errors.append(f"action '{action_raw}' is not in allowed actions and has no synonym mapping")

    if errors:
        return None, errors

    return {"domain": domain, "entity": entity, "action": action}, []


def compose(coords, vocab):
    d = coords["domain"]
    e = coords["entity"]
    a = coords["action"]

    return {
        "domain":    d,
        "entity":    e,
        "action":    a,
        "function":  f"spx_{d}_{e}_{a}",
        "class":     f"SPX\\{_pascal(d)}\\{_pascal(e)}\\{_pascal(a)}Service",
        "route":     f"/{d}/{e}/{a}",
        "namespace": f"SPX\\{_pascal(d)}\\{_pascal(e)}",
        "file":      f"/src/{_pascal(d)}/{_pascal(e)}/{_pascal(a)}Service.php",
    }


def validate_payload(payload, expected):
    errors = []
    for field in ["function", "class", "route", "namespace", "file"]:
        if field not in payload:
            errors.append(f"missing field '{field}'")
            continue
        if payload[field] != expected[field]:
            errors.append(
                f"field '{field}':\n"
                f"    expected: {expected[field]}\n"
                f"    got:      {payload[field]}"
            )
    return errors


def validate_class_suffix(class_name, vocab):
    allowed = vocab.get("allowed_class_suffixes", ["Service"])
    forbidden = vocab.get("forbidden_class_suffixes", [])
    for suffix in forbidden:
        if class_name.endswith(suffix):
            return f"class '{class_name}' uses forbidden suffix '{suffix}'"
    for suffix in allowed:
        if class_name.endswith(suffix):
            return None
    return f"class '{class_name}' does not end with an allowed suffix {allowed}"


def validate_casing(composed):
    errors = []
    for field in ["domain", "entity", "action"]:
        if composed[field] != composed[field].lower():
            errors.append(f"coordinate '{field}' must be lowercase, got '{composed[field]}'")
    if composed["function"] != composed["function"].lower():
        errors.append(f"function must be lowercase, got '{composed['function']}'")
    if not composed["route"] == composed["route"].lower():
        errors.append(f"route must be lowercase, got '{composed['route']}'")
    return errors


def run_validation(domain_raw, entity_raw, action_raw, payload=None, vocab_path="spx-vocab.json"):
    vocab = load_vocab(vocab_path)

    coords, errors = resolve_coordinates(domain_raw, entity_raw, action_raw, vocab)
    if errors:
        for e in errors:
            print(f"  INVALID: {e}", file=sys.stderr)
        _fail("intent could not be resolved against protocol")

    composed = compose(coords, vocab)

    casing_errors = validate_casing(composed)
    if casing_errors:
        for e in casing_errors:
            print(f"  INVALID: {e}", file=sys.stderr)
        _fail("casing violation")

    suffix_error = validate_class_suffix(composed["class"], vocab)
    if suffix_error:
        print(f"  INVALID: {suffix_error}", file=sys.stderr)
        _fail("class suffix violation")

    if payload is not None:
        payload_errors = validate_payload(payload, composed)
        if payload_errors:
            for e in payload_errors:
                print(f"  INVALID: {e}", file=sys.stderr)
            _fail("payload does not match expected composition")

    return composed


def print_result(composed):
    print(f"domain:    {composed['domain']}")
    print(f"entity:    {composed['entity']}")
    print(f"action:    {composed['action']}")
    print(f"function:  {composed['function']}")
    print(f"class:     {composed['class']}")
    print(f"route:     {composed['route']}")
    print(f"namespace: {composed['namespace']}")
    print(f"file:      {composed['file']}")


if __name__ == "__main__":
    print("=== SPX Protocol Validator — Test Suite ===\n")

    vocab = load_vocab("spx-vocab.json")

    tests = [
        {
            "label": "convert speech to text",
            "inputs": ("artifact", "speech", "convert"),
            "expect_pass": True,
        },
        {
            "label": "handle a failed transaction",
            "inputs": ("wallet", "transaction", "handle"),
            "expect_pass": True,
        },
        {
            "label": "store a new word token",
            "inputs": ("lexicon", "token", "store"),
            "expect_pass": True,
        },
        {
            "label": "retrieve session context",
            "inputs": ("context", "session", "retrieve"),
            "expect_pass": True,
        },
        {
            "label": "validate an audio artifact",
            "inputs": ("artifact", "audio", "validate"),
            "expect_pass": True,
        },
        {
            "label": "authenticate the session [EXPECT FAIL]",
            "inputs": ("context", "session", "authenticate"),
            "expect_pass": False,
        },
        {
            "label": "payload mismatch [EXPECT FAIL]",
            "inputs": ("artifact", "audio", "transcribe"),
            "payload": {
                "function":  "spx_artifact_audio_transcribe",
                "class":     "SPX\\Artifact\\Audio\\TranscribeManager",
                "route":     "/artifact/audio/transcribe",
                "namespace": "SPX\\Artifact\\Audio",
                "file":      "/src/Artifact/Audio/TranscribeService.php",
            },
            "expect_pass": False,
        },
        {
            "label": "forbidden suffix — Handler [EXPECT FAIL]",
            "inputs": ("artifact", "audio", "validate"),
            "payload": {
                "function":  "spx_artifact_audio_validate",
                "class":     "SPX\\Artifact\\Audio\\ValidateHandler",
                "route":     "/artifact/audio/validate",
                "namespace": "SPX\\Artifact\\Audio",
                "file":      "/src/Artifact/Audio/ValidateService.php",
            },
            "expect_pass": False,
        },
    ]

    passed = 0
    failed = 0

    for test in tests:
        label = test["label"]
        d, e, a = test["inputs"]
        payload = test.get("payload", None)
        expect_pass = test["expect_pass"]

        print(f"--- {label}")

        coords, errors = resolve_coordinates(d, e, a, vocab)

        if errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED: {'; '.join(errors)}\n")
                passed += 1
            else:
                print(f"  UNEXPECTED FAILURE: {'; '.join(errors)}\n", file=sys.stderr)
                failed += 1
            continue

        composed = compose(coords, vocab)

        casing_errors = validate_casing(composed)
        suffix_error = validate_class_suffix(composed["class"], vocab)
        payload_errors = validate_payload(payload, composed) if payload else []

        all_errors = casing_errors + ([suffix_error] if suffix_error else []) + payload_errors

        if payload and payload_errors:
            check_class = payload.get("class", "")
            suffix_err = validate_class_suffix(check_class, vocab)
            if suffix_err and suffix_err not in all_errors:
                all_errors.append(suffix_err)

        if all_errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED:")
                for e in all_errors:
                    print(f"    {e}")
                print()
                passed += 1
            else:
                print(f"  UNEXPECTED FAILURE:")
                for e in all_errors:
                    print(f"    {e}")
                print()
                failed += 1
        else:
            if expect_pass:
                print_result(composed)
                print(f"  CI: PASSED\n")
                passed += 1
            else:
                print(f"  EXPECTED FAILURE BUT PASSED — protocol gap detected\n")
                failed += 1

    print(f"=== Results: {passed} passed, {failed} failed ===")
    if failed > 0:
        sys.exit(1)
