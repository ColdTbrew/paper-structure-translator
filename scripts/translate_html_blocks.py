from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag


TRANSLATE_SELECTORS = [
    "h1.ltx_title_document",
    "h2.ltx_title_section",
    "h3.ltx_title_subsection",
    "h4.ltx_title_subsubsection",
    "h5.ltx_title_paragraph",
    "h6.ltx_title_abstract",
    "p.ltx_p",
    "figcaption.ltx_caption",
]

SKIP_TAGS = {"script", "style", "pre", "code", "math", "svg"}

SYSTEM_PROMPT = """You are a professional academic paper translator.
Translate English academic paper text into Korean as literally and faithfully as possible.
The input uses placeholder tokens such as ⟦H0001⟧ instead of HTML tags. Preserve every placeholder token exactly and in the same order.
Preserve math, citations, links, figure/table numbers, model names, dataset names, metric names, URLs, filenames, and code-like strings.
Do not summarize. Do not omit details. Do not add explanations.
Return only valid JSON."""

USER_PROMPT = """Translate each masked text fragment from English to Korean.

Rules:
- Literal translation is more important than fluency.
- Preserve every placeholder token like ⟦H0001⟧ exactly and in the same order.
- Do not translate dataset/model/metric names such as MMLongBench-Doc, LongDocURL, MMDocRAG, GPT-4o, Recall@K, F1, BLEU, ROUGE-L.
- Do not translate citations, URLs, math, numbers, or code-like strings.
- Output exactly:
{{"translations":[{{"id":"b0","text":"..."}}, ...]}}

Fragments:
{items_json}
"""


