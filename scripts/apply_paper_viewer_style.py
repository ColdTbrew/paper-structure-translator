from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

from translate_html_blocks import fix_file_viewer_links, inject_style


def restore_source_tables(translated: BeautifulSoup, source: BeautifulSoup) -> int:
    restored = 0
    source_tables = {
        table.get("id"): table
        for table in source.select("figure.ltx_table")
        if table.get("id")
    }
    for table in translated.select("figure.ltx_table"):
        table_id = table.get("id")
        if not table_id or table_id not in source_tables:
            continue
        table.replace_with(BeautifulSoup(str(source_tables[table_id]), "lxml").find("figure"))
        restored += 1
    return restored


def main(argv: list[str]) -> None:
    if len(argv) not in {1, 2, 3}:
        raise SystemExit("usage: apply_paper_viewer_style.py INPUT_HTML [OUTPUT_HTML] [SOURCE_HTML_FOR_TABLES]")
    input_path = Path(argv[0]).resolve()
    output_path = Path(argv[1]).resolve() if len(argv) == 2 else input_path
    source_path = Path(argv[2]).resolve() if len(argv) == 3 else None
    if len(argv) == 3:
        output_path = Path(argv[1]).resolve()
    soup = BeautifulSoup(input_path.read_text(encoding="utf-8"), "lxml")
    restored = 0
    if source_path:
        source_soup = BeautifulSoup(source_path.read_text(encoding="utf-8"), "lxml")
        restored = restore_source_tables(soup, source_soup)
    inject_style(soup)
    fix_file_viewer_links(soup)
    output_path.write_text(str(soup), encoding="utf-8")
    print(f"wrote {output_path} restored_tables={restored}")


if __name__ == "__main__":
    main(sys.argv[1:])
