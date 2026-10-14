#!/usr/bin/env bash
# One-command start: creates a virtual environment on first run, installs the
# requirements, enables the NVIDIA GPU when there is one, then starts the app.
#   ./run.sh                  open http://127.0.0.1:7860
#   ./run.sh --host 0.0.0.0   reach it from other devices on your network
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "First run: creating .venv and installing packages..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
  # Desktop/laptop NVIDIA GPU: add the CUDA 12 libraries faster-whisper needs.
  if command -v nvidia-smi >/dev/null 2>&1 && [ "$(uname -m)" = "x86_64" ]; then
    .venv/bin/pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
  fi
fi

# Make the pip-installed CUDA libraries visible, if present.
CUDA_LIBS=$(.venv/bin/python - <<'EOF' 2>/dev/null || true
import os
import nvidia.cublas.lib, nvidia.cudnn.lib
print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))
EOF
)
if [ -n "$CUDA_LIBS" ]; then
  export LD_LIBRARY_PATH="$CUDA_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec .venv/bin/python app.py "$@"
