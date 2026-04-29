#!/usr/bin/env bash
set -euo pipefail

PYTHONUNBUFFERED=1 uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --progress-log outputs/cache/mmlongbench-doc.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0

PYTHONUNBUFFERED=1 uv run scripts/translate_html_chunks.py \
  --input inputs/longdocurl.source.html \
  --output outputs/longdocurl.ko.literal.html \
  --cache outputs/cache/longdocurl.translation.jsonl \
  --progress-log outputs/cache/longdocurl.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0

PYTHONUNBUFFERED=1 uv run scripts/translate_html_chunks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.literal.html \
  --cache outputs/cache/mmdocrag.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0
