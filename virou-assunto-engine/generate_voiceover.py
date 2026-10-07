from __future__ import annotations

import json
from pathlib import Path
import re

import numpy as np
import soundfile as sf
from kokoro import KPipeline

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
SRC = ROOT / "src"
PUBLIC.mkdir(exist_ok=True)
SRC.mkdir(exist_ok=True)

VOICE = "pm_alex"
SPEED = 1.02
SR = 24000

TEXT = (
    "Se você ainda tinha dinheiro em uma bet, presta atenção. "
    "Desde ontem, as plataformas autorizadas estão fora do ar no Brasil. "
    "Segundo o Governo Federal, um bilhão, trezentos e vinte e cinco milhões de reais ainda aguardavam devolução "
    "a cerca de vinte e seis milhões e meio de apostadores. "
    "As empresas têm até hoje, sete de outubro, para informar os saldos aos bancos. "
    "A devolução está prevista entre nove e quatorze de outubro. "
    "Se o dinheiro não chegar, a Caixa passa a atuar a partir do dia quatorze. "
    "Salva este vídeo e manda para quem ainda tinha saldo."
)

def words(text: str) -> list[str]:
    return re.findall(r"\S+", text.strip())

def main() -> None:
    pipe = KPipeline(lang_code="p")
    pieces: list[np.ndarray] = []
    chunks: list[dict] = []
    cursor = 0.0
    gap = np.zeros(int(SR * 0.055), dtype=np.float32)

    for graphemes, _phonemes, audio in pipe(TEXT, voice=VOICE, speed=SPEED):
        wav = np.asarray(audio, dtype=np.float32).reshape(-1)
        if not wav.size:
            continue
        text = str(graphemes).strip()
        start = cursor
        duration = len(wav) / SR
        end = start + duration
        chunks.append({"text": text, "start": start, "end": end})
        pieces.extend([wav, gap])
        cursor = end + len(gap) / SR

    full = np.concatenate(pieces).astype(np.float32)
    peak = float(np.max(np.abs(full))) or 1.0
    full = 0.90 * full / peak
    sf.write(PUBLIC / "voiceover.wav", full, SR, subtype="PCM_16")

    # Approximate word timestamps inside Kokoro's natural chunks.
    word_items: list[dict] = []
    global_idx = 0
    for chunk in chunks:
        ws = words(chunk["text"])
        if not ws:
            continue
        weights = []
        for w in ws:
            clean = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", w)
            weight = max(2.0, len(clean) ** 0.82)
            if w.endswith((",", ";", ":")):
                weight += 0.8
            if w.endswith((".", "!", "?")):
                weight += 1.35
            weights.append(weight)
        total = sum(weights)
        t = chunk["start"]
        span = chunk["end"] - chunk["start"]
        for w, wt in zip(ws, weights):
            d = span * wt / total
            word_items.append({
                "word": w,
                "start": round(t, 4),
                "end": round(t + d, 4),
                "index": global_idx,
            })
            global_idx += 1
            t += d

    timing = {
        "voice": VOICE,
        "speed": SPEED,
        "sampleRate": SR,
        "duration": round(len(full) / SR, 4),
        "chunks": chunks,
        "words": word_items,
    }
    (PUBLIC / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write a generated TS module so Remotion can import timing synchronously.
    ts = "export const timing = " + json.dumps(timing, ensure_ascii=False) + " as const;\n"
    (SRC / "timing.generated.ts").write_text(ts, encoding="utf-8")

    # Minimal news bed: low pulse, restrained texture, no melody.
    total_s = max(32.0, timing["duration"] + 2.0)
    tt = np.arange(int(total_s * SR), dtype=np.float32) / SR
    bed = (
        0.020 * np.sin(2 * np.pi * 55 * tt)
        + 0.009 * np.sin(2 * np.pi * 110 * tt)
    )
    for beat in np.arange(0.0, total_s, 0.72):
        mask = (tt >= beat) & (tt < beat + 0.12)
        x = tt[mask] - beat
        bed[mask] += 0.045 * np.sin(2 * np.pi * 86 * tt[mask]) * np.exp(-24 * x)

    rng = np.random.default_rng(7)
    for hit in [2.8, 6.6, 11.0, 15.5, 20.5, 25.2]:
        mask = (tt >= hit) & (tt < hit + 0.42)
        n = int(mask.sum())
        if n:
            x = np.linspace(0, 1, n, dtype=np.float32)
            bed[mask] += 0.018 * rng.normal(0, 1, n).astype(np.float32) * np.sin(np.pi * x) ** 2

    bed = np.clip(bed, -0.35, 0.35)
    sf.write(PUBLIC / "bed.wav", bed.astype(np.float32), SR, subtype="PCM_16")

    print(json.dumps(timing, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
