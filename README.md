# Structure-Preserving Paper Translator

[English](README.md) | [한국어](README.ko.md)

OpenAI-compatible pipeline for making clean Korean paper-viewer HTML from ar5iv HTML.

The goal is not to summarize a paper. The goal is to keep the paper readable like a normal article page while translating the body text as literally as possible.

## Preview

The generated HTML is meant to feel like a quiet paper reader: figures and tables stay in place, citations remain clickable, and the translated body text is easy to read line by line.

| Korean reader | English/Korean parallel reader |
| --- | --- |
| ![Korean paper reader](docs/korean-reader.png) | ![English and Korean parallel paper reader](docs/parallel-reader.png) |

The bilingual output includes an `원본 보기` mode with English on the left and Korean on the right. Scroll sync is enabled by default, but you can turn it off, adjust either side manually, then turn it back on without moving the current view. Future scrolls continue in sync from that state.

## Features

- Uses ar5iv HTML instead of PDF parsing.
- Masks HTML tags before calling the model, then restores the exact tags after translation.
- Sends only translatable text blocks to the model.
- Keeps `figure.ltx_table` table HTML unchanged to save tokens and avoid breaking tables.
- Preserves links, citations, figures, equations, code/pre/math blocks, and document structure.
- Adds a clean paper-viewer style: centered white page, white background, readable typography.
- Writes Korean-only HTML and bilingual English/Korean HTML.
- Provides a two-column bilingual reader with optional scroll sync.
- Writes JSONL caches so interrupted runs can resume.

## Agent Ready

This repository includes instructions for coding agents. If you are using Codex, Claude Code, or a similar agent, give it this repository URL and point it to:

- `AGENTS.md` for the full agent operating guide.
- `CLAUDE.md` for Claude Code-specific defaults.
- `skills/paper-structure-translator/SKILL.md` for reusable skill-style instructions.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill `.env` locally:

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://host:port/v1
```

`.env`, downloaded sources, caches, and generated HTML outputs are ignored by git.

## Quick Start

Run the full configured pipeline:

```bash
./scripts/run_all_block_translations.sh
```

This will:

1. Download configured ar5iv HTML files into `inputs/`.
2. Translate masked non-table text blocks.
3. Restore the original HTML tags.
4. Keep table HTML unchanged.
5. Write final paper-viewer HTML files under `outputs/`.

Current configured outputs:

```text
outputs/mmlongbench-doc.ko.paper.html
outputs/mmlongbench-doc.ko-en.paper.html
outputs/longdocurl.ko.paper.html
outputs/longdocurl.ko-en.paper.html
outputs/mmdocrag.ko.paper.html
outputs/mmdocrag.ko-en.paper.html
```

`*.ko.paper.html` is the Korean-only viewer.  
`*.ko-en.paper.html` starts with a Korean-only view. Click `원본 보기` to switch to a two-column reader with English on the left and Korean on the right.

## Run One Paper

Fetch source HTML first:

```bash
uv run scripts/fetch_sources.py
```

Dry run:

```bash
uv run scripts/translate_html_blocks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.paper.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html \
  --cache outputs/cache/mmdocrag.masked.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.masked.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --dry-run
```

Actual run:

```bash
PYTHONUNBUFFERED=1 uv run scripts/translate_html_blocks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.paper.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html \
  --cache outputs/cache/mmdocrag.masked.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.masked.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 5000
```

## Re-apply Viewer Style or Restore Tables

If you already have translated HTML and only want to refresh the viewer CSS or restore source tables:

```bash
uv run scripts/apply_paper_viewer_style.py \
  outputs/mmdocrag.ko.paper.html \
  outputs/mmdocrag.ko.paper.html \
  inputs/mmdocrag.source.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html
```

## Scripts

- `scripts/fetch_sources.py`: downloads the configured ar5iv HTML sources.
- `scripts/translate_html_blocks.py`: masks tags, translates text blocks, restores tags, writes paper-viewer HTML.
- `scripts/apply_paper_viewer_style.py`: reapplies viewer CSS, fixes ar5iv asset links, optionally restores original table HTML.
- `scripts/run_all_block_translations.sh`: runs the configured end-to-end workflow.

## Notes

Use this for documents you have the right to translate. Full translated paper outputs should stay local unless redistribution is permitted.
