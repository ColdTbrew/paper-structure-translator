#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import socketserver
import sys
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import apply_paper_viewer_style  # noqa: E402
import translate_html_blocks  # noqa: E402


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_MAX_CHARS = 5000


def write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def emit(args: argparse.Namespace, payload: dict[str, Any], message: str) -> None:
    if args.json:
        write_json(payload)
    else:
        print(message)


def fail(message: str, hint: str | None = None, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    if hint:
        print(f"hint: {hint}", file=sys.stderr)
    raise SystemExit(code)


def load_env_file(path: Path) -> None:
    translate_html_blocks.load_env_file(path)


def slug_from_input(path: Path) -> str:
    name = path.name
    if name.endswith(".source.html"):
        return name[: -len(".source.html")]
    if name.endswith(".html"):
        return name[: -len(".html")]
    return path.stem


def resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    paper_id = args.paper_id
    input_path = Path(args.input) if args.input else None
    if not paper_id and input_path:
        paper_id = slug_from_input(input_path)
    if not paper_id:
        fail(
            "--paper-id is required when --input is not provided",
            "try: scripts/paper_translator.py translate --paper-id my-paper --source-url https://ar5iv.labs.arxiv.org/html/...",
        )

    input_path = input_path or Path("inputs") / f"{paper_id}.source.html"
    output_path = Path(args.output) if args.output else Path("outputs") / f"{paper_id}.ko.paper.html"
    bilingual_output = (
        Path(args.bilingual_output)
        if args.bilingual_output
        else Path("outputs") / f"{paper_id}.ko-en.paper.html"
    )
    cache_arg = getattr(args, "cache", "")
    progress_arg = getattr(args, "progress_log", "")
    cache_path = Path(cache_arg) if cache_arg else Path("outputs/cache") / f"{paper_id}.masked.translation.jsonl"
    progress_path = (
        Path(progress_arg)
        if progress_arg
        else Path("outputs/cache") / f"{paper_id}.masked.progress.log"
    )
    return {
        "input": input_path,
        "output": output_path,
        "bilingual_output": bilingual_output,
        "cache": cache_path,
        "progress_log": progress_path,
    }


def fetch_source(source_url: str, output_path: Path, force: bool, dry_run: bool) -> dict[str, Any]:
    if output_path.exists() and not force:
        return {
            "status": "exists",
            "source_url": source_url,
            "output": str(output_path),
            "bytes": output_path.stat().st_size,
        }
    if dry_run:
        return {
            "status": "dry_run",
            "source_url": source_url,
            "output": str(output_path),
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(source_url, timeout=60)
    response.raise_for_status()
    output_path.write_text(response.text, encoding="utf-8")
    return {
        "status": "wrote",
        "source_url": source_url,
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
    }


def command_doctor(args: argparse.Namespace) -> None:
    env_path = Path(args.env_file)
    load_env_file(env_path)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    checks = {
        "cwd": str(Path.cwd()),
        "env_file": str(env_path),
        "env_file_exists": env_path.exists(),
        "openai_api_key_present": bool(api_key),
        "openai_base_url_present": bool(base_url),
        "inputs_dir_exists": Path("inputs").exists(),
        "outputs_dir_exists": Path("outputs").exists(),
        "scripts_dir_exists": Path("scripts").exists(),
    }
    ok = all(
        checks[key]
        for key in (
            "env_file_exists",
            "openai_api_key_present",
            "openai_base_url_present",
            "scripts_dir_exists",
        )
    )
    payload = {"ok": ok, "checks": checks}
    if args.json:
        write_json(payload)
    else:
        for key, value in checks.items():
            print(f"{key}: {value}")
        if not ok:
            print("hint: cp .env.example .env && edit .env", file=sys.stderr)
    raise SystemExit(0 if ok else 1)


def command_fetch(args: argparse.Namespace) -> None:
    output = Path(args.output) if args.output else Path("inputs") / f"{args.paper_id}.source.html"
    result = fetch_source(args.source_url, output, args.force, args.dry_run)
    emit(args, {"ok": True, "result": result}, f"{result['status']} {result['output']}")


def command_translate(args: argparse.Namespace) -> None:
    paths = resolve_paths(args)
    fetch_result = None
    if args.source_url:
        fetch_result = fetch_source(args.source_url, paths["input"], args.force, args.dry_run)
    if args.dry_run and args.source_url and not paths["input"].exists():
        payload = {
            "ok": True,
            "dry_run": True,
            "note": "source would be fetched before block analysis; run fetch or remove --dry-run to continue",
            "fetch": fetch_result,
            "input": str(paths["input"]),
            "output": str(paths["output"]),
            "bilingual_output": str(paths["bilingual_output"]),
            "cache": str(paths["cache"]),
            "progress_log": str(paths["progress_log"]),
        }
        emit(args, payload, f"dry_run fetch_then_translate {paths['input']} -> {paths['output']}")
        return
    if not paths["input"].exists() and not args.dry_run:
        fail(
            f"input HTML not found: {paths['input']}",
            f"try: scripts/paper_translator.py fetch --paper-id {args.paper_id} --source-url https://ar5iv.labs.arxiv.org/html/...",
        )

    translated_args = [
        "--input",
        str(paths["input"]),
        "--output",
        str(paths["output"]),
        "--bilingual-output",
        str(paths["bilingual_output"]),
        "--cache",
        str(paths["cache"]),
        "--progress-log",
        str(paths["progress_log"]),
        "--model",
        args.model,
        "--env-file",
        args.env_file,
        "--max-chars",
        str(args.max_chars),
        "--timeout",
        str(args.timeout),
        "--max-retries",
        str(args.max_retries),
    ]
    if args.dry_run:
        translated_args.append("--dry-run")

    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            translate_html_blocks.main(translated_args)
    else:
        translate_html_blocks.main(translated_args)

    payload = {
        "ok": True,
        "dry_run": args.dry_run,
        "fetch": fetch_result,
        "input": str(paths["input"]),
        "output": str(paths["output"]),
        "bilingual_output": str(paths["bilingual_output"]),
        "cache": str(paths["cache"]),
        "progress_log": str(paths["progress_log"]),
    }
    if args.json:
        write_json(payload)


def command_restyle(args: argparse.Namespace) -> None:
    paths = resolve_paths(args)
    source_path = Path(args.source) if args.source else paths["input"]
    if args.dry_run:
        emit(
            args,
            {
                "ok": True,
                "dry_run": True,
                "input": str(paths["output"]),
                "output": str(paths["output"]),
                "source": str(source_path),
                "bilingual_output": str(paths["bilingual_output"]),
            },
            f"dry_run restyle {paths['output']}",
        )
        return
    if not paths["output"].exists():
        fail(
            f"translated HTML not found: {paths['output']}",
            f"try: scripts/paper_translator.py translate --paper-id {args.paper_id} --input {source_path}",
        )
    if not source_path.exists():
        fail(f"source HTML not found: {source_path}")
    restyle_args = [
        str(paths["output"]),
        str(paths["output"]),
        str(source_path),
        "--bilingual-output",
        str(paths["bilingual_output"]),
    ]
    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            apply_paper_viewer_style.main(restyle_args)
        write_json(
            {
                "ok": True,
                "input": str(paths["output"]),
                "output": str(paths["output"]),
                "source": str(source_path),
                "bilingual_output": str(paths["bilingual_output"]),
            }
        )
    else:
        apply_paper_viewer_style.main(restyle_args)


def command_serve(args: argparse.Namespace) -> None:
    directory = Path(args.directory).resolve()
    if args.json:
        write_json(
            {
                "ok": True,
                "url": f"http://{args.host}:{args.port}/",
                "directory": str(directory),
            }
        )
    handler = lambda *handler_args, **handler_kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(directory),
        **handler_kwargs,
    )
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        if not args.json:
            print(f"serving {directory} at http://{args.host}:{args.port}/")
        httpd.serve_forever()


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="write a deterministic JSON summary to stdout")


