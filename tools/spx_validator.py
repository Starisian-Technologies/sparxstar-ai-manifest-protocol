#!/usr/bin/env python3
"""
SPX Protocol Validator
Authority: spx-vocab.json
Contract:  CONTRACT.md
Rule:      Same input + same vocab = SAME output. If not, protocol is incomplete.
Version:   2.0.0 — Two-Group Model (Structure Path + Function Signature)
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

    # Support both flat list and dict formats
    domains  = _domain_keys(vocab)
    entities = _entity_keys(vocab)
    actions  = _action_keys(vocab)

    if token in domains or token in entities or token in actions:
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

    if domain is None or domain not in _domain_keys(vocab):
        errors.append(f"ERR_COORDINATE_UNDEF: domain '{domain_raw}' is not in allowed domains and has no synonym mapping")
    if entity is None or entity not in _entity_keys(vocab):
        errors.append(f"ERR_COORDINATE_UNDEF: entity '{entity_raw}' is not in allowed entities and has no synonym mapping")
    if action is None or action not in _action_keys(vocab):
        errors.append(f"ERR_COORDINATE_UNDEF: action '{action_raw}' is not in allowed actions and has no synonym mapping")

    if errors:
        return None, errors

    return {"domain": domain, "entity": entity, "action": action}, []


def _entity_keys(vocab):
    entities = vocab.get("entities", {})
    if isinstance(entities, list):
        return set(entities)
    return set(entities.keys())


def _action_keys(vocab):
    actions = vocab.get("actions", {})
    if isinstance(actions, list):
        return set(actions)
    return set(actions.keys())


def _domain_keys(vocab):
    domains = vocab.get("domains", {})
    if isinstance(domains, list):
        return set(domains)
    return set(domains.keys())


def validate_constraints(domain, entity, action, vocab):
    """
    Validate that the combination of domain, entity, and action
    is legal according to the constraint rules in spx-vocab.json.

    Returns list of errors. Empty list = valid.

    New machine states:
      ERR_ILLEGAL_COMBINATION — pairing violates explicit constraint
    """
    errors = []

    entities = vocab.get("entities", {})
    actions  = vocab.get("actions",  {})
    domains  = vocab.get("domains",  {})

    # Skip constraint checks if vocab uses old flat-list format
    if isinstance(entities, list):
        return []

    entity_def = entities.get(entity, {})
    action_def = actions.get(action,  {})
    domain_def = domains.get(domain,  {})

    # Check entity's allowed_actions
    allowed_actions = entity_def.get("allowed_actions")
    if allowed_actions is not None and action not in allowed_actions:
        errors.append(
            f"ERR_ILLEGAL_COMBINATION: action '{action}' is not allowed "
            f"for entity '{entity}'. Allowed: {allowed_actions}"
        )

    # Check entity's disallowed_with
    disallowed = entity_def.get("disallowed_with", [])
    if action in disallowed:
        errors.append(
            f"ERR_ILLEGAL_COMBINATION: action '{action}' is explicitly "
            f"disallowed with entity '{entity}'"
        )

    # Check action's allowed_domains (if constrained)
    action_allowed_domains = action_def.get("allowed_domains")
    if action_allowed_domains is not None and domain not in action_allowed_domains:
        errors.append(
            f"ERR_ILLEGAL_COMBINATION: action '{action}' requires domain "
            f"to be one of {action_allowed_domains}, got '{domain}'"
        )

    # Check action's allowed_entities (if constrained)
    action_allowed_entities = action_def.get("allowed_entities")
    if action_allowed_entities is not None and entity not in action_allowed_entities:
        errors.append(
            f"ERR_ILLEGAL_COMBINATION: action '{action}' requires entity "
            f"to be one of {action_allowed_entities}, got '{entity}'"
        )

    # Check domain's allowed_entities (if constrained)
    domain_allowed_entities = domain_def.get("allowed_entities")
    if domain_allowed_entities is not None and entity not in domain_allowed_entities:
        errors.append(
            f"ERR_ILLEGAL_COMBINATION: domain '{domain}' requires entity "
            f"to be one of {domain_allowed_entities}, got '{entity}'"
        )

    return errors


def compose(structure, coords, vocab):
    """
    Compose all outputs from Structure Path and Function Signature.
    Name = Structure_Path + f(domain, entity, action[, execution])
    execution is optional. When present it disambiguates HOW the action runs.
    All inputs are from closed sets. Output is deterministic.
    """
    auth = structure["authority"]
    sys_ = structure["system"]
    prod = structure["product"]
    sub  = structure.get("subsystem")
    ex   = coords.get("execution")

    d = coords["domain"]
    e = coords["entity"]
    a = coords["action"]

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

    if ex:
        function_  = f"spx_{struct_flat}_{d}_{e}_{a}_{ex}"
        class_     = f"SPX\\{struct_ns}\\{_pascal(d)}\\{_pascal(e)}\\{_pascal(a)}{_pascal(ex)}Service"
        route_     = f"{struct_path}/{d}/{e}/{a}/{ex}"
        file_      = f"/src/{struct_dir}/{_pascal(d)}/{_pascal(e)}/{_pascal(a)}{_pascal(ex)}Service.php"
    else:
        function_  = f"spx_{struct_flat}_{d}_{e}_{a}"
        class_     = f"SPX\\{struct_ns}\\{_pascal(d)}\\{_pascal(e)}\\{_pascal(a)}Service"
        route_     = f"{struct_path}/{d}/{e}/{a}"
        file_      = f"/src/{struct_dir}/{_pascal(d)}/{_pascal(e)}/{_pascal(a)}Service.php"

    return {
        "authority":  auth,
        "system":     sys_,
        "product":    prod,
        "subsystem":  sub,
        "domain":     d,
        "entity":     e,
        "action":     a,
        "execution":  ex,
        "function":   function_,
        "class":      class_,
        "route":      route_,
        "namespace":  f"SPX\\{struct_ns}\\{_pascal(d)}\\{_pascal(e)}",
        "file":       file_,
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
                f"  expected: {expected[field]}\n"
                f"  got:      {payload[field]}"
            )
    return errors


def validate_class_suffix(class_name, vocab):
    allowed  = vocab.get("allowed_class_suffixes", ["Service"])
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


def validate_execution(execution_raw, vocab):
    """
    Validate optional execution coordinate against closed vocabulary.
    Returns (execution, errors). If execution_raw is None, returns (None, []).
    """
    if execution_raw is None:
        return None, []

    executions = vocab.get("executions", {})
    token_raw = execution_raw.strip()

    if "-" in token_raw:
        return None, [f"ERR_COORDINATE_UNDEF: execution '{token_raw}' contains hyphen — use underscore"]
    if token_raw != token_raw.lower():
        return None, [f"ERR_COORDINATE_UNDEF: execution '{token_raw}' must be lowercase"]

    token = token_raw.lower()
    if token not in executions:
        return None, [f"ERR_COORDINATE_UNDEF: execution '{token}' not in allowed executions {sorted(executions.keys())}"]

    return token, []


def print_result(composed):
    print(f"authority: {composed['authority']}")
    print(f"system:    {composed['system']}")
    print(f"product:   {composed['product']}")
    if composed.get("subsystem"):
        print(f"subsystem: {composed['subsystem']}")
    print(f"domain:    {composed['domain']}")
    print(f"entity:    {composed['entity']}")
    print(f"action:    {composed['action']}")
    if composed.get("execution"):
        print(f"execution: {composed['execution']}")
    print(f"function:  {composed['function']}")
    print(f"class:     {composed['class']}")
    print(f"route:     {composed['route']}")
    print(f"namespace: {composed['namespace']}")
    print(f"file:      {composed['file']}")


def validate_working_tree(src_path=None):
    """
    Walk src/ and validate all PHP files against the SPX protocol.

    Called by CI as the authoritative repository-scanning entry point.
    Returns True on clean pass, False on any violation.
    Skips src/Protocol/ (protocol-internal infrastructure; exempt from SPX naming).
    Handles a missing src/ directory gracefully — returns True (nothing to check).

    Parameters
    ----------
    src_path : str or None
        Path to the source directory to scan.  Defaults to "src".
    """
    import re
    import pathlib

    src_root = pathlib.Path(src_path) if src_path is not None else pathlib.Path("src")

    if not src_root.exists():
        print("SPX: src/ not found; no PHP files to validate.")
        return True

    vocab = load_vocab()

    domains    = _domain_keys(vocab)
    entities   = _entity_keys(vocab)
    actions    = _action_keys(vocab)
    structure  = vocab.get("structure", {})
    executions = set(vocab.get("executions", {}).keys())

    authorities = set(structure.get("authorities", []))
    systems     = set(structure.get("systems",     []))
    products    = set(structure.get("products",    []))
    subsystems  = set(structure.get("subsystems",  []))

    allowed_suffixes  = vocab.get("allowed_class_suffixes",  ["Service"])
    forbidden_suffixes = vocab.get("forbidden_class_suffixes", [])

    violations = []
    checked    = 0

    def pascal_ok(seg):
        """
        True when seg is already the expected PascalCase form of its own text.

        SPX vocabulary tokens are single lowercase words (e.g. 'audio', 'artifact',
        'brain').  PascalCase for those is simply ucfirst(strtolower) — identical
        to the PHP validator's spxToPascal() helper.  Directory segments are always
        single-word vocab tokens, so compound-word PascalCase never occurs here.
        """
        if not seg:
            return True
        return seg == seg[0].upper() + seg[1:].lower()

    def pascal_expected(seg):
        if not seg:
            return seg
        return seg[0].upper() + seg[1:].lower()

    for php_file in sorted(src_root.rglob("*.php")):
        # rel is relative to the repo root so its parts start with 'src'
        # e.g. ('src', 'Artifact', 'Audio', 'TranscribeService.php')
        rel   = php_file.relative_to(src_root.parent)
        parts = rel.parts

        # Skip Protocol-internal infrastructure
        if len(parts) >= 2 and parts[1] == "Protocol":
            continue

        checked += 1
        rel_str     = "/".join(parts)
        file_errors = []

        # ------------------------------------------------------------------ #
        # 1. Path-segment validation                                           #
        # Legacy:    src/{Domain}/{Entity}/File.php             (4 parts)      #
        # Full:      src/{Auth}/{Sys}/{Prod}/{Domain}/{Entity}/File.php (7)    #
        # Full+sub:  src/{Auth}/{Sys}/{Prod}/{Sub}/{Domain}/{Entity}/File.php (8) #
        # ------------------------------------------------------------------ #
        seg_count   = len(parts)
        path_domain = None
        path_entity = None

        if seg_count == 4:
            pd_pascal = parts[1]
            pe_pascal = parts[2]
            for seg, label in [(pd_pascal, "domain"), (pe_pascal, "entity")]:
                if not pascal_ok(seg):
                    file_errors.append(
                        f"  Path {label}: must be PascalCase, "
                        f"got '{seg}' (expected '{pascal_expected(seg)}')"
                    )
            path_domain = pd_pascal.lower()
            path_entity = pe_pascal.lower()

        elif seg_count == 7:
            pa_pascal, ps_pascal, pp_pascal = parts[1], parts[2], parts[3]
            pd_pascal, pe_pascal            = parts[4], parts[5]
            for seg, label in [
                (pa_pascal, "authority"), (ps_pascal, "system"), (pp_pascal, "product"),
                (pd_pascal, "domain"),    (pe_pascal, "entity"),
            ]:
                if not pascal_ok(seg):
                    file_errors.append(
                        f"  Path {label}: must be PascalCase, "
                        f"got '{seg}' (expected '{pascal_expected(seg)}')"
                    )
            if authorities and pa_pascal.lower() not in authorities:
                file_errors.append(f"  Path authority: '{pa_pascal.lower()}' not in vocab")
            if systems and ps_pascal.lower() not in systems:
                file_errors.append(f"  Path system: '{ps_pascal.lower()}' not in vocab")
            if products and pp_pascal.lower() not in products:
                file_errors.append(f"  Path product: '{pp_pascal.lower()}' not in vocab")
            path_domain = pd_pascal.lower()
            path_entity = pe_pascal.lower()

        elif seg_count == 8:
            pa_pascal, ps_pascal, pp_pascal = parts[1], parts[2], parts[3]
            psub_pascal                     = parts[4]
            pd_pascal, pe_pascal            = parts[5], parts[6]
            for seg, label in [
                (pa_pascal,   "authority"), (ps_pascal,   "system"),
                (pp_pascal,   "product"),   (psub_pascal, "subsystem"),
                (pd_pascal,   "domain"),    (pe_pascal,   "entity"),
            ]:
                if not pascal_ok(seg):
                    file_errors.append(
                        f"  Path {label}: must be PascalCase, "
                        f"got '{seg}' (expected '{pascal_expected(seg)}')"
                    )
            if authorities and pa_pascal.lower() not in authorities:
                file_errors.append(f"  Path authority: '{pa_pascal.lower()}' not in vocab")
            if systems and ps_pascal.lower() not in systems:
                file_errors.append(f"  Path system: '{ps_pascal.lower()}' not in vocab")
            if products and pp_pascal.lower() not in products:
                file_errors.append(f"  Path product: '{pp_pascal.lower()}' not in vocab")
            if subsystems and psub_pascal.lower() not in subsystems:
                file_errors.append(f"  Path subsystem: '{psub_pascal.lower()}' not in vocab")
            path_domain = pd_pascal.lower()
            path_entity = pe_pascal.lower()

        else:
            file_errors.append(
                f"  File path: unexpected depth ({seg_count} segments); "
                "expected 4 (legacy), 7 (full), or 8 (full+subsystem)"
            )

        if path_domain is not None:
            if path_domain not in domains:
                file_errors.append(f"  Path domain: '{path_domain}' not in vocab")
            if path_entity not in entities:
                file_errors.append(f"  Path entity: '{path_entity}' not in vocab")

        # ------------------------------------------------------------------ #
        # 2. Read source                                                        #
        # ------------------------------------------------------------------ #
        try:
            source = php_file.read_text(encoding="utf-8")
        except Exception as exc:
            violations.append(f"CANNOT READ {rel_str}: {exc}")
            continue

        # ------------------------------------------------------------------ #
        # 3. Namespace validation                                               #
        # ------------------------------------------------------------------ #
        ns_match = re.search(
            r'^\s*namespace\s+(SPX(?:\\[A-Za-z]+){2,6})\s*;',
            source, re.MULTILINE
        )
        if not ns_match:
            file_errors.append(
                "  Namespace: expected 'SPX\\...\\{Domain}\\{Entity}', "
                "none found or wrong format"
            )
        else:
            ns_parts   = ns_match.group(1).split("\\")
            part_count = len(ns_parts)  # includes 'SPX'

            ns_domain_pascal = ns_parts[part_count - 2]
            ns_entity_pascal = ns_parts[part_count - 1]

            for seg, label in [(ns_domain_pascal, "domain"), (ns_entity_pascal, "entity")]:
                if not pascal_ok(seg):
                    file_errors.append(
                        f"  Namespace {label}: must be PascalCase, "
                        f"got '{seg}' (expected '{pascal_expected(seg)}')"
                    )

            if ns_domain_pascal.lower() not in domains:
                file_errors.append(
                    f"  Namespace domain: '{ns_domain_pascal.lower()}' not in vocab"
                )
            if ns_entity_pascal.lower() not in entities:
                file_errors.append(
                    f"  Namespace entity: '{ns_entity_pascal.lower()}' not in vocab"
                )

            # Full-protocol namespace (6+ parts): validate structure segments
            if part_count >= 6:
                for idx, (coord, allowed_set) in enumerate(
                    [("authority", authorities), ("system", systems), ("product", products)],
                    start=1,
                ):
                    seg = ns_parts[idx]
                    if not pascal_ok(seg):
                        file_errors.append(
                            f"  Namespace {coord}: must be PascalCase, "
                            f"got '{seg}' (expected '{pascal_expected(seg)}')"
                        )
                    if allowed_set and seg.lower() not in allowed_set:
                        file_errors.append(
                            f"  Namespace {coord}: '{seg.lower()}' not in vocab"
                        )
                if part_count >= 7:
                    seg = ns_parts[4]
                    if not pascal_ok(seg):
                        file_errors.append(
                            f"  Namespace subsystem: must be PascalCase, "
                            f"got '{seg}' (expected '{pascal_expected(seg)}')"
                        )
                    if subsystems and seg.lower() not in subsystems:
                        file_errors.append(
                            f"  Namespace subsystem: '{seg.lower()}' not in vocab"
                        )

        # ------------------------------------------------------------------ #
        # 4. Class-suffix validation                                           #
        # The regex is built dynamically from allowed_class_suffixes so that  #
        # adding a new allowed suffix to the vocab is automatically picked up. #
        # ------------------------------------------------------------------ #
        if allowed_suffixes:
            suffix_alts  = "|".join(re.escape(s) for s in allowed_suffixes)
            class_re     = re.compile(
                r'^\s*class\s+([A-Za-z]+(?:' + suffix_alts + r'))\b',
                re.MULTILINE,
            )
            class_match = class_re.search(source)
        else:
            class_match = None

        if class_match:
            class_name = class_match.group(1)

            # Identify which allowed suffix the class uses
            matched_suffix = next(
                (s for s in allowed_suffixes if class_name.endswith(s)), None
            )

            # Check forbidden suffixes (independent of match outcome)
            for suffix in forbidden_suffixes:
                if class_name.endswith(suffix):
                    file_errors.append(
                        f"  Class: '{class_name}' uses forbidden suffix '{suffix}'"
                    )
                    break

            if matched_suffix is None:
                file_errors.append(
                    f"  Class: '{class_name}' does not end with an "
                    f"allowed suffix {allowed_suffixes}"
                )
            else:
                # Action name is everything before the suffix
                action_name  = class_name[: -len(matched_suffix)]
                action_match = re.match(r'^([A-Z][a-z]+)$', action_name)
                if not action_match:
                    file_errors.append(
                        f"  Class: '{class_name}' must be "
                        f"{{Action}}{matched_suffix} "
                        f"(PascalCase action + '{matched_suffix}')"
                    )
                else:
                    class_action = action_name.lower()
                    if class_action not in actions:
                        file_errors.append(
                            f"  Class action: '{class_action}' not in vocab actions"
                        )

        # ------------------------------------------------------------------ #
        # 5. spx_ function name validation                                     #
        # ------------------------------------------------------------------ #
        for func_name in re.findall(
            r'^\s*function\s+(spx_[a-z_]+)\s*\(', source, re.MULTILINE
        ):
            func_parts   = func_name.split("_")  # ['spx', ...]
            part_count_f = len(func_parts)

            if func_parts[0] != "spx" or part_count_f < 4:
                file_errors.append(
                    f"  Function '{func_name}': must start with 'spx_' "
                    "and have domain/entity/action"
                )
                continue

            fd = fe = fa = None

            if part_count_f == 4:
                # Legacy: spx_domain_entity_action
                fd, fe, fa = func_parts[1], func_parts[2], func_parts[3]

            elif part_count_f == 7:
                # Full: spx_auth_sys_prod_domain_entity_action
                fd, fe, fa = func_parts[4], func_parts[5], func_parts[6]
                if authorities and func_parts[1] not in authorities:
                    file_errors.append(
                        f"  Function '{func_name}': authority '{func_parts[1]}' not in vocab"
                    )
                if systems and func_parts[2] not in systems:
                    file_errors.append(
                        f"  Function '{func_name}': system '{func_parts[2]}' not in vocab"
                    )
                if products and func_parts[3] not in products:
                    file_errors.append(
                        f"  Function '{func_name}': product '{func_parts[3]}' not in vocab"
                    )

            elif part_count_f == 8:
                # Full+exec:  spx_auth_sys_prod_domain_entity_action_exec
                # Full+sub:   spx_auth_sys_prod_sub_domain_entity_action
                if func_parts[4] in domains:
                    fd, fe, fa   = func_parts[4], func_parts[5], func_parts[6]
                    exec_token   = func_parts[7]
                    if exec_token not in executions:
                        file_errors.append(
                            f"  Function '{func_name}': "
                            f"execution '{exec_token}' not in vocab"
                        )
                else:
                    sub_token  = func_parts[4]
                    fd, fe, fa = func_parts[5], func_parts[6], func_parts[7]
                    if subsystems and sub_token not in subsystems:
                        file_errors.append(
                            f"  Function '{func_name}': "
                            f"subsystem '{sub_token}' not in vocab"
                        )
                if authorities and func_parts[1] not in authorities:
                    file_errors.append(
                        f"  Function '{func_name}': authority '{func_parts[1]}' not in vocab"
                    )
                if systems and func_parts[2] not in systems:
                    file_errors.append(
                        f"  Function '{func_name}': system '{func_parts[2]}' not in vocab"
                    )
                if products and func_parts[3] not in products:
                    file_errors.append(
                        f"  Function '{func_name}': product '{func_parts[3]}' not in vocab"
                    )

            else:
                file_errors.append(
                    f"  Function '{func_name}': unexpected part count "
                    f"({part_count_f}); expected 4, 7, or 8"
                )
                continue

            if fd is not None:
                if fd not in domains:
                    file_errors.append(
                        f"  Function '{func_name}': domain '{fd}' not in vocab"
                    )
                if fe not in entities:
                    file_errors.append(
                        f"  Function '{func_name}': entity '{fe}' not in vocab"
                    )
                if fa not in actions:
                    file_errors.append(
                        f"  Function '{func_name}': action '{fa}' not in vocab"
                    )
                if fd in domains and fe in entities and fa in actions:
                    for err in validate_constraints(fd, fe, fa, vocab):
                        file_errors.append(f"  Function '{func_name}': {err}")

        if file_errors:
            violations.append(f"VIOLATION: {rel_str}")
            violations.extend(file_errors)

    if violations:
        for v in violations:
            print(v, file=sys.stderr)
        return False

    print(f"SPX repository validation passed: {checked} file(s) checked, 0 violations.")
    return True


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
        {
            "label": "INVALID constraint — transcribe on session [EXPECT FAIL]",
            "structure": ("brain", "sparxstar", "player"),
            "inputs":    ("context", "session", "transcribe"),
            "expect_pass": False,
        },
        {
            "label": "INVALID constraint — transcribe wrong domain [EXPECT FAIL]",
            "structure": ("group", "aiwa", "archive"),
            "inputs":    ("lexicon", "word", "transcribe"),
            "expect_pass": False,
        },
        {
            "label": "with execution — stream audio read",
            "structure":  ("brain", "sparxstar", "player"),
            "inputs":     ("artifact", "audio", "read"),
            "execution":  "stream",
            "expect_pass": True,
        },
        {
            "label": "with execution — batch audio read",
            "structure":  ("brain", "sparxstar", "archive"),
            "inputs":     ("artifact", "audio", "read"),
            "execution":  "batch",
            "expect_pass": True,
        },
        {
            "label": "INVALID execution — hyphen [EXPECT FAIL]",
            "structure":  ("brain", "sparxstar", "player"),
            "inputs":     ("artifact", "audio", "read"),
            "execution":  "real-time",
            "expect_pass": False,
        },
        {
            "label": "INVALID execution — invented [EXPECT FAIL]",
            "structure":  ("brain", "sparxstar", "player"),
            "inputs":     ("artifact", "audio", "read"),
            "execution":  "turbo",
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
        exec_raw = test.get("execution")
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

        # Validate execution coordinate (optional)
        execution, ex_errors = validate_execution(exec_raw, vocab)
        if ex_errors:
            if not expect_pass:
                print(f"  CORRECTLY FAILED (execution): {'; '.join(ex_errors)}\n")
                passed += 1
            else:
                print(f"  UNEXPECTED EXECUTION FAILURE: {'; '.join(ex_errors)}\n", file=sys.stderr)
                failed += 1
            continue

        # Validate function signature
        coords, f_errors = resolve_coordinates(d, e, a, vocab)
        if execution is not None:
            coords["execution"] = execution

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
        constraint_errs = validate_constraints(coords["domain"], coords["entity"], coords["action"], vocab)
        payload_errs = validate_payload(payload, composed) if payload else []

        all_errors = casing_errs + ([suffix_err] if suffix_err else []) + constraint_errs + payload_errs

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
