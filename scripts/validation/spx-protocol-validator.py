#!/usr/bin/env python3
"""
SPX Protocol Validator

Authority:      spx-vocab.json
Contract:       CONTRACT.md
Rule:           Same input + same vocab = SAME output. If not, protocol is incomplete.
Author:         Claude Sonnet 4.6, made by Anthropic
Contributor:    Starisian Technology (Max Barrett)
Version:        2.0.0 — Two-Group Model (Structure Path + Function Signature)
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


def validate_structure(authority_raw, system_raw, product_raw, vocab, subsystem_raw=None):
    """
    Validate Structure Path coordinates against the controlled vocabulary.
    Rules:
      - All terms must be lowercase
      - All terms must exist in structure vocabulary
      - Hyphens are forbidden — underscores only
      - Abbreviations and invented terms are forbidden
      - Subsystem is optional; if provided must be in structure.subsystems
    """
    errors = []
    structure = vocab.get("structure", {})

    def check(raw, coord_name, allowed_set):
        if raw is None:
            return None
        token = raw.strip()
        if token != token.lower():
            errors.append(
                f"ERR_COORDINATE_UNDEF: structure {coord_name} '{token}' must be lowercase"
            )
            return None
        if "-" in token:
            errors.append(
                f"ERR_COORDINATE_UNDEF: structure {coord_name} '{token}' contains hyphen — use underscore"
            )
            return None
        if token not in allowed_set:
            errors.append(
                f"ERR_COORDINATE_UNDEF: structure {coord_name} '{token}' not in allowed {coord_name}s {sorted(allowed_set)}"
            )
            return None
        return token

    authority = check(authority_raw, "authority", set(structure.get("authorities", [])))
    system    = check(system_raw,    "system",    set(structure.get("systems",     [])))
    product   = check(product_raw,   "product",   set(structure.get("products",    [])))
    subsystem = check(subsystem_raw, "subsystem", set(structure.get("subsystems",  []))) if subsystem_raw else None

    if errors:
        return None, errors

    return {
        "authority": authority,
        "system":    system,
        "product":   product,
        "subsystem": subsystem,
    }, []


def resolve_coordinates(domain_raw, entity_raw, action_raw, vocab):
    errors = []

    domain = normalize(domain_raw, vocab)
    entity = normalize(entity_raw, vocab)
    action = normalize(action_raw, vocab)

    if domain is None or domain not in vocab["domains"]:
        errors.append(f"ERR_COORDINATE_UNDEF: domain '{domain_raw}' is not in allowed domains and has no synonym mapping")
    if entity is None or entity not in vocab["entities"]:
        errors.append(f"ERR_COORDINATE_UNDEF: entity '{entity_raw}' is not in allowed entities and has no synonym mapping")
    if action is None or action not in vocab["actions"]:
        errors.append(f"ERR_COORDINATE_UNDEF: action '{action_raw}' is not in allowed actions and has no synonym mapping")

    if errors:
        return None, errors

    return {"domain": domain, "entity": entity, "action": action}, []


def compose(structure, coords, vocab):
    """
    Compose all outputs from both Structure Path and Function Signature.
    Name = Structure_Path + f(domain, entity, action)
    All six inputs are from closed sets. Output is deterministic.
    """
    auth = structure["authority"]
    sys_ = structure["system"]
    prod = structure["product"]
    sub  = structure.get("subsystem")

    d = coords["domain"]
    e = coords["entity"]
    a = coords["action"]

    # Structure path string (with optional subsystem)
    if sub:
        struct_flat = f"{auth}_{sys_}_{prod}_{sub}"
        struct_path = f"/{auth}/{sys_}/{prod}/{sub}"
        struct_ns   = f"{_pascal(auth)}\\{_pascal(sys_)}\\{_pascal(prod)}\\{_pascal(sub)}"
        struct_dir  = f"{_pascal(auth)}/{_pascal(sys_)}/{_pascal(prod)}/{_pascal(sub)}"
    else:
        struct_flat = f"{auth}_{sys_}_{prod}"
        struct_path = f"/{auth}/{sys_}/{prod}"
        struct_ns   = f"{_pascal(auth)}\\{_pascal(sys_)}\\{_pascal(prod)}"
        struct_dir  = f"{_pascal(auth)}/{_pascal(sys_)}/{_pascal(prod)}"

    return {
        "authority":  auth,
        "system":     sys_,
        "product":    prod,
        "subsystem":  sub,
        "domain":     d,
        "entity":     e,
        "action":     a,
        "function":   f"spx_{struct_flat}_{d}_{e}_{a}",
        "class":      f"SPX\\{struct_ns}\\{_pascal(d)}\\{_pascal(e)}\\{_pascal(a)}Service",
        "route":      f"{struct_path}/{d}/{e}/{a}",
        "namespace":  f"SPX\\{struct_ns}\\{_pascal(d)}\\{_pascal(e)}",
        "file":       f"/src/{struct_dir}/{_pascal(d)}/{_pascal(e)}/{_pascal(a)}Service.php",
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
    for field in ["authority", "system", "product", "domain", "entity", "action"]:
        if composed.get(field) and composed[field] != composed[field].lower():
            errors.append(f"coordinate '{field}' must be lowercase, got '{composed[field]}'")
    if composed["function"] != composed["function"].lower():
        errors.append(f"function must be lowercase, got '{composed['function']}'")
    if composed["route"] != composed["route"].lower():
        errors.append(f"route must be lowercase, got '{composed['route']}'")
    return errors


def print_result(composed):
    print(f"authority:  {composed['authority']}")
    print(f"system:     {composed['system']}")
    print(f"product:    {composed['product']}")
    if composed.get("subsystem"):
        print(f"subsystem:  {composed['subsystem']}")
    print(f"domain:     {composed['domain']}")
    print(f"entity:     {composed['entity']}")
    print(f"action:     {composed['action']}")
    print(f"function:   {composed['function']}")
    print(f"class:      {composed['class']}")
    print(f"route:      {composed['route']}")
    print(f"namespace:  {composed['namespace']}")
    print(f"file:       {composed['file']}")


if __name__ == "__main__":
    print("=== SPX Protocol Validator v2.0 — Test Suite ===\n")
    print("Two-Group Model: Structure Path + Function Signature\n")

    vocab = load_vocab("system/spx-vocab.json")

    tests = [
        {
            "label": "SPARXSTAR player reads audio",
            "structure": ("brain", "sparxstar", "player"),
            "inputs":    ("artifact", "speech", "convert"),
            "expect_pass": True,
        },
        {
            "label": "SPARXSTAR archive resolves a transaction",
            "structure": ("brain", "sparxstar", "archive"),
            "inputs":    ("wallet", "transaction", "handle"),
            "expect_pass": True,
        },
        {
            "label": "AiWA archive creates a word token",
            "structure": ("group", "aiwa", "archive"),
            "inputs":    ("lexicon", "token", "store"),
            "expect_pass": True,
        },
        {
            "label": "SPARXSTAR player reads session context",
            "structure": ("brain", "sparxstar", "player"),
            "inputs":    ("context", "session", "retrieve"),
            "expect_pass": True,
        },
        {
            "label": "SPARXSTAR editor validates audio",
            "structure": ("brain", "sparxstar", "editor"),
            "inputs":    ("artifact", "audio", "validate"),
            "expect_pass": True,
        },
        {
            "label": "with streaming subsystem",
            "structure": ("brain", "sparxstar", "player", "streaming"),
            "inputs":    ("artifact", "audio", "read"),
            "expect_pass": True,
        },
        {
            "label": "INVALID structure — bad authority [EXPECT FAIL]",
            "structure": ("BRAIN", "sparxstar", "player"),
            "inputs":    ("artifact", "audio", "read"),
            "expect_pass": False,
        },
        {
            "label": "INVALID structure — hyphen in system [EXPECT FAIL]",
            "structure": ("brain", "sparx-star", "player"),
            "inputs":    ("artifact", "audio", "read"),
            "expect_pass": False,
        },
        {
            "label": "INVALID structure — invented authority [EXPECT FAIL]",
            "structure": ("corporate", "sparxstar", "player"),
            "inputs":    ("artifact", "audio", "read"),
            "expect_pass": False,
        },
        {
            "label": "INVALID function — unknown action [EXPECT FAIL]",
            "structure": ("brain", "sparxstar", "player"),
            "inputs":    ("context", "session", "authenticate"),
            "expect_pass": False,
        },
    ]

    passed = 0
    failed = 0

    for test in tests:
        label    = test["label"]
        struct_t = test["structure"]
        d, e, a  = test["inputs"]
        payload  = test.get("payload")
        expect_pass = test["expect_pass"]

        print(f"--- {label}")

        # Validate structure path
        sub = struct_t[3] if len(struct_t) == 4 else None
        structure, s_errors = validate_structure(struct_t[0], struct_t[1], struct_t[2], vocab, sub)

        if s_errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED (structure): {'; '.join(s_errors)}\n")
                passed += 1
            else:
                print(f"  UNEXPECTED STRUCTURE FAILURE: {'; '.join(s_errors)}\n", file=sys.stderr)
                failed += 1
            continue

        # Validate function signature
        coords, f_errors = resolve_coordinates(d, e, a, vocab)

        if f_errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED (function): {'; '.join(f_errors)}\n")
                passed += 1
            else:
                print(f"  UNEXPECTED FUNCTION FAILURE: {'; '.join(f_errors)}\n", file=sys.stderr)
                failed += 1
            continue

        composed     = compose(structure, coords, vocab)
        casing_errs  = validate_casing(composed)
        suffix_err   = validate_class_suffix(composed["class"], vocab)
        payload_errs = validate_payload(payload, composed) if payload else []

        all_errors = casing_errs + ([suffix_err] if suffix_err else []) + payload_errs

        if all_errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED:")
                for err in all_errors:
                    print(f"    {err}")
                print()
                passed += 1
            else:
                print(f"  UNEXPECTED FAILURE:")
                for err in all_errors:
                    print(f"    {err}")
                print()
                failed += 1
        else:
            if expect_pass:
                print_result(composed)
                print(f"  CI: PASSED\n")
                passed += 1
            else:
                print(f"  EXPECTED FAILURE BUT PASSED — protocol gap\n")
                failed += 1

    print(f"=== Results: {passed} passed, {failed} failed ===")
    if failed > 0:
        sys.exit(1)
