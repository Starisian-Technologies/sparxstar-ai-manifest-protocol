<?php

declare(strict_types=1);

/**
 * SPX Protocol Validator
 *
 * Reads system/spx-vocab.json and scans src/ for compliance with the SPX naming protocol.
 *
 * Exit codes:
 *   0 — all files pass
 *   1 — one or more violations found
 */

$repoRoot  = dirname(__DIR__);
$vocabPath = $repoRoot . '/system/spx-vocab.json';
$srcPath   = $repoRoot . '/src';

// ---------------------------------------------------------------------------
// Load vocabulary
// ---------------------------------------------------------------------------

if (!file_exists($vocabPath)) {
    fwrite(STDERR, "ERROR: Vocab file not found: {$vocabPath}\n");
    exit(1);
}

$vocabJson = file_get_contents($vocabPath);
if ($vocabJson === false) {
    fwrite(STDERR, "ERROR: Could not read vocab file: {$vocabPath}\n");
    exit(1);
}

$vocab = json_decode($vocabJson, true);
if (!is_array($vocab)) {
    fwrite(STDERR, "ERROR: Invalid JSON in vocab file: {$vocabPath}\n");
    exit(1);
}

// ---------------------------------------------------------------------------
// Helper: extract canonical keys from either flat-list or dict-style vocab
// ---------------------------------------------------------------------------

function spxVocabKeys(array $vocab, string $key): array
{
    $val = $vocab[$key] ?? [];
    if (!is_array($val)) {
        return [];
    }
    // Dict-style: ['audio' => [...], 'word' => [...]] — keys are the canonical tokens
    if (!empty($val) && is_string(array_key_first($val))) {
        return array_map('strtolower', array_keys($val));
    }
    // Flat list: ['audio', 'word', ...]
    return array_map('strtolower', $val);
}

// ---------------------------------------------------------------------------
// Helper: extract keys from a nested structure sub-key
// ---------------------------------------------------------------------------

function spxStructureKeys(array $vocab, string $subKey): array
{
    $structure = $vocab['structure'] ?? [];
    $val = $structure[$subKey] ?? [];
    if (!is_array($val)) {
        return [];
    }
    // Dict-style: ['brain' => [...], 'group' => [...]] — keys are canonical tokens
    if (!empty($val) && is_string(array_key_first($val))) {
        return array_map('strtolower', array_keys($val));
    }
    // Flat list fallback
    return array_map('strtolower', $val);
}

$domains     = spxVocabKeys($vocab, 'domains');
$entities    = spxVocabKeys($vocab, 'entities');
$actions     = spxVocabKeys($vocab, 'actions');
$executions  = spxVocabKeys($vocab, 'executions');
$authorities = spxStructureKeys($vocab, 'authorities');
$systems     = spxStructureKeys($vocab, 'systems');
$products    = spxStructureKeys($vocab, 'products');
$subsystems  = spxStructureKeys($vocab, 'subsystems');

if (empty($domains) || empty($entities) || empty($actions)) {
    fwrite(STDERR, "ERROR: Vocab file must define non-empty 'domains', 'entities', and 'actions'.\n");
    exit(1);
}

// ---------------------------------------------------------------------------
// Forbidden words (may never appear in any namespace segment, class, or function name)
// ---------------------------------------------------------------------------

$forbiddenWords = [
    'Manager', 'Engine', 'Processor', 'Handler', 'Pipeline',
    'Controller', 'Helper', 'Util', 'Utils', 'Base', 'Abstract',
    'Factory', 'Builder', 'Registry', 'Repository', 'Facade',
    'Adapter', 'Proxy', 'Decorator', 'Observer', 'Listener', 'Emitter',
];

// ---------------------------------------------------------------------------
// Helper: PascalCase a lowercase vocab word
// ---------------------------------------------------------------------------

function spxToPascal(string $word): string
{
    return ucfirst(strtolower($word));
}

// ---------------------------------------------------------------------------
// Collect PHP files under src/
// ---------------------------------------------------------------------------

