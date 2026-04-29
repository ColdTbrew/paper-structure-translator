# Paper Structure Translator Skill

Use this skill when a user wants to run, modify, debug, or extend the structure-preserving paper translation pipeline in this repository.

## Trigger Phrases

- "Translate this ar5iv paper into Korean HTML"
- "Make the paper viewer"
- "Fix the bilingual reader"
- "Restore tables without retranslating"
- "Run the paper-structure-translator repo"
- "Use this repo to translate papers"

## Purpose

Generate faithful Korean paper-reader HTML from ar5iv HTML while preserving the paper's structure. The pipeline is for literal translation and readable viewing, not summarization.

## First Steps

1. Read `AGENTS.md`.
2. Read `README.md` or `README.ko.md` depending on the user's language.
3. Check repo state:

```bash
git status -sb
```

4. Set up dependencies:

```bash
uv sync
```

5. Confirm `.env` exists for real translation. It must contain:

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://host:port/v1
```

If `.env` is missing, do not invent credentials. Run `--dry-run` or ask the user for local credentials.

## Main Commands

Fetch source HTML:

```bash
uv run scripts/fetch_sources.py
```

One-paper dry run:

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

One-paper real run:

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

Style/table refresh without LLM calls:

```bash
uv run scripts/apply_paper_viewer_style.py \
  outputs/mmdocrag.ko.paper.html \
  outputs/mmdocrag.ko.paper.html \
  inputs/mmdocrag.source.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html
```

## Editing Rules

- Use `scripts/translate_html_blocks.py` for translation, masking, bilingual viewer, and CSS behavior.
- Use `scripts/apply_paper_viewer_style.py` for regenerating final viewer HTML from already translated HTML.
- Add or change configured source URLs in `scripts/fetch_sources.py`, or place an ar5iv HTML file directly under `inputs/`.
- Keep `figure.ltx_table` out of model calls.
- Preserve HTML tags with the mask/restore path.
- Keep generated HTML under `outputs/`; it is ignored by git.

## Verification

Always run:

```bash
uv run python -m py_compile scripts/*.py
```

For layout changes, verify in a browser:

```bash
python3 -m http.server 8799
```

Open:

```text
http://127.0.0.1:8799/outputs/mmlongbench-doc.ko.paper.html
http://127.0.0.1:8799/outputs/mmlongbench-doc.ko-en.paper.html
```

Check:

- The Korean-only reader is readable.
- `원본 보기` shows English left and Korean right.
- Scroll sync off/on works.
- Turning scroll sync on does not jump the current view.
- Tables have borders and do not overlap text.
- Figures render.

## Before Committing

Check for secrets:

```bash
rg -n -e 'sk-[A-Za-z0-9]' -e 'OPENAI_API_KEY=.*sk-[A-Za-z0-9]' README.md README.ko.md AGENTS.md CLAUDE.md skills scripts .env.example pyproject.toml uv.lock || true
```

Do not commit:

- `.env`
- `.venv/`
- `inputs/`
- `outputs/`
- `outputs/cache/`
- full translated paper outputs unless the user explicitly requests it and redistribution is permitted

README preview screenshots under `docs/*.png` may be committed.

## Reporting Back

Report:

- Which outputs were generated or refreshed.
- Whether API calls were made.
- Which browser checks passed.
- Any missing credentials or skipped verification.
