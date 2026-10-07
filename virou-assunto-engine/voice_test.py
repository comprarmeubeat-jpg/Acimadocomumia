from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

OUT = Path("voice_test_output")
OUT.mkdir(parents=True, exist_ok=True)

TEXT = (
    "Se você tinha dinheiro em uma plataforma de apostas, atenção. "
    "As regras mudaram e milhões de brasileiros acompanham agora o processo de devolução dos saldos. "
    "Segundo informações oficiais, mais de um bilhão de reais ainda aguardava pagamento. "
    "O Virou Assunto explica o que muda, quais são os prazos e o que você precisa observar a partir de agora. "
    "Informação rápida, contexto e fonte na tela, sem enrolação."
)

VOICES = {
    "pm_alex": {"label": "Alex", "gender": "male"},
    "pm_santa": {"label": "Santa", "gender": "male"},
    "pf_dora": {"label": "Dora", "gender": "female"},
}


def synthesize(pipe: KPipeline, voice: str, speed: float = 1.03) -> np.ndarray:
    chunks: list[np.ndarray] = []
    silence = np.zeros(int(24000 * 0.08), dtype=np.float32)

    for _graphemes, _phonemes, audio in pipe(TEXT, voice=voice, speed=speed):
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        if arr.size:
            chunks.append(arr)
            chunks.append(silence)

    if not chunks:
        raise RuntimeError(f"No audio produced for {voice}")

    wav = np.concatenate(chunks)
    peak = float(np.max(np.abs(wav))) or 1.0
    wav = 0.92 * wav / peak
    return wav.astype(np.float32)


def metrics(wav: np.ndarray, sr: int = 24000) -> dict:
    rms = float(np.sqrt(np.mean(np.square(wav))))
    peak = float(np.max(np.abs(wav)))
    duration = float(len(wav) / sr)
    clip_ratio = float(np.mean(np.abs(wav) >= 0.999))
    return {
        "duration_seconds": round(duration, 3),
        "peak": round(peak, 5),
        "rms": round(rms, 5),
        "clip_ratio": round(clip_ratio, 8),
    }


def main() -> None:
    pipe = KPipeline(lang_code="p")
    report = {"text": TEXT, "sample_rate": 24000, "voices": {}}

    for voice, meta in VOICES.items():
        print(f"Generating {voice}...")
        wav = synthesize(pipe, voice)
        wav_path = OUT / f"{voice}.wav"
        sf.write(wav_path, wav, 24000, subtype="PCM_16")
        report["voices"][voice] = {**meta, **metrics(wav), "file": wav_path.name}

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
