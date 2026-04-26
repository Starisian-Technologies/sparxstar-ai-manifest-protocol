<?php

declare(strict_types=1);

namespace SPX\Artifact\Audio;

class TranscribeService
{
    public function execute(array $payload): array
    {
        return $payload;
    }
}

function spx_artifact_audio_transcribe(array $payload): array
{
    return (new TranscribeService())->execute($payload);
}
