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
- Converts PDF-only papers into image-backed source HTML with `pdf-import`.
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

Check the local environment:

```bash
./paper-translator doctor
```

Fetch source HTML with explicit CLI flags:

```bash
./paper-translator fetch \
  --paper-id mmdocrag \
  --source-url https://ar5iv.labs.arxiv.org/html/2505.16470v2
```

Agent-friendly JSON output is available on every command:

```bash
./paper-translator doctor --json
```

Run a dry run to inspect block counts before calling the model:

```bash
./paper-translator translate \
  --paper-id mmdocrag \
  --dry-run
```

Then run the translation:

```bash
./paper-translator translate --paper-id mmdocrag
```

The output files are:

```text
outputs/mmdocrag.ko.paper.html
outputs/mmdocrag.ko-en.paper.html
```

`*.ko.paper.html` is the Korean-only viewer.  
`*.ko-en.paper.html` starts with a Korean-only view. Click `원본 보기` to switch to a two-column reader with English on the left and Korean on the right.

## macOS App

This repo also includes a small SwiftUI wrapper app for local desktop use. The app is native SwiftUI for the macOS interface, while the translation engine remains the existing Python pipeline for HTML parsing, caching, and model calls.

The app runtime does not require `uv`: it runs `scripts/paper_translator.py` directly through `repo/.venv/bin/python`. If you want to prepare that environment without `uv`, run:

```bash
./scripts/bootstrap_python_env.sh
```

For drag-and-drop PDF import support, install the optional PDF dependency:

```bash
./scripts/bootstrap_python_env.sh --with-pdf
```

Build the app bundle:

```bash
./scripts/build_macos_app.sh
```

The bundle is written to:

```text
dist/Paper Translator.app
```

In the app you can:

- Drag and drop a local PDF. The app runs `pdf-import`, `translate`, then `restyle`.
- Copy an arXiv/ar5iv HTML URL, then click `클립보드 URL 번역`. The app runs `fetch`, `translate`, then `restyle`.
- Watch the CLI progress log live.
- Open the Korean-only or English/Korean parallel HTML output.

The app auto-detects this repository when launched from the repo, and you can edit the repo path in the Settings panel. Leave API key and base URL fields empty to use `.env`; fill them only when you want a temporary app-level override.

## Translate Another Paper

Pass a new ar5iv URL directly to the CLI. It will derive the default input, output, cache, and bilingual output paths from `--paper-id`.

```bash
./paper-translator translate \
  --paper-id your-paper \
  --source-url https://ar5iv.labs.arxiv.org/html/... \
  --dry-run
```

Remove `--dry-run` when the block count looks right.

## PDF-Only Papers

If a paper has no ar5iv HTML and only ships as a PDF, import the PDF into source HTML first. PDF import requires PyMuPDF.

```bash
uv add pymupdf
```

Hugging Face `/blob/...` PDF URLs are normalized to the raw `/resolve/...` PDF URL automatically.

```bash
./paper-translator pdf-import \
  --paper-id deepseek-v4 \
  --pdf-url https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf \
  --title "DeepSeek V4" \
  --json
```

This writes:

```text
inputs/pdfs/deepseek-v4.pdf
inputs/assets/deepseek-v4/page-0001.png
inputs/deepseek-v4.source.html
```

Then use the normal translation command:

```bash
./paper-translator translate --paper-id deepseek-v4 --dry-run
./paper-translator translate --paper-id deepseek-v4
```

The PDF path is less structurally rich than ar5iv HTML. It preserves original page images for figures, equations, and tables, while translated text comes from extracted PDF text blocks.

## Re-apply Viewer Style or Restore Tables

If you already have translated HTML and only want to refresh the viewer CSS or restore source tables:

```bash
./paper-translator restyle --paper-id mmdocrag
```

## Scripts

- `paper-translator`: CLI wrapper that runs `scripts/paper_translator.py` through `uv`.
- `scripts/paper_translator.py`: agent-aware CLI for `doctor`, `fetch`, `translate`, `restyle`, and `serve`.
- `scripts/translate_html_blocks.py`: masks tags, translates text blocks, restores tags, writes paper-viewer HTML.
- `scripts/apply_paper_viewer_style.py`: reapplies viewer CSS, fixes ar5iv asset links, optionally restores original table HTML.
- `scripts/bootstrap_python_env.sh`: creates `.venv` without `uv` and installs runtime Python dependencies.
- `scripts/build_macos_app.sh`: builds the SwiftUI desktop wrapper into `dist/Paper Translator.app`.

## Notes

Use this for documents you have the right to translate. Full translated paper outputs should stay local unless redistribution is permitted.