PAPER_CSS = """
<style id="codex-paper-viewer-style">
html { background: #fff; }
body {
  margin: 0;
  background: #fff;
  color: #252525;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Helvetica Neue", Arial, sans-serif;
  font-size: 19px;
  line-height: 1.48;
}
.ltx_page_main, .ltx_page_content {
  margin: 0 auto !important;
  padding: 0 !important;
  background: transparent !important;
}
.ltx_document {
  box-sizing: border-box;
  max-width: 900px !important;
  margin: 0 auto !important;
  padding: 54px 46px 96px !important;
  background: #fff;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Helvetica Neue", Arial, sans-serif !important;
}
.ltx_title_document {
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  font-size: 30px !important;
  line-height: 1.25 !important;
  font-weight: 600 !important;
  margin: 0 auto 32px !important;
  max-width: 760px;
}
.ltx_authors {
  text-align: center;
  font-size: 16px;
  line-height: 1.45;
  margin-bottom: 58px;
}
.ltx_title_abstract, .ltx_title_section, .ltx_title_subsection {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  font-weight: 700 !important;
  letter-spacing: 0;
}
.ltx_title_abstract { font-size: 24px !important; margin: 0 0 18px !important; }
.ltx_title_section { font-size: 27px !important; margin: 54px 0 18px !important; }
.ltx_title_subsection { font-size: 22px !important; margin: 34px 0 12px !important; }
.ltx_p {
  margin: 0 0 1.05em !important;
  text-align: justify;
  word-break: keep-all;
  overflow-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Helvetica Neue", Arial, sans-serif !important;
}
.ltx_abstract {
  margin: 0 0 42px !important;
}
.ltx_figure, .ltx_table {
  margin: 42px auto !important;
  max-width: 100%;
  overflow: visible;
  clear: both;
  display: block;
}
.ltx_table {
  display: flow-root !important;
  width: 100% !important;
  text-align: center !important;
  page-break-inside: avoid;
  break-inside: avoid;
}
.ltx_table .ltx_transformed_outer {
  display: block !important;
  width: 100% !important;
  height: auto !important;
  margin-left: auto !important;
  margin-right: auto !important;
  text-align: center !important;
  vertical-align: baseline !important;
}
.ltx_table .ltx_transformed_inner {
  display: block !important;
  width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  transform: none !important;
}
.ltx_figure:has(.ltx_transformed_outer table),
.ltx_figure_panel:has(.ltx_transformed_outer table),
.ltx_minipage:has(.ltx_transformed_outer table) {
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  text-align: center !important;
}
.ltx_transformed_outer:has(table) {
  display: block !important;
  width: 100% !important;
  height: auto !important;
  margin-left: auto !important;
  margin-right: auto !important;
  text-align: center !important;
  vertical-align: baseline !important;
}
.ltx_transformed_outer:has(table) > .ltx_transformed_inner {
  display: block !important;
  width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  transform: none !important;
}
.ltx_figure img, .ltx_graphics {
  display: block;
  max-width: 100% !important;
  height: auto !important;
  margin: 0 auto;
}
.ltx_picture {
  display: block !important;
  max-width: 100% !important;
  height: auto !important;
  margin: 24px auto !important;
  overflow: hidden !important;
}
svg.ltx_picture {
  font-family: Arial, sans-serif !important;
  font-size: 6px !important;
  line-height: 1.08 !important;
}
svg.ltx_picture .ltx_p {
  display: block;
  margin: 0 0 2px !important;
  text-align: left !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  font-family: inherit !important;
  font-size: inherit !important;
  line-height: inherit !important;
}
svg.ltx_picture .ltx_text,
svg.ltx_picture .ltx_inline-block {
  font-family: inherit !important;
  font-size: inherit !important;
  line-height: inherit !important;
}
svg.ltx_picture .ltx_inline-block {
  max-width: 100%;
}
.ltx_caption {
  margin: 12px auto 0 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;
  text-align: left !important;
  max-width: 820px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Helvetica Neue", Arial, sans-serif !important;
}
table, .ltx_tabular {
  border-collapse: collapse !important;
  margin: 0 auto !important;
  width: 100% !important;
  max-width: 100% !important;
  table-layout: fixed !important;
  font-size: clamp(7px, 0.82vw, 11px) !important;
  line-height: 1.12 !important;
  border-top: 1.5px solid #333 !important;
  border-bottom: 1.5px solid #333 !important;
}
td, th, .ltx_td, .ltx_th {
  padding: 2px 3px !important;
  vertical-align: middle;
  border: 1px solid #8e8e8e !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
  word-break: normal;
}
.ltx_table + *,
.ltx_figure + * {
  clear: both;
  margin-top: 24px !important;
}
thead td, thead th, .ltx_tr:first-child > .ltx_td, .ltx_tr:first-child > .ltx_th {
  border-bottom: 1.5px solid #333 !important;
}
.ltx_tabular .ltx_border_t,
.ltx_tabular .ltx_border_b,
.ltx_tabular .ltx_border_l,
.ltx_tabular .ltx_border_r {
  border-color: #333 !important;
}
.ltx_page_footer, .ltx_page_header, .ltx_page_logo {
  display: none !important;
}
a { color: #174ea6; text-decoration-thickness: 1px; text-underline-offset: 2px; }
@media (max-width: 760px) {
  body { font-size: 17px; }
  .ltx_document { padding: 32px 18px 72px !important; }
  .ltx_title_document { font-size: 25px !important; }
}
</style>
"""


