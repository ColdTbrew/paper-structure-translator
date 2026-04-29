from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

from translate_html_blocks import fix_file_viewer_links, inject_style


def main(argv: list[str]) -> None:
    if len(argv) not in {1, 2}:
        raise SystemExit("usage: apply_paper_viewer_style.py INPUT_HTML [OUTPUT_HTML]")
    input_path = Path(argv[0]).resolve()
    output_path = Path(argv[1]).resolve() if len(argv) == 2 else input_path
    soup = BeautifulSoup(input_path.read_text(encoding="utf-8"), "lxml")
    inject_style(soup)
    fix_file_viewer_links(soup)
    output_path.write_text(str(soup), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
