from __future__ import annotations

from pathlib import Path

import requests


PAPERS = {
    "mmlongbench-doc": "https://ar5iv.labs.arxiv.org/html/2407.01523v3",
    "longdocurl": "https://ar5iv.labs.arxiv.org/html/2412.18424v3",
    "mmdocrag": "https://ar5iv.labs.arxiv.org/html/2505.16470v2",
}


def main() -> None:
    out_dir = Path("inputs")
    out_dir.mkdir(exist_ok=True)

    for key, url in PAPERS.items():
        path = out_dir / f"{key}.source.html"
        if path.exists():
            print(f"exists {path}")
            continue
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