if (!is_dir($srcPath)) {
    fwrite(STDERR, "ERROR: src/ directory not found: {$srcPath}\n");
    exit(1);
}

/** @var SplFileInfo[] $phpFiles */
$phpFiles = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($srcPath, FilesystemIterator::SKIP_DOTS)
);

$violations = [];
$checked    = 0;

foreach ($phpFiles as $file) {
    if ($file->getExtension() !== 'php') {
        continue;
    }

    ++$checked;
    $filePath     = $file->getRealPath();
    $relativePath = str_replace($repoRoot . '/', '', $filePath);
    $fileErrors   = [];

    // -----------------------------------------------------------------------
    // Skip protocol-internal infrastructure (not a domain service)
    // -----------------------------------------------------------------------

    if (strpos($relativePath, 'src/Protocol/') === 0) {
        --$checked;
        continue;
    }

    // -----------------------------------------------------------------------
    // Parse the relative path.
    //
    // Legacy (3-coord):  src/{Domain}/{Entity}/{Action}Service.php  — 4 segments
    // Full protocol:     src/{Auth}/{Sys}/{Prod}/{Domain}/{Entity}/{Action}Service.php — 7 segments
    // Full + subsystem:  src/{Auth}/{Sys}/{Prod}/{Sub}/{Domain}/{Entity}/{Action}Service.php — 8 segments
    // -----------------------------------------------------------------------

    $pathSegments = explode('/', str_replace('\\', '/', $relativePath));
    $segCount     = count($pathSegments);

    // Minimum: src + at least Domain + Entity + File = 4
    // Maximum so far: 8 (with subsystem)
    if ($segCount < 4 || $pathSegments[0] !== 'src') {
        $fileErrors[] = sprintf(
            "  File path: expected 'src/.../{Action}Service.php' structure, got '%s'",
            $relativePath
        );
        $pathFileName     = null;
        $pathActionPascal = null;
        $pathDomainPascal = null;
        $pathEntityPascal = null;
        $nsDomainPascal   = null;
        $nsEntityPascal   = null;
    } else {
        $pathFileName = $pathSegments[$segCount - 1];

        // File name must be {Action}[{Execution}]Service.php
        // Split the stem before "Service.php" to get the action (and optional execution) parts.
        if (!preg_match('/^([A-Z][A-Za-z]+?)(?:([A-Z][A-Za-z]+))?Service\.php$/', $pathFileName, $fileNameMatch)) {
            $fileErrors[] = sprintf(
                "  File name: expected '{Action}[{Execution}]Service.php' (PascalCase), got '%s'",
                $pathFileName
            );
            $pathActionPascal = null;
        } else {
            // Check if the full PascalCase stem before "Service" is a single action
            // or an action+execution compound (e.g. ReadStream = Read + Stream)
            $fullStem     = $fileNameMatch[1] . ($fileNameMatch[2] ?? '');
            $stemLower    = strtolower($fullStem);
            $part1Lower   = strtolower($fileNameMatch[1]);
            $part2        = $fileNameMatch[2] ?? null;
            $part2Lower   = $part2 !== null ? strtolower($part2) : null;

            if (in_array($stemLower, $actions, true)) {
                // Single action: e.g. TranscribeService.php
                $pathActionPascal = $fullStem;
                $pathAction       = $stemLower;
            } elseif (in_array($part1Lower, $actions, true)) {
                // Action + optional execution: e.g. ReadStreamService.php
                $pathActionPascal = $fileNameMatch[1];
                $pathAction       = $part1Lower;
                if ($part2Lower !== null && !in_array($part2Lower, $executions, true)) {
                    $fileErrors[] = sprintf(
                        "  File execution: '%s' is not in allowed executions [%s] (in '%s')",
                        $part2Lower,
                        implode(', ', $executions),
                        $pathFileName
                    );
                }
            } else {
                $fileErrors[] = sprintf(
                    "  Path action: expected one of [%s], got '%s'",
                    implode(', ', $actions),
                    $part1Lower
                );
                $pathActionPascal = null;
                $pathAction       = null;
            }
        }

        // Identify Domain and Entity position based on segment count
        // Legacy 4-segment: src/Domain/Entity/File.php
        // Full 7-segment:   src/Auth/Sys/Prod/Domain/Entity/File.php
        // Full 8-segment:   src/Auth/Sys/Prod/Sub/Domain/Entity/File.php
        if ($segCount === 4) {
            // Legacy
            $pathDomainPascal = $pathSegments[1];
            $pathEntityPascal = $pathSegments[2];
        } elseif ($segCount === 7) {
            // Full protocol: src/Auth/Sys/Prod/Domain/Entity/File
            $pathAuthPascal   = $pathSegments[1];
            $pathSysPascal    = $pathSegments[2];
            $pathProdPascal   = $pathSegments[3];
            $pathDomainPascal = $pathSegments[4];
            $pathEntityPascal = $pathSegments[5];

            if (!empty($authorities) && !in_array(strtolower($pathAuthPascal), $authorities, true)) {
                $fileErrors[] = sprintf(
                    "  Path authority: expected one of [%s], got '%s'",
                    implode(', ', $authorities),
                    strtolower($pathAuthPascal)
                );
            }
            if (!empty($systems) && !in_array(strtolower($pathSysPascal), $systems, true)) {
                $fileErrors[] = sprintf(
                    "  Path system: expected one of [%s], got '%s'",
                    implode(', ', $systems),
                    strtolower($pathSysPascal)
                );
            }
            if (!empty($products) && !in_array(strtolower($pathProdPascal), $products, true)) {
                $fileErrors[] = sprintf(
                    "  Path product: expected one of [%s], got '%s'",
                    implode(', ', $products),
                    strtolower($pathProdPascal)
                );
            }
        } elseif ($segCount === 8) {
            // Full + subsystem: src/Auth/Sys/Prod/Sub/Domain/Entity/File
            $pathAuthPascal   = $pathSegments[1];
            $pathSysPascal    = $pathSegments[2];
            $pathProdPascal   = $pathSegments[3];
            $pathSubPascal    = $pathSegments[4];
            $pathDomainPascal = $pathSegments[5];
            $pathEntityPascal = $pathSegments[6];

            if (!empty($authorities) && !in_array(strtolower($pathAuthPascal), $authorities, true)) {
                $fileErrors[] = sprintf(
                    "  Path authority: expected one of [%s], got '%s'",
                    implode(', ', $authorities),
                    strtolower($pathAuthPascal)
                );
            }
            if (!empty($systems) && !in_array(strtolower($pathSysPascal), $systems, true)) {
                $fileErrors[] = sprintf(
                    "  Path system: expected one of [%s], got '%s'",
                    implode(', ', $systems),
                    strtolower($pathSysPascal)
                );
            }
            if (!empty($products) && !in_array(strtolower($pathProdPascal), $products, true)) {
                $fileErrors[] = sprintf(
                    "  Path product: expected one of [%s], got '%s'",
                    implode(', ', $products),
                    strtolower($pathProdPascal)
                );
            }
            if (!empty($subsystems) && !in_array(strtolower($pathSubPascal), $subsystems, true)) {
                $fileErrors[] = sprintf(
                    "  Path subsystem: expected one of [%s], got '%s'",
                    implode(', ', $subsystems),
                    strtolower($pathSubPascal)
                );
            }
        } else {
            $fileErrors[] = sprintf(
                "  File path: unexpected depth (got %d segments), expected 4 (legacy), 7 (full), or 8 (full+subsystem) in '%s'",
                $segCount,
                $relativePath
            );
            $pathDomainPascal = null;
            $pathEntityPascal = null;
        }

        if (isset($pathDomainPascal, $pathEntityPascal)) {
            $pathDomain = strtolower($pathDomainPascal);
            $pathEntity = strtolower($pathEntityPascal);

            if (!in_array($pathDomain, $domains, true)) {
                $fileErrors[] = sprintf(
                    "  Path domain: expected one of [%s], got '%s'",
                    implode(', ', $domains),
                    $pathDomain
                );
            }

            if (!in_array($pathEntity, $entities, true)) {
                $fileErrors[] = sprintf(
                    "  Path entity: expected one of [%s], got '%s'",
                    implode(', ', $entities),
                    $pathEntity
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Read and parse file contents
    // -----------------------------------------------------------------------

    $source = file_get_contents($filePath);
    if ($source === false) {
        $violations[] = "CANNOT READ: {$relativePath}";
        continue;
    }

    // -----------------------------------------------------------------------
    // Rule 1: Namespace format
    //
    // Legacy:        SPX\{Domain}\{Entity}                  (3 parts)
    // Full protocol: SPX\{Auth}\{Sys}\{Prod}\{Domain}\{Entity} (6 parts)
    // Full+sub:      SPX\{Auth}\{Sys}\{Prod}\{Sub}\{Domain}\{Entity} (7 parts)
    // -----------------------------------------------------------------------

    if (!preg_match('/^\s*namespace\s+(SPX(?:\\\\[A-Za-z]+){2,6})\s*;/m', $source, $nsMatch)) {
        $fileErrors[] = "  Namespace: expected 'SPX\\...\\{Domain}\\{Entity}', none found or wrong format";
        $nsDomain = $nsEntity = null;
        $nsDomainPascal = $nsEntityPascal = null;
    } else {
        $fullNamespace  = $nsMatch[1];
        $nsParts        = explode('\\', $fullNamespace);
        $partCount      = count($nsParts); // includes 'SPX'

        // Last two parts are always Domain, Entity
        $nsDomainPascal = $nsParts[$partCount - 2];
        $nsEntityPascal = $nsParts[$partCount - 1];
        $nsDomain       = strtolower($nsDomainPascal);
        $nsEntity       = strtolower($nsEntityPascal);

        if (!in_array($nsDomain, $domains, true)) {
            $fileErrors[] = sprintf(
                "  Namespace domain: expected one of [%s], got '%s' (in '%s')",
                implode(', ', $domains),
                $nsDomain,
                $fullNamespace
            );
        }

        if (!in_array($nsEntity, $entities, true)) {
            $fileErrors[] = sprintf(
                "  Namespace entity: expected one of [%s], got '%s' (in '%s')",
                implode(', ', $entities),
                $nsEntity,
                $fullNamespace
            );
        }

        // If full protocol (6+ parts: SPX\Auth\Sys\Prod\...\Domain\Entity), validate structure coords
        if ($partCount >= 5 && !empty($authorities)) {
            $nsAuth = strtolower($nsParts[1]);
            if (!in_array($nsAuth, $authorities, true)) {
                $fileErrors[] = sprintf(
                    "  Namespace authority: expected one of [%s], got '%s' (in '%s')",
                    implode(', ', $authorities),
                    $nsAuth,
                    $fullNamespace
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Rule 2: Class name — {Action}Service
    // -----------------------------------------------------------------------

    if (!preg_match('/^\s*class\s+([A-Za-z]+Service)\b/m', $source, $classMatch)) {
        $fileErrors[] = "  Class: expected '{Action}Service', none found";
        $classAction = null;
    } else {
        $className = $classMatch[1];

        if (!preg_match('/^([A-Z][a-z]+)Service$/', $className, $classActionMatch)) {
            $fileErrors[] = sprintf(
                "  Class name: expected '{Action}Service' (PascalCase action + 'Service'), got '%s'",
                $className
            );
            $classAction = null;
        } else {
            $classAction = strtolower($classActionMatch[1]);

            if (!in_array($classAction, $actions, true)) {
                $fileErrors[] = sprintf(
                    "  Class action: expected one of [%s], got '%s' (in class '%s')",
                    implode(', ', $actions),
                    $classAction,
                    $className
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Rule 3: Function names
    //
    // Legacy:        spx_{domain}_{entity}_{action}                  (4 parts)
    // Full protocol: spx_{auth}_{sys}_{prod}_{domain}_{entity}_{action}      (7 parts)
    // Full+sub:      spx_{auth}_{sys}_{prod}_{sub}_{domain}_{entity}_{action} (8 parts)
    // Full+exec:     spx_{auth}_{sys}_{prod}_{domain}_{entity}_{action}_{exec} (8 parts)
    // -----------------------------------------------------------------------

    preg_match_all('/^\s*function\s+(spx_[a-z_]+)\s*\(/m', $source, $funcMatches, PREG_SET_ORDER);

    if (empty($funcMatches)) {
        preg_match_all('/^\s*function\s+([a-zA-Z_]+)\s*\(/m', $source, $allFuncMatches, PREG_SET_ORDER);
        $nonSpxFunctions = array_filter(
            $allFuncMatches,
            static fn(array $m): bool => strpos($m[1], 'spx_') !== 0
        );

        if (!empty($nonSpxFunctions)) {
            foreach ($nonSpxFunctions as $nf) {
                $fileErrors[] = sprintf(
                    "  Function name: expected 'spx_{...}_{domain}_{entity}_{action}', got '%s'",
                    $nf[1]
                );
            }
        }
    } else {
        foreach ($funcMatches as $funcMatch) {
            $funcName  = $funcMatch[1];
            $funcParts = explode('_', $funcName); // ['spx', ...]
            $partCount = count($funcParts);

            // Must start with 'spx' and have at least 4 parts (legacy minimum)
            if ($funcParts[0] !== 'spx' || $partCount < 4) {
                $fileErrors[] = sprintf(
                    "  Function name: must start with 'spx_' and have domain/entity/action, got '%s'",
                    $funcName
                );
                continue;
            }

            if ($partCount === 4) {
                // Legacy: spx_domain_entity_action
                $funcDomain = $funcParts[1];
                $funcEntity = $funcParts[2];
                $funcAction = $funcParts[3];
            } elseif ($partCount === 7) {
                // Full protocol: spx_auth_sys_prod_domain_entity_action
                $funcDomain = $funcParts[4];
                $funcEntity = $funcParts[5];
                $funcAction = $funcParts[6];
                if (!empty($authorities) && !in_array($funcParts[1], $authorities, true)) {
                    $fileErrors[] = sprintf(
                        "  Function authority: expected one of [%s], got '%s' (in '%s')",
                        implode(', ', $authorities),
                        $funcParts[1],
                        $funcName
                    );
                }
            } elseif ($partCount === 8) {
                // Full+sub or full+exec: spx_auth_sys_prod_{sub_or_domain}_entity_action_{exec_or_nothing}
                // Domain is always in positions 4 or 5 — determine by vocab membership
                $candidate4 = $funcParts[4];
                $candidate5 = $funcParts[5];
                if (in_array($candidate4, $domains, true)) {
                    // spx_auth_sys_prod_domain_entity_action_exec
                    $funcDomain = $candidate4;
                    $funcEntity = $candidate5;
                    $funcAction = $funcParts[6];
                } else {
                    // spx_auth_sys_prod_sub_domain_entity_action
                    $funcDomain = $candidate5;
                    $funcEntity = $funcParts[6];
                    $funcAction = $funcParts[7];
                }
                if (!empty($authorities) && !in_array($funcParts[1], $authorities, true)) {
                    $fileErrors[] = sprintf(
                        "  Function authority: expected one of [%s], got '%s' (in '%s')",
                        implode(', ', $authorities),
                        $funcParts[1],
                        $funcName
                    );
                }
            } else {
                $fileErrors[] = sprintf(
                    "  Function name: unexpected part count (%d) in '%s'; expected 4 (legacy), 7, or 8 (full protocol)",
                    $partCount,
                    $funcName
                );
                continue;
            }

            if (!in_array($funcDomain, $domains, true)) {
                $fileErrors[] = sprintf(
                    "  Function domain: expected one of [%s], got '%s' (in '%s')",
                    implode(', ', $domains),
                    $funcDomain,
                    $funcName
                );
            }

            if (!in_array($funcEntity, $entities, true)) {
                $fileErrors[] = sprintf(
                    "  Function entity: expected one of [%s], got '%s' (in '%s')",
                    implode(', ', $entities),
                    $funcEntity,
                    $funcName
                );
            }

            if (!in_array($funcAction, $actions, true)) {
                $fileErrors[] = sprintf(
                    "  Function action: expected one of [%s], got '%s' (in '%s')",
                    implode(', ', $actions),
                    $funcAction,
                    $funcName
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Rule 5: No forbidden words in identifiers
    //
    // Collect the actual identifier strings found in the file and check each
    // one for forbidden word substrings.  Using stripos (not \b) is necessary
    // because PascalCase compound words share no word-boundary between their
    // components (e.g. "TranscribeHandler" has no \b before "Handler").
    // -----------------------------------------------------------------------

    $identifiersToCheck = [];

    // Namespace segments
    if (preg_match('/^\s*namespace\s+([A-Za-z\\\\]+)\s*;/m', $source, $nsRaw)) {
        foreach (explode('\\', $nsRaw[1]) as $seg) {
            $identifiersToCheck[] = $seg;
        }
    }

    // Class name(s)
    preg_match_all('/^\s*(?:abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)/m', $source, $classRaw);
    foreach ($classRaw[1] ?? [] as $cn) {
        $identifiersToCheck[] = $cn;
    }

    // Function names (all of them)
    preg_match_all('/^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/m', $source, $funcRaw);
    foreach ($funcRaw[1] ?? [] as $fn) {
        $identifiersToCheck[] = $fn;
    }

    foreach ($identifiersToCheck as $identifier) {
        foreach ($forbiddenWords as $word) {
            if (stripos($identifier, $word) !== false) {
                $fileErrors[] = sprintf(
                    "  Forbidden word: '%s' must not appear in any identifier (found in '%s')",
                    $word,
                    $identifier
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Rule 6: File path must be consistent with namespace + class
    // -----------------------------------------------------------------------

    if (isset($pathDomainPascal, $pathEntityPascal, $nsDomainPascal, $nsEntityPascal)) {
        if ($pathDomainPascal !== $nsDomainPascal) {
            $fileErrors[] = sprintf(
                "  Path/namespace mismatch (domain): path has '%s', namespace has '%s'",
                $pathDomainPascal,
                $nsDomainPascal
            );
        }

        if ($pathEntityPascal !== $nsEntityPascal) {
            $fileErrors[] = sprintf(
                "  Path/namespace mismatch (entity): path has '%s', namespace has '%s'",
                $pathEntityPascal,
                $nsEntityPascal
            );
        }
    }

    if (isset($pathActionPascal, $classAction)) {
        if (strtolower($pathActionPascal) !== $classAction) {
            $fileErrors[] = sprintf(
                "  Path/class mismatch (action): path file is '%sService.php', class is '%sService'",
                $pathActionPascal,
                ucfirst($classAction)
            );
        }
    }

    // -----------------------------------------------------------------------
    // Collect violations for this file
    // -----------------------------------------------------------------------

    if (!empty($fileErrors)) {
        $violations[] = "VIOLATION: {$relativePath}";
        foreach ($fileErrors as $err) {
            $violations[] = $err;
        }
    }
}

// ---------------------------------------------------------------------------
// Report results
// ---------------------------------------------------------------------------

if ($checked === 0) {
    echo "No PHP files found in src/. Nothing to validate.\n";
    exit(0);
}

if (!empty($violations)) {
    foreach ($violations as $line) {
        echo $line . "\n";
    }
    echo "\nValidation FAILED: " . count(array_filter($violations, static fn(string $l): bool => strpos($l, 'VIOLATION:') === 0)) . " file(s) with violations.\n";
    exit(1);
}

echo "Validation PASSED: {$checked} file(s) checked, 0 violations.\n";
exit(0);
