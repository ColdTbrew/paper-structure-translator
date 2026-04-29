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
  font-family: Georgia, "Times New Roman", "Noto Serif KR", serif;
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
}
.ltx_abstract {
  margin: 0 0 42px !important;
}
.ltx_figure, .ltx_table {
  margin: 42px auto !important;
  max-width: 100%;
  overflow-x: auto;
}
.ltx_figure img, .ltx_graphics {
  display: block;
  max-width: 100% !important;
  height: auto !important;
  margin: 0 auto;
}
.ltx_caption {
  margin: 12px auto 0 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;
  text-align: left !important;
  max-width: 820px;
}
table, .ltx_tabular {
  border-collapse: collapse !important;
  margin-left: auto !important;
  margin-right: auto !important;
  font-size: 16px;
  line-height: 1.35;
}
td, th, .ltx_td, .ltx_th {
  padding: 4px 8px !important;
  vertical-align: middle;
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
    head.append(BeautifulSoup(PAPER_CSS, "lxml"))


def fix_file_viewer_links(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["img", "link", "script", "a"]):
        attr = "href" if tag.name in {"a", "link"} else "src"
        value = tag.get(attr)
        if not isinstance(value, str):
            continue
        if value.startswith("/html/") or value.startswith("/assets/"):
            tag[attr] = "https://ar5iv.labs.arxiv.org" + value


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


if __name__ == "__main__":
    main(sys.argv[1:])
