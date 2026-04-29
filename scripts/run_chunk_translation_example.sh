#!/usr/bin/env bash
set -euo pipefail

# Fill these in your shell, not in this file:
# export OPENAI_API_KEY="..."
# export OPENAI_BASE_URL="http://host:port/v1"

uv run scripts/translate_html_chunks.py \
  --model gpt-5.4-mini \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --max-chars 6000 \
  --temperature 0