def add_path_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--paper-id", default="", help="stable paper id used for default input/output paths")
    parser.add_argument("--input", default="", help="source ar5iv HTML path; defaults to inputs/<paper-id>.source.html")
    parser.add_argument("--output", default="", help="Korean output path; defaults to outputs/<paper-id>.ko.paper.html")
    parser.add_argument(
        "--bilingual-output",
        default="",
        help="bilingual output path; defaults to outputs/<paper-id>.ko-en.paper.html",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-translator",
        description="Agent-aware CLI for structure-preserving Korean paper HTML translation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor",
        help="check local environment readiness",
        description="Check whether dependencies, directories, and headless API credentials are ready.",
        epilog="example: scripts/paper_translator.py doctor --json",
    )
    add_common_flags(doctor)
    doctor.add_argument("--env-file", default=".env")
    doctor.set_defaults(func=command_doctor)

    fetch = subparsers.add_parser(
        "fetch",
        help="download one ar5iv HTML source",
        description="Download a single ar5iv HTML document into inputs/ using explicit CLI flags.",
        epilog="example: scripts/paper_translator.py fetch --paper-id my-paper --source-url https://ar5iv.labs.arxiv.org/html/...",
    )
    add_common_flags(fetch)
    fetch.add_argument("--paper-id", required=True)
    fetch.add_argument("--source-url", required=True)
    fetch.add_argument("--output", default="")
    fetch.add_argument("--force", action="store_true", help="overwrite existing input HTML")
    fetch.add_argument("--dry-run", action="store_true", help="show what would be downloaded without writing files")
    fetch.set_defaults(func=command_fetch)

    translate = subparsers.add_parser(
        "translate",
        help="translate one paper into Korean reader HTML",
        description="Translate one source HTML file and write Korean-only plus bilingual reader HTML.",
        epilog=(
            "example: scripts/paper_translator.py translate --paper-id my-paper "
            "--source-url https://ar5iv.labs.arxiv.org/html/... --dry-run"
        ),
    )
    add_common_flags(translate)
    add_path_flags(translate)
    translate.add_argument("--source-url", default="", help="optional ar5iv URL to fetch before translating")
    translate.add_argument("--force", action="store_true", help="overwrite existing fetched source when --source-url is used")
    translate.add_argument("--cache", default="")
    translate.add_argument("--progress-log", default="")
    translate.add_argument("--model", default=DEFAULT_MODEL)
    translate.add_argument("--env-file", default=".env")
    translate.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    translate.add_argument("--timeout", type=int, default=180)
    translate.add_argument("--max-retries", type=int, default=3)
    translate.add_argument("--dry-run", action="store_true")
    translate.set_defaults(func=command_translate)

    restyle = subparsers.add_parser(
        "restyle",
        help="refresh viewer CSS and restore source tables",
        description="Reapply viewer styling and rebuild bilingual output without making model calls.",
        epilog="example: scripts/paper_translator.py restyle --paper-id mmdocrag",
    )
    add_common_flags(restyle)
    add_path_flags(restyle)
    restyle.add_argument("--source", default="", help="source HTML for table restoration; defaults to input path")
    restyle.add_argument("--dry-run", action="store_true")
    restyle.set_defaults(func=command_restyle)

    serve = subparsers.add_parser(
        "serve",
        help="serve the workspace for browser verification",
        description="Start a local static file server for inspecting generated outputs in a browser.",
        epilog="example: scripts/paper_translator.py serve --port 8799",
    )
    add_common_flags(serve)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8799)
    serve.add_argument("--directory", default=".")
    serve.set_defaults(func=command_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
