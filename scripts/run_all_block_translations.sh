#!/usr/bin/env bash
set -euo pipefail

PYTHONUNBUFFERED=1 uv run scripts/translate_html_blocks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.paper.html \
  --cache outputs/cache/mmlongbench-doc.masked.translation.jsonl \
  --progress-log outputs/cache/mmlongbench-doc.block.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 5000

PYTHONUNBUFFERED=1 uv run scripts/translate_html_blocks.py \
  --input inputs/longdocurl.source.html \
  --output outputs/longdocurl.ko.paper.html \
  --cache outputs/cache/longdocurl.masked.translation.jsonl \
  --progress-log outputs/cache/longdocurl.block.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 5000

PYTHONUNBUFFERED=1 uv run scripts/translate_html_blocks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.paper.html \
  --cache outputs/cache/mmdocrag.masked.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.block.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 5000
