<?php

declare(strict_types=1);

namespace SPX\Protocol;

/**
 * SPX Protocol Validator
 * Authority: spx-vocab.json
 * Contract:  CONTRACT.md
 *
 * Rule: Same input + same vocab = SAME output.
 * If not, the protocol is incomplete.
 */
class Validator
{
    private array $vocab;

    public function __construct(?string $vocabPath = null)
    {
        $vocabPath = $vocabPath ?? dirname(__DIR__, 2) . '/system/spx-vocab.json';

        if (!file_exists($vocabPath)) {
            throw new \RuntimeException("SPX PROTOCOL ERROR: vocab file not found at '{$vocabPath}'");
        }

        $decoded = json_decode((string) file_get_contents($vocabPath), true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \RuntimeException("SPX PROTOCOL ERROR: spx-vocab.json is not valid JSON");
        }

        $this->vocab = $decoded;
    }

    /**
     * Normalize a raw token against the synonym map and allowed values.
     * Returns null if unmappable.
     *
     * Supports both flat-list and dict-style (v2.x) vocab.
     */
    public function normalize(string $token, string $coordinate): ?string
    {
        $token        = strtolower(trim($token));
        $allowedLookup = $this->getAllowedCoordinateLookup($coordinate);

        if (isset($allowedLookup[$token])) {
            return $token;
        }

        $synonym = $this->vocab['synonyms'][$token] ?? null;

        if (is_string($synonym)) {
            $synonym = strtolower(trim($synonym));
            if (isset($allowedLookup[$synonym])) {
                return $synonym;
            }
        }

        return null;
    }

    /**
     * Build a canonical lookup table for a coordinate collection.
     *
     * Supports:
     * - flat lists of strings;
     * - associative arrays keyed by canonical token;
     * - nested arrays containing a string 'value' field.
     *
     * @return array<string, true>
     */
    private function getAllowedCoordinateLookup(string $coordinate): array
    {
        $rawAllowed = $this->vocab[$coordinate . 's'] ?? [];

        if (!is_array($rawAllowed)) {
            return [];
        }

        $lookup = [];

        foreach ($rawAllowed as $key => $definition) {
            if (is_string($key) && $key !== '') {
                $lookup[strtolower(trim($key))] = true;
            }

            if (is_string($definition) && $definition !== '') {
                $lookup[strtolower(trim($definition))] = true;
                continue;
            }

            if (is_array($definition) && isset($definition['value']) && is_string($definition['value']) && $definition['value'] !== '') {
                $lookup[strtolower(trim($definition['value']))] = true;
            }
        }

        return $lookup;
    }

    /**
     * Resolve raw intent coordinates to canonical protocol coordinates.
     * Throws on any unmappable input.
     */
    public function resolve(string $domainRaw, string $entityRaw, string $actionRaw): array
    {
        $domain = $this->normalize($domainRaw, 'domain');
        $entity = $this->normalize($entityRaw, 'entity');
        $action = $this->normalize($actionRaw, 'action');

        $errors = [];

        if ($domain === null) {
            $errors[] = "domain '{$domainRaw}' is not in allowed domains and has no synonym mapping";
        }
        if ($entity === null) {
            $errors[] = "entity '{$entityRaw}' is not in allowed entities and has no synonym mapping";
        }
        if ($action === null) {
            $errors[] = "action '{$actionRaw}' is not in allowed actions and has no synonym mapping";
        }

        if (!empty($errors)) {
            throw new ProtocolException("INTENT UNRESOLVABLE: " . implode('; ', $errors));
        }

        return $this->compose($domain, $entity, $action);
    }

    /**
     * Compose deterministic outputs from resolved coordinates.
     * Composition is NOT invention.
     */
    public function compose(string $domain, string $entity, string $action): array
    {
        $d = $domain;
        $e = $entity;
        $a = $action;

        $dP = ucfirst($d);
        $eP = ucfirst($e);
        $aP = ucfirst($a);

        return [
            'domain'    => $d,
            'entity'    => $e,
            'action'    => $a,
            'function'  => "spx_{$d}_{$e}_{$a}",
            'class'     => "SPX\\{$dP}\\{$eP}\\{$aP}Service",
            'route'     => "/{$d}/{$e}/{$a}",
            'namespace' => "SPX\\{$dP}\\{$eP}",
            'file'      => "/src/{$dP}/{$eP}/{$aP}Service.php",
        ];
    }

    /**
     * Validate a payload array against expected composed output.
     * Throws on any mismatch.
     */
    public function validatePayload(array $payload, string $domain, string $entity, string $action): void
    {
        $expected = $this->compose($domain, $entity, $action);
        $errors   = [];

        foreach (['function', 'class', 'route', 'namespace', 'file'] as $field) {
            if (!isset($payload[$field])) {
                $errors[] = "missing field '{$field}'";
                continue;
            }
            if ($payload[$field] !== $expected[$field]) {
                $errors[] = "field '{$field}':\n    expected: {$expected[$field]}\n    got:      {$payload[$field]}";
            }
        }

        if (!empty($errors)) {
            throw new ProtocolException("CI FAILED:\n" . implode("\n", $errors));
        }
    }

    /**
     * Validate class suffix against allowed list.
     * Throws on forbidden or unknown suffix.
     */
    public function validateClassSuffix(string $className): void
    {
        $allowed   = $this->vocab['allowed_class_suffixes'] ?? ['Service'];
        $forbidden = $this->vocab['forbidden_class_suffixes'] ?? [];

        foreach ($forbidden as $suffix) {
            if (str_ends_with($className, $suffix)) {
                throw new ProtocolException(
                    "CI FAILED: class '{$className}' uses forbidden suffix '{$suffix}'"
                );
            }
        }

        foreach ($allowed as $suffix) {
            if (str_ends_with($className, $suffix)) {
                return;
            }
        }

        throw new ProtocolException(
            "CI FAILED: class '{$className}' does not end with an allowed suffix [" . implode(', ', $allowed) . "]"
        );
    }
}

class ProtocolException extends \RuntimeException {}
