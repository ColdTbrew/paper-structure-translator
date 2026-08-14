# Claude Code Instructions

Use `AGENTS.md` as the source of truth for this repository.

## What This Repo Does

This project converts ar5iv HTML into faithful Korean paper-reader HTML while preserving the original paper structure. It is a translation and viewer-generation pipeline, not a summarizer.

## Default Claude Workflow

1. Read `AGENTS.md`, `README.md`, and `README.ko.md`.
2. Use `uv sync` for setup.
3. Require a local `.env` with `OPENAI_API_KEY` and `OPENAI_BASE_URL` for real translation runs.
4. Use `./kpaper fetch`, then `./kpaper translate` for the target paper.
5. Use `./kpaper restyle` for CSS/table/viewer-only fixes without calling the model.
6. Verify generated HTML in a browser before reporting success.

## Non-Negotiables

- Do not commit `.env`, `inputs/`, `outputs/`, `.venv/`, or cache files.
- Do not send `figure.ltx_table` HTML to the model; tables are copied/restored from the source HTML.
- Preserve citations, links, figures, equations, and document structure.
- Keep Korean translation literal and line-by-line readable.
- If secrets are missing, stop before real API calls and ask the user to provide local `.env` values.

## Quick Commands

```bash
uv sync
uv run python -m py_compile scripts/*.py
./kpaper doctor --json
```

Style-only refresh:

```bash
./kpaper restyle --paper-id mmdocrag
```
