"""Record the voice clips listed in docs/audio-script.md with OpenAI text-to-speech.

One-time tool, run on your computer (the key never goes into the app):
    OPENAI_API_KEY=... backend/.venv/bin/python scripts/make_audio.py          # missing clips only
    OPENAI_API_KEY=... backend/.venv/bin/python scripts/make_audio.py --force  # redo all
or put OPENAI_API_KEY in backend/.env. Writes frontend/public/audio/{ar,fr}/<id>.mp3.
Needs: backend/.venv/bin/pip install openai
"""
import os
import re
import sys
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "audio"
MODEL, VOICE = "gpt-4o-mini-tts", "onyx"
INSTRUCTIONS = {
    "ar": ("Speak Moroccan Darija (Moroccan Arabic), as a farmer from the Saiss region would. "
           "Calm, warm and reassuring, like a trusted local agricultural advisor talking to a farmer. "
           "Slow, clear and steady; short pause at punctuation."),
    "fr": ("Parle français avec un accent marocain léger et naturel. Calme, chaleureux et rassurant, "
           "comme un conseiller agricole qui parle à un agriculteur. Lent, clair, posé."),
}


def load_key():
    if os.environ.get("OPENAI_API_KEY"):
        return
    env = ROOT / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY (environment or backend/.env).")


def clips():
    """(id, darija, french) rows from the table in docs/audio-script.md."""
    rows = []
    for line in (ROOT / "docs" / "audio-script.md").read_text().splitlines():
        m = re.match(r"\| `([a-z0-9_]+)` \| (.*?) \| (.*?) \|", line)
        if m:
            rows.append((m.group(1), m.group(2).replace("\\|", "|"), m.group(3).replace("\\|", "|")))
    return rows


def main():
    load_key()
    force = "--force" in sys.argv
    client = OpenAI()
    done = 0
    for cid, darija, french in clips():
        for lang, text in (("ar", darija), ("fr", french)):
            path = OUT / lang / f"{cid}.mp3"
            if path.exists() and not force:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with client.audio.speech.with_streaming_response.create(
                model=MODEL, voice=VOICE, input=text, instructions=INSTRUCTIONS[lang], response_format="mp3",
            ) as response:
                response.stream_to_file(path)
            done += 1
            print(f"{lang}/{cid}.mp3")
    print(f"{done} clip(s) recorded.")


if __name__ == "__main__":
    main()
