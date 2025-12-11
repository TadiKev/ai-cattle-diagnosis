#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${1:-https://github.com/TadiKev/ai-cattle-diagnosis/releases/download/v1.0.0}"
TARGET_DIR="ml-inference/models"
mkdir -p "$TARGET_DIR"

assets=("best_model_state_dict.pth" "class_map.json")

for a in "${assets[@]}"; do
  out="$TARGET_DIR/$a"
  if [ -f "$out" ]; then
    echo "Skipping existing $a (remove it or pass a different BASE_URL to overwrite)"
    continue
  fi
  url="$BASE_URL/$a"
  echo "Downloading $a from $url ..."
  curl -L -o "$out" "$url" || { echo "Download failed: $url"; exit 1; }
  echo "Saved -> $out"
done
echo "Done. Models in $TARGET_DIR"
