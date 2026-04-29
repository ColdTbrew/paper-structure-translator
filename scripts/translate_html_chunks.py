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
from bs4 import BeautifulSoup, NavigableString, Tag


SKIP_TAGS = {
    "script",
    "style",
    "code",
    "pre",
    "math",
    "annotation",
    "semantics",
    "svg",
    "noscript",
}


SYSTEM_PROMPT = """You are a professional academic paper translator.
Translate English academic paper text into Korean as literally and faithfully as possible.
Preserve technical terms, dataset names, benchmark names, model names, metric names, citation markers, figure/table numbers, math variables, URLs, filenames, and code-like strings.
Do not summarize. Do not omit details. Do not add explanations.
Return only valid JSON in the requested schema."""


USER_PROMPT = """Translate each item from English to Korean.

Rules:
- Literal translation is more important than fluency.
- Keep names such as MMLongBench-Doc, LongDocURL, MMDocRAG, GPT-4o, Recall@K, F1, BLEU, ROUGE-L unchanged.
- Keep citation markers, numbers, equations, and URLs unchanged.
- Preserve line breaks inside each text when present.
- Output exactly:
{{"translations":[{{"i":0,"ko":"..."}}, ...]}}

Items:
{items_json}
"""


def clean_for_count(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def should_translate(node: NavigableString) -> bool:
    text = str(node)
    if not text or not clean_for_count(text):
        return False
    parent = node.parent
    while isinstance(parent, Tag):
        if parent.name and parent.name.lower() in SKIP_TAGS:
            return False
        parent = parent.parent
    stripped = clean_for_count(text)
    if len(stripped) <= 1:
        return False
    if re.fullmatch(r"[\W\d_]+", stripped):
        return False
    return True


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.exists():
        return cache
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        cache[obj["hash"]] = obj["ko"]
    return cache


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def append_cache(path: Path, source: str, ko: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"hash": text_hash(source), "source": source, "ko": ko}, ensure_ascii=False) + "\n")


def make_batches(items: list[tuple[int, str]], max_chars: int) -> list[list[tuple[int, str]]]:
    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_chars = 0
    for item in items:
        item_chars = len(item[1])
        if current and current_chars + item_chars > max_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += item_chars
    if current:
        batches.append(current)
    return batches


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    batch: list[tuple[int, str]],
    temperature: float,
    timeout: int,
    max_retries: int,
) -> dict[int, str]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    items_json = json.dumps([{"i": i, "text": text} for i, text in batch], ensure_ascii=False)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(items_json=items_json)},
        ],
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = extract_json(content)
            translations = parsed["translations"]
            result = {int(item["i"]): str(item["ko"]) for item in translations}
            expected = [i for i, _ in batch]
            # Some OpenAI-compatible servers/models return batch-local indices
            # even when absolute node ids are provided. Recover that shape.
            if set(result) != set(expected) and set(result) == set(range(len(batch))):
                return {expected[local_i]: result[local_i] for local_i in range(len(batch))}
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"translation request failed after retries: {last_error}") from last_error


def translate_html(args: argparse.Namespace) -> None:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    cache_path = Path(args.cache).resolve()
    progress_path = Path(args.progress_log).resolve() if args.progress_log else None
    env_path = Path(args.env_file).resolve() if args.env_file else None
    if env_path:
        load_env_file(env_path)

    html = input_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    nodes = [node for node in soup.find_all(string=True) if should_translate(node)]

    indexed_texts = [(idx, str(node)) for idx, node in enumerate(nodes)]
    cache = load_cache(cache_path)
    todo: list[tuple[int, str]] = []
    translations: dict[int, str] = {}

    for idx, text in indexed_texts:
        cached = cache.get(text_hash(text))
        if cached is not None:
            translations[idx] = cached
        else:
            todo.append((idx, text))

    if args.limit:
        todo = todo[: args.limit]

    def log(message: str) -> None:
        stamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(stamped, flush=True)
        if progress_path:
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            with progress_path.open("a", encoding="utf-8") as f:
                f.write(stamped + "\n")

    log(f"input={input_path}")
    log(f"output={output_path}")
    log(f"text_nodes={len(nodes)} cached={len(translations)} todo={len(todo)}")

    if args.dry_run:
        total_chars = sum(len(t) for _, t in todo)
        log(f"dry_run=true chars_to_translate={total_chars}")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required in the environment")
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL is required in the environment")

    batches = make_batches(todo, args.max_chars)
    for batch_no, batch in enumerate(batches, start=1):
        done_items = len(translations)
        total_items = len(nodes)
        log(
            f"translating batch {batch_no}/{len(batches)} "
            f"items={len(batch)} chars={sum(len(t) for _, t in batch)} "
            f"done_nodes={done_items}/{total_items}"
        )
        batch_translations = call_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=args.model,
            batch=batch,
            temperature=args.temperature,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
        missing = [idx for idx, _ in batch if idx not in batch_translations]
        if missing:
            log(f"batch {batch_no} missing {len(missing)} items; retrying missing items one by one")
            for missing_idx, missing_source in [(idx, src) for idx, src in batch if idx in missing]:
                single = call_openai_compatible(
                    base_url=base_url,
                    api_key=api_key,
                    model=args.model,
                    batch=[(missing_idx, missing_source)],
                    temperature=args.temperature,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                )
                batch_translations.update(single)
        for idx, source in batch:
            ko = batch_translations.get(idx)
            if ko is None:
                raise RuntimeError(f"missing translation for item {idx}")
            translations[idx] = ko
            append_cache(cache_path, source, ko)
        log(f"completed batch {batch_no}/{len(batches)} cached_nodes={len(translations)}/{len(nodes)}")

    for idx, node in enumerate(nodes):
        ko = translations.get(idx)
        if ko is not None:
            node.replace_with(NavigableString(ko))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")
    log(f"wrote {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunked literal Korean translation for structure-preserving HTML.")
    parser.add_argument("--input", required=True, help="Source HTML path")
    parser.add_argument("--output", required=True, help="Translated HTML path")
    parser.add_argument("--cache", required=True, help="JSONL translation cache path")
    parser.add_argument("--model", default="gpt-5.4-mini", help="OpenAI-compatible model name")
    parser.add_argument("--max-chars", type=int, default=6000, help="Approximate source characters per batch")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="Translate only the first N uncached text nodes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--env-file", default=".env", help="Optional .env file to load before reading OPENAI_API_KEY/OPENAI_BASE_URL")
    parser.add_argument("--progress-log", default="", help="Optional progress log path")
    return parser.parse_args(argv)


if __name__ == "__main__":
    translate_html(parse_args(sys.argv[1:]))