BILINGUAL_CSS = """
<style id="codex-bilingual-viewer-style">
body.has_bilingual_view .codex_tabs {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.96);
  border-bottom: 1px solid #e5e5e5;
}
body.has_bilingual_view .codex_tab_button {
  appearance: none;
  border: 1px solid #cfcfcf;
  background: #fff;
  color: #222;
  border-radius: 6px;
  padding: 7px 14px;
  font: 600 14px -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  cursor: pointer;
}
body.has_bilingual_view .codex_tab_button[aria-selected="true"] {
  border-color: #222;
  background: #222;
  color: #fff;
}
body.has_bilingual_view .codex_sync_button {
  appearance: none;
  border: 1px solid #cfcfcf;
  background: #fff;
  color: #222;
  border-radius: 6px;
  padding: 7px 12px;
  font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  cursor: pointer;
}
body.has_bilingual_view .codex_sync_button.is_off {
  color: #666;
}
body.has_bilingual_view .codex_sync_button[hidden] {
  display: none !important;
}
body.has_bilingual_view .codex_panel[hidden] {
  display: none !important;
}
body.has_bilingual_view .codex_parallel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0;
  background: #fff;
  height: calc(100vh - 57px);
  overflow: hidden;
}
body.has_bilingual_view .codex_parallel_column {
  min-width: 0;
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-left: 1px solid #eee;
}
body.has_bilingual_view .codex_parallel_column:first-child {
  border-left: 0;
}
body.has_bilingual_view .codex_parallel_label {
  position: sticky;
  top: 54px;
  z-index: 10;
  padding: 6px 12px;
  background: rgba(255,255,255,0.96);
  border-bottom: 1px solid #e7e7e7;
  font: 600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  color: #555;
  text-align: center;
}
body.has_bilingual_view .codex_parallel .ltx_document {
  max-width: 760px !important;
  padding-left: 34px !important;
  padding-right: 34px !important;
}
@media (max-width: 1100px) {
  body.has_bilingual_view .codex_parallel {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }
  body.has_bilingual_view .codex_parallel_column {
    height: auto;
    overflow: visible;
    border-left: 0;
    border-top: 1px solid #eee;
  }
  body.has_bilingual_view .codex_parallel_column:first-child {
    border-top: 0;
  }
}
</style>
"""


BILINGUAL_SCRIPT = """
<script id="codex-bilingual-viewer-script">
document.addEventListener("DOMContentLoaded", function () {
  const buttons = Array.from(document.querySelectorAll(".codex_tab_button"));
  const panels = Array.from(document.querySelectorAll(".codex_panel"));
  const syncButton = document.querySelector(".codex_sync_button");
  const columns = Array.from(document.querySelectorAll(".codex_parallel_column"));
  let syncEnabled = true;
  let isSyncing = false;
  const scrollPositions = new Map();
  function captureScrollPositions() {
    columns.forEach((column) => {
      scrollPositions.set(column, column.scrollTop);
    });
  }
  function clampScrollTop(element, value) {
    const max = element.scrollHeight - element.clientHeight;
    return Math.max(0, Math.min(max, value));
  }
  function syncFrom(source) {
    if (!source || !syncEnabled || isSyncing || columns.length < 2) return;
    const previousTop = scrollPositions.get(source) ?? source.scrollTop;
    const delta = source.scrollTop - previousTop;
    if (!delta) {
      captureScrollPositions();
      return;
    }
    isSyncing = true;
    columns.forEach((column) => {
      if (column !== source) {
        column.scrollTop = clampScrollTop(column, column.scrollTop + delta);
      }
    });
    window.setTimeout(() => {
      captureScrollPositions();
      isSyncing = false;
    }, 0);
  }
  function setSyncEnabled(enabled) {
    syncEnabled = enabled;
    if (!syncButton) return;
    syncButton.textContent = enabled ? "스크롤 동기화 끄기" : "스크롤 동기화 켜기";
    syncButton.classList.toggle("is_off", !enabled);
    syncButton.setAttribute("aria-pressed", enabled ? "true" : "false");
    captureScrollPositions();
  }
  function activate(target) {
    buttons.forEach((button) => {
      const selected = button.dataset.target === target;
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    panels.forEach((panel) => {
      panel.hidden = panel.id !== target;
    });
    if (syncButton) {
      syncButton.hidden = target !== "codex-panel-parallel";
    }
    if (target === "codex-panel-parallel") {
      window.scrollTo(0, 0);
      window.setTimeout(captureScrollPositions, 0);
    }
  }
  buttons.forEach((button) => {
    button.addEventListener("click", () => activate(button.dataset.target));
  });
  columns.forEach((column) => {
    column.addEventListener("scroll", () => {
      if (isSyncing) return;
      syncFrom(column);
    }, { passive: true });
  });
  if (syncButton) {
    syncButton.addEventListener("click", () => setSyncEnabled(!syncEnabled));
    setSyncEnabled(true);
  }
  activate("codex-panel-ko");
});
</script>
"""


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def block_hash(fragment: str) -> str:
    return hashlib.sha256(fragment.encode("utf-8")).hexdigest()


