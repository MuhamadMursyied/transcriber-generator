#!/usr/bin/env bash
# Optional: convert a Malaysian Whisper model from mesolitica yourself instead
# of using the ready-made "Malaysian Turbo" download.
#
# The result goes to models/<name>/ and shows up in the app's model list as
# "<name> (local)". Needs ~6 GB of free disk for the one-off conversion tools.
#
#   ./scripts/convert_malaysian.sh                                   # turbo (default)
#   ./scripts/convert_malaysian.sh mesolitica/malaysian-whisper-small-v3 malaysian-small
set -e
cd "$(dirname "$0")/.."

REPO=${1:-mesolitica/Malaysian-whisper-large-v3-turbo-v3}
NAME=${2:-malaysian-turbo-local}

# Conversion needs PyTorch and transformers. Keep them in their own venv so the
# app itself stays small.
if [ ! -d .venv-convert ]; then
  python3 -m venv .venv-convert
  .venv-convert/bin/pip install -q --upgrade pip
  .venv-convert/bin/pip install -q ctranslate2 "transformers[torch]" --extra-index-url https://download.pytorch.org/whl/cpu
fi

mkdir -p models
.venv-convert/bin/ct2-transformers-converter \
  --model "$REPO" \
  --output_dir "models/$NAME" \
  --copy_files tokenizer.json preprocessor_config.json \
  --quantization float16 \
  --force

echo "Done. Restart the app and pick '$NAME (local)' in the model list."
