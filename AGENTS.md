# Agent Guide

This repository builds structure-preserving Korean paper-reader HTML from ar5iv HTML.

If a user gives you only this repository URL, use this file as the operating guide. The short version:

1. Set up with `uv sync`.
2. Ask the user for `OPENAI_API_KEY` and `OPENAI_BASE_URL` if `.env` is not already present.
3. Use `./paper-translator` for `doctor`, `fetch`, `translate`, `restyle`, and `serve`.
4. Verify generated HTML in a real browser.
5. Never commit `.env`, `inputs/`, `outputs/`, or cache files unless the user explicitly changes the repo policy.

## Project Goal

The output is not a summary. It is a faithful Korean translation in a clean paper-reader layout.

The pipeline should:

- Use ar5iv HTML as the source, not PDF/OCR.
- Preserve document structure, links, citations, figures, equations, and code/pre/math blocks.
- Translate normal text blocks as literally as possible.
- Keep `figure.ltx_table` HTML unchanged and restore tables from source HTML.
- Produce both:
  - `*.ko.paper.html`: Korean-only paper reader.
  - `*.ko-en.paper.html`: Korean view plus `원본 보기`, a two-column English/Korean reader.

## Important Files

- `README.md`: English user documentation.
- `README.ko.md`: Korean user documentation.
- `paper-translator`: primary CLI wrapper; it runs `scripts/paper_translator.py` through `uv`.
- `scripts/paper_translator.py`: agent-aware CLI with `--json` and `--dry-run` support.
- `scripts/translate_html_blocks.py`: masks HTML tags, translates text blocks, restores tags, and writes viewer HTML.
- `scripts/apply_paper_viewer_style.py`: reapplies viewer CSS and restores source tables without calling the model.
- `skills/paper-structure-translator/SKILL.md`: reusable skill instructions for agents.

## Setup

Use `uv`; do not replace the project with another package manager.

```bash
uv sync
cp .env.example .env
```

The `.env` file must contain:

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://host:port/v1
```

Do not invent or commit secrets. If credentials are missing, run only non-network verification or `--dry-run`, then ask the user for the missing values.

## CLI Workflow

Check readiness:

```bash
./paper-translator doctor --json
```

Fetch source HTML with explicit flags:

```bash
./paper-translator fetch \
  --paper-id mmdocrag \
  --source-url https://ar5iv.labs.arxiv.org/html/2505.16470v2 \
  --json
```

Dry run before calling the model:

```bash
./paper-translator translate \
  --paper-id mmdocrag \
  --json \
  --dry-run
```

Actual run:

```bash
./paper-translator translate --paper-id mmdocrag
```

## Style-Only Refresh

If translated HTML already exists and the user only wants CSS/viewer/table fixes, do not call the LLM. Reapply style and restore tables:

```bash
./paper-translator restyle --paper-id mmdocrag
```

## Verification Checklist

Run:

```bash
uv run python -m py_compile scripts/*.py
```

For browser verification:

```bash
./paper-translator serve --port 8799
```

Then open generated files, for example:

```text
http://127.0.0.1:8799/outputs/mmlongbench-doc.ko.paper.html
http://127.0.0.1:8799/outputs/mmlongbench-doc.ko-en.paper.html
```

Check:

- Korean-only page loads.
- Bilingual page opens in Korean view.
- `원본 보기` switches to a two-column reader.
- Scroll sync can be turned off and on.
- Turning sync on does not move the current view; future scrolls sync from the current state.
- Tables have visible borders and do not overlap following text.
- Figures load through fixed ar5iv asset links.

## Git and Safety Rules

- Keep `.env`, `inputs/`, `outputs/`, `.venv/`, and caches untracked.
- `docs/*.png` screenshots are allowed to be tracked for README previews.
- Before committing, check for secrets:

```bash
rg -n -e 'sk-[A-Za-z0-9]' -e 'OPENAI_API_KEY=.*sk-[A-Za-z0-9]' README.md README.ko.md AGENTS.md CLAUDE.md skills scripts paper-translator .env.example pyproject.toml uv.lock || true
```

- Do not include full translated paper outputs in git unless the user explicitly asks and redistribution is permitted.
- Keep changes scoped. If the user asks for a viewer/layout fix, prefer `./paper-translator restyle` or CSS changes over rerunning translation.