def load_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.exists():
        return cache
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "ko_masked" in obj:
            cache.setdefault(obj["hash"], obj["ko_masked"])
    return cache


def append_cache(path: Path, source_masked: str, ko_masked: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"hash": block_hash(source_masked), "source_masked": source_masked, "ko_masked": ko_masked},
                ensure_ascii=False,
            )
            + "\n"
        )


def should_translate_tag(tag: Tag) -> bool:
    if any(parent.name in SKIP_TAGS for parent in tag.parents if isinstance(parent, Tag)):
        return False
    if "ltx_table" in (tag.get("class") or []) or tag.find_parent("figure", class_="ltx_table"):
        return False
    text = tag.get_text(" ", strip=True)
    if len(text) < 2:
        return False
    if re.fullmatch(r"[\W\d_]+", text):
        return False
    return True


def collect_blocks(soup: BeautifulSoup) -> list[Tag]:
    blocks: list[Tag] = []
    seen: set[int] = set()
    for selector in TRANSLATE_SELECTORS:
        for tag in soup.select(selector):
            if id(tag) in seen or not should_translate_tag(tag):
                continue
            seen.add(id(tag))
            blocks.append(tag)
    blocks.sort(key=lambda t: getattr(t, "sourceline", 0) or 0)
    return blocks


TAG_PATTERN = re.compile(r"<[^>]+>")
PLACEHOLDER_PATTERN = re.compile(r"⟦H\d{4}⟧")


def mask_html(fragment: str) -> tuple[str, list[str]]:
    tags: list[str] = []

    def repl(match: re.Match[str]) -> str:
        tags.append(match.group(0))
        return f"⟦H{len(tags) - 1:04d}⟧"

    return TAG_PATTERN.sub(repl, fragment), tags


def unmask_html(masked: str, tags: list[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        idx = int(match.group(0)[2:6])
        return tags[idx] if idx < len(tags) else match.group(0)

    return PLACEHOLDER_PATTERN.sub(repl, masked)


def make_batches(items: list[tuple[str, str]], max_chars: int) -> list[list[tuple[str, str]]]:
    batches: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    chars = 0
    for item in items:
        size = len(item[1])
        if current and chars + size > max_chars:
            batches.append(current)
            current = []
            chars = 0
        current.append(item)
        chars += size
    if current:
        batches.append(current)
    return batches


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def call_api(base_url: str, api_key: str, model: str, batch: list[tuple[str, str]], timeout: int, retries: int) -> dict[str, str]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    items_json=json.dumps([{"id": bid, "text": text} for bid, text in batch], ensure_ascii=False)
                ),
            },
        ],
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = extract_json(content)
            return {str(item["id"]): str(item["text"]) for item in parsed["translations"]}
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"request failed: {last}") from last


def log_factory(path: Path | None):
    def log(message: str) -> None:
        stamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(stamped, flush=True)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(stamped + "\n")

    return log


def inject_style(soup: BeautifulSoup) -> None:
    existing = soup.find(id="codex-paper-viewer-style")
    if existing:
        existing.decompose()
    head = soup.head or soup.new_tag("head")
    if not soup.head:
        soup.html.insert(0, head)
    style_tag = BeautifulSoup(PAPER_CSS, "lxml").find("style")
    if style_tag:
        head.append(style_tag)


