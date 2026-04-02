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

$domains  = array_map('strtolower', (array) ($vocab['domains']  ?? []));
$entities = array_map('strtolower', (array) ($vocab['entities'] ?? []));
$actions  = array_map('strtolower', (array) ($vocab['actions']  ?? []));

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
    // Parse the relative path: src/{Domain}/{Entity}/{Action}Service.php
    // -----------------------------------------------------------------------

    $pathSegments = explode('/', str_replace('\\', '/', $relativePath));

    // Expected: ['src', DomainPascal, EntityPascal, ActionPascalService.php]
    if (count($pathSegments) !== 4 || $pathSegments[0] !== 'src') {
        $fileErrors[] = sprintf(
            "  File path: expected 'src/{Domain}/{Entity}/{Action}Service.php', got '%s'",
            $relativePath
        );
    } else {
        $pathDomainPascal = $pathSegments[1];
        $pathEntityPascal = $pathSegments[2];
        $pathFileName     = $pathSegments[3];

        $pathDomain = strtolower($pathDomainPascal);
        $pathEntity = strtolower($pathEntityPascal);

        // Validate domain in path
        if (!in_array($pathDomain, $domains, true)) {
            $fileErrors[] = sprintf(
                "  Path domain: expected one of [%s], got '%s'",
                implode(', ', $domains),
                $pathDomain
            );
        }

        // Validate entity in path
        if (!in_array($pathEntity, $entities, true)) {
            $fileErrors[] = sprintf(
                "  Path entity: expected one of [%s], got '%s'",
                implode(', ', $entities),
                $pathEntity
            );
        }

        // Validate file name: {Action}Service.php
        if (!preg_match('/^([A-Z][a-z]+)Service\.php$/', $pathFileName, $fileNameMatch)) {
            $fileErrors[] = sprintf(
                "  File name: expected '{Action}Service.php' (PascalCase action), got '%s'",
                $pathFileName
            );
            $pathActionPascal = null;
        } else {
            $pathActionPascal = $fileNameMatch[1];
            $pathAction       = strtolower($pathActionPascal);

            if (!in_array($pathAction, $actions, true)) {
                $fileErrors[] = sprintf(
                    "  Path action: expected one of [%s], got '%s'",
                    implode(', ', $actions),
                    $pathAction
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
    // Rule 1: Namespace format — SPX\{Domain}\{Entity}
    // -----------------------------------------------------------------------

    if (!preg_match('/^\s*namespace\s+(SPX\\\\([A-Za-z]+)\\\\([A-Za-z]+))\s*;/m', $source, $nsMatch)) {
        $fileErrors[] = "  Namespace: expected 'SPX\\{Domain}\\{Entity}', none found or wrong format";
        $nsDomain = $nsEntity = null;
    } else {
        $fullNamespace = $nsMatch[1];
        $nsDomainPascal = $nsMatch[2];
        $nsEntityPascal = $nsMatch[3];
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
    // Rule 3: Function names — spx_{domain}_{entity}_{action}
    // -----------------------------------------------------------------------

    preg_match_all('/^\s*function\s+(spx_([a-z]+)_([a-z]+)_([a-z]+))\s*\(/m', $source, $funcMatches, PREG_SET_ORDER);

    if (empty($funcMatches)) {
        // Only flag missing function if there are no functions at all, or only wrongly named ones
        preg_match_all('/^\s*function\s+([a-zA-Z_]+)\s*\(/m', $source, $allFuncMatches, PREG_SET_ORDER);
        $nonSpxFunctions = array_filter(
            $allFuncMatches,
            static fn(array $m): bool => strpos($m[1], 'spx_') !== 0
        );

        if (!empty($nonSpxFunctions)) {
            foreach ($nonSpxFunctions as $nf) {
                $fileErrors[] = sprintf(
                    "  Function name: expected 'spx_{domain}_{entity}_{action}', got '%s'",
                    $nf[1]
                );
            }
        }
    } else {
        foreach ($funcMatches as $funcMatch) {
            $funcName       = $funcMatch[1];
            $funcDomain     = $funcMatch[2];
            $funcEntity     = $funcMatch[3];
            $funcAction     = $funcMatch[4];

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
    // Rule 6: File path must match /src/{DomainPascal}/{EntityPascal}/{ActionPascal}Service.php
    //         and be consistent with namespace + class
    // -----------------------------------------------------------------------

    if (isset($pathDomainPascal, $pathEntityPascal, $pathActionPascal, $nsDomainPascal, $nsEntityPascal)) {
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
