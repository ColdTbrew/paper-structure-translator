from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import translate_html_blocks  # noqa: E402


class LocalAssetRebaseTests(unittest.TestCase):
    def test_rebases_input_asset_for_output_reader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "inputs"
            output_dir = root / "outputs"
            crop = input_dir / "assets" / "paper" / "layout" / "figure.png"
            crop.parent.mkdir(parents=True)
            output_dir.mkdir()
            crop.write_bytes(b"png")
            soup = BeautifulSoup(
                '<figure><img src="assets/paper/layout/figure.png"></figure>',
                "lxml",
            )

            translate_html_blocks.rebase_local_asset_links(soup, input_dir, output_dir)

            self.assertEqual(soup.img["src"], "../inputs/assets/paper/layout/figure.png")


if __name__ == "__main__":
    unittest.main()
