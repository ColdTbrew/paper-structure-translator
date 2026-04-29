# Structure-Preserving Paper Translator

Chunked, literal Korean translation pipeline for academic paper HTML.

The pipeline is designed for papers where figures, tables, equations, citations, and section structure should remain readable while text is translated line by line. It works best with ar5iv HTML because the LaTeX-derived structure is usually cleaner than PDF text extraction.

## What It Does

- Downloads ar5iv HTML sources for configured papers.
- Builds Korean structure-reader pages with headings, figures, tables, and local image assets.
- Translates HTML text nodes in chunks with an OpenAI-compatible `chat/completions` API.
- Preserves `script`, `style`, `code`, `pre`, `math`, `svg`, links, figures, tables, and DOM structure.
- Stores translation cache as JSONL so interrupted runs can resume.

## Setup

```bash
uv venv .venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

Fill `.env` locally:

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://host:port/v1
```

Do not commit `.env`.

## Build Structure Readers

```bash
uv run scripts/build_structure_preserving_readers.py
```

This creates:

- `inputs/*.source.html`
- `outputs/*.ko.reader.html`
- `outputs/*.ko.reader.md`
- `assets/<paper>/figure-*.png`
- `outputs/translation_log.md`

Generated paper sources, images, and outputs are ignored by git.

## Run Literal Chunk Translation

Dry run first:

```bash
uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --dry-run
```

Run all configured papers:

```bash
./scripts/run_all_literal_translations.sh
```

Progress is printed immediately and also written under `outputs/cache/*.progress.log`.

## Notes

This project intentionally avoids committing full translated papers, source HTML downloads, caches, or API secrets. Use it for documents you have the right to translate and keep generated outputs local unless redistribution is permitted.
