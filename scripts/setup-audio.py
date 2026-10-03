"""Explicit setup download. Importing student audio never downloads a model."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--download", action="store_true", help="Download multilingual faster-whisper Tiny")
args = parser.parse_args()
if not args.download:
    parser.error("Pass --download to fetch the local speech model.")
from huggingface_hub import snapshot_download
destination = Path(__file__).resolve().parents[1] / "models/faster-whisper-tiny"
snapshot_download("Systran/faster-whisper-tiny", local_dir=destination,
                  revision="d90ca5fe260221311c53c58e660288d3deb8d356",
                  allow_patterns=["model.bin", "config.json", "tokenizer.json", "vocabulary.txt", "vocabulary.json"])
print("Local audio model ready:", destination)