def inject_bilingual_assets(soup: BeautifulSoup) -> None:
    for element_id in ("codex-bilingual-viewer-style", "codex-bilingual-viewer-script"):
        existing = soup.find(id=element_id)
        if existing:
            existing.decompose()
    head = soup.head or soup.new_tag("head")
    if not soup.head:
        soup.html.insert(0, head)
    body = soup.body or soup.new_tag("body")
    if not soup.body:
        soup.html.append(body)
    style_tag = BeautifulSoup(BILINGUAL_CSS, "lxml").find("style")
    script_tag = BeautifulSoup(BILINGUAL_SCRIPT, "lxml").find("script")
    if style_tag:
        head.append(style_tag)
    if script_tag:
        body.append(script_tag)


def fix_file_viewer_links(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["img", "link", "script", "a"]):
        attr = "href" if tag.name in {"a", "link"} else "src"
        value = tag.get(attr)
        if not isinstance(value, str):
            continue
        if value.startswith("/html/") or value.startswith("/assets/"):
            tag[attr] = "https://ar5iv.labs.arxiv.org" + value


def build_bilingual_view(ko_soup: BeautifulSoup, source_soup: BeautifulSoup) -> BeautifulSoup:
    source_copy = BeautifulSoup(str(source_soup), "lxml")
    inject_style(ko_soup)
    inject_style(source_copy)
    fix_file_viewer_links(ko_soup)
    fix_file_viewer_links(source_copy)

    ko_article = ko_soup.select_one("article.ltx_document")
    en_article = source_copy.select_one("article.ltx_document")
    if not ko_article or not en_article:
        raise RuntimeError("Could not find article.ltx_document in source or translated HTML")

    out = BeautifulSoup("<!doctype html><html lang=\"ko\"><head></head><body class=\"has_bilingual_view\"></body></html>", "lxml")
    meta_charset = out.new_tag("meta", charset="utf-8")
    meta_viewport = out.new_tag("meta")
    meta_viewport["name"] = "viewport"
    meta_viewport["content"] = "width=device-width, initial-scale=1"
    out.head.append(meta_charset)
    out.head.append(meta_viewport)
    title = ko_soup.find("title")
    if title:
        out.head.append(BeautifulSoup(str(title), "lxml").find("title"))
    for style in ko_soup.find_all("style", id=["codex-paper-viewer-style"]):
        out.head.append(BeautifulSoup(str(style), "lxml").find("style"))
    inject_bilingual_assets(out)

    nav = out.new_tag("nav")
    nav["class"] = "codex_tabs"
    nav["aria-label"] = "paper language tabs"
    for label, target, selected in (("한국어", "codex-panel-ko", "true"), ("원본 보기", "codex-panel-parallel", "false")):
        button = out.new_tag("button")
        button["class"] = "codex_tab_button"
        button["data-target"] = target
        button["aria-selected"] = selected
        button.string = label
        nav.append(button)
    sync_button = out.new_tag("button")
    sync_button["class"] = "codex_sync_button"
    sync_button["type"] = "button"
    sync_button["aria-pressed"] = "true"
    sync_button["hidden"] = ""
    sync_button.string = "스크롤 동기화 끄기"
    nav.append(sync_button)

    main = out.new_tag("main")
    ko_panel = out.new_tag("section", id="codex-panel-ko")
    ko_panel["class"] = "codex_panel"
    parallel_panel = out.new_tag("section", id="codex-panel-parallel")
    parallel_panel["class"] = "codex_panel"
    parallel_panel["hidden"] = ""
    parallel = out.new_tag("div")
    parallel["class"] = "codex_parallel"
    en_col = out.new_tag("div")
    en_col["class"] = "codex_parallel_column"
    ko_col = out.new_tag("div")
    ko_col["class"] = "codex_parallel_column"
    en_label = out.new_tag("div")
    en_label["class"] = "codex_parallel_label"
    en_label.string = "English original"
    ko_label = out.new_tag("div")
    ko_label["class"] = "codex_parallel_label"
    ko_label.string = "Korean translation"
    ko_panel.append(BeautifulSoup(str(ko_article), "lxml").find("article"))
    en_col.append(en_label)
    en_col.append(BeautifulSoup(str(en_article), "lxml").find("article"))
    ko_col.append(ko_label)
    ko_col.append(BeautifulSoup(str(ko_article), "lxml").find("article"))
    parallel.append(en_col)
    parallel.append(ko_col)
    parallel_panel.append(parallel)
    main.append(ko_panel)
    main.append(parallel_panel)
    out.body.insert(0, nav)
    out.body.insert(1, main)
    return out


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Translate ar5iv HTML by block while preserving paper layout.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--max-chars", type=int, default=5000)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--progress-log", default="")
    parser.add_argument("--bilingual-output", default="", help="Optional HTML output with Korean and English tabs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    load_env_file(Path(args.env_file))
    log = log_factory(Path(args.progress_log) if args.progress_log else None)

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    cache_path = Path(args.cache).resolve()
    soup = BeautifulSoup(input_path.read_text(encoding="utf-8"), "lxml")
    blocks = collect_blocks(soup)
    cache = load_cache(cache_path)

    todo: list[tuple[str, str]] = []
    translations: dict[str, str] = {}
    id_to_tag: dict[str, Tag] = {}
    id_to_tags: dict[str, list[str]] = {}
    for idx, tag in enumerate(blocks):
        bid = f"b{idx}"
        source_html = str(tag)
        source_masked, html_tags = mask_html(source_html)
        id_to_tag[bid] = tag
        id_to_tags[bid] = html_tags
        cached = cache.get(block_hash(source_masked))
        if cached is not None:
            translations[bid] = cached
        else:
            todo.append((bid, source_masked))

    log(f"input={input_path}")
    log(f"output={output_path}")
    log(f"blocks={len(blocks)} cached={len(translations)} todo={len(todo)}")
    if args.dry_run:
        log(f"dry_run=true chars_to_translate={sum(len(x[1]) for x in todo)}")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key or not base_url:
        raise SystemExit("OPENAI_API_KEY and OPENAI_BASE_URL are required")

    batches = make_batches(todo, args.max_chars)
    for batch_no, batch in enumerate(batches, 1):
        log(f"translating batch {batch_no}/{len(batches)} blocks={len(batch)} chars={sum(len(x[1]) for x in batch)}")
        result = call_api(base_url, api_key, args.model, batch, args.timeout, args.max_retries)
        missing = [bid for bid, _ in batch if bid not in result]
        if missing:
            log(f"batch {batch_no} missing={len(missing)}; retrying one by one")
            for bid, html_fragment in batch:
                if bid in result:
                    continue
                single = call_api(base_url, api_key, args.model, [(bid, html_fragment)], args.timeout, args.max_retries)
                result.update(single)
        for bid, source_masked in batch:
            ko_masked = result[bid]
            translations[bid] = ko_masked
            append_cache(cache_path, source_masked, ko_masked)
        log(f"completed batch {batch_no}/{len(batches)} translated={len(translations)}/{len(blocks)}")

    for bid, tag in id_to_tag.items():
        ko_masked = translations.get(bid)
        if not ko_masked:
            continue
        ko_html = unmask_html(ko_masked, id_to_tags[bid])
        parsed = BeautifulSoup(ko_html, "lxml")
        replacement = parsed.find(tag.name)
        if replacement:
            tag.replace_with(replacement)

    inject_style(soup)
    fix_file_viewer_links(soup)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")
    log(f"wrote {output_path}")

    if args.bilingual_output:
        source_soup = BeautifulSoup(input_path.read_text(encoding="utf-8"), "lxml")
        bilingual = build_bilingual_view(BeautifulSoup(str(soup), "lxml"), source_soup)
        bilingual_path = Path(args.bilingual_output).resolve()
        bilingual_path.parent.mkdir(parents=True, exist_ok=True)
        bilingual_path.write_text(str(bilingual), encoding="utf-8")
        log(f"wrote {bilingual_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
