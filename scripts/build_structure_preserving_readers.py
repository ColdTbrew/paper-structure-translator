from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"
ASSETS = ROOT / "assets"


@dataclass(frozen=True)
class Paper:
    key: str
    title: str
    url: str
    arxiv: str
    note_md: str
    thesis_ko: str
    reading_lens: str


PAPERS = [
    Paper(
        key="mmlongbench-doc",
        title="MMLongBench-Doc",
        url="https://ar5iv.labs.arxiv.org/html/2407.01523v3",
        arxiv="https://arxiv.org/abs/2407.01523",
        note_md="MMLongBench-Doc_ko_note.md",
        thesis_ko=(
            "긴 PDF 문서 전체를 페이지 이미지 또는 OCR 텍스트로 넣었을 때, "
            "모델이 필요한 근거를 찾아 답할 수 있는지 평가한다."
        ),
        reading_lens=(
            "RAG 검색 성능이 아니라 long-context document understanding, cross-page QA, "
            "unanswerable 질문에서의 hallucination 억제를 보는 벤치마크로 읽는다."
        ),
    ),
    Paper(
        key="longdocurl",
        title="LongDocURL",
        url="https://ar5iv.labs.arxiv.org/html/2412.18424v3",
        arxiv="https://arxiv.org/abs/2412.18424",
        note_md="LongDocURL_ko_note.md",
        thesis_ko=(
            "긴 문서에서 understanding, reasoning, locating을 함께 평가하되, "
            "LVLM 평가에서는 정답 evidence 주변 연속 30페이지를 넣는 방식을 쓴다."
        ),
        reading_lens=(
            "일반 RAG가 아니라 oracle evidence window에 가까운 세팅이다. "
            "관련 페이지 묶음이 주어졌을 때 구조/수치/위치 추론을 보는 데 초점을 둔다."
        ),
    ),
    Paper(
        key="mmdocrag",
        title="MMDocRAG",
        url="https://ar5iv.labs.arxiv.org/html/2505.16470v2",
        arxiv="https://arxiv.org/abs/2505.16470",
        note_md="MMDocRAG_ko_note.md",
        thesis_ko=(
            "문서를 text/image quote로 나누고, retrieval, quote selection, "
            "multimodal answer generation을 분리해서 평가한다."
        ),
        reading_lens=(
            "RAG 지향 벤치마크이지만, generation 평가는 fixed candidate quotes 기반인 경우가 중심이다. "
            "retriever 점수와 generator 점수를 섞어 읽지 않는다."
        ),
    ),
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def download(url: str, path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    path.write_text(resp.text, encoding="utf-8")
    return resp.text


def tag_id(tag: Tag, fallback: str) -> str:
    existing = tag.get("id")
    if existing:
        return str(existing)
    text = clean_text(tag.get_text(" "))
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", text).strip("-").lower()
    return slug[:80] or fallback


def extract_headings(soup: BeautifulSoup) -> list[dict[str, str]]:
    headings: list[dict[str, str]] = []
    for idx, h in enumerate(soup.find_all(re.compile(r"^h[1-6]$"))):
        level = int(h.name[1])
        text = clean_text(h.get_text(" "))
        if not text:
            continue
        hid = tag_id(h, f"heading-{idx}")
        headings.append({"level": str(level), "text": text, "id": hid})
    return headings


def extract_figures(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    figures: list[dict[str, str]] = []
    seen: set[str] = set()
    figure_tags = soup.find_all("figure")
    if not figure_tags:
        figure_tags = soup.find_all("img")

    for idx, fig in enumerate(figure_tags):
        if fig.name == "img":
            img = fig
            caption = clean_text(img.get("alt", ""))
        else:
            img = fig.find("img")
            caption_tag = fig.find(["figcaption", "caption"])
            caption = clean_text(caption_tag.get_text(" ")) if caption_tag else clean_text(fig.get_text(" "))
        if not img:
            continue
        src = img.get("src")
        if not src:
            continue
        abs_src = urljoin(base_url, str(src))
        if abs_src in seen:
            continue
        seen.add(abs_src)
        alt = clean_text(img.get("alt", "")) or f"Figure {idx + 1}"
        figures.append(
            {
                "index": str(idx + 1),
                "src": abs_src,
                "alt": alt,
                "caption": caption or alt,
            }
        )
    return figures


def download_figures(paper: Paper, figures: list[dict[str, str]]) -> list[dict[str, str]]:
    paper_assets = ASSETS / paper.key
    paper_assets.mkdir(parents=True, exist_ok=True)
    updated: list[dict[str, str]] = []
    for fig in figures:
        src = fig["src"]
        parsed = urlparse(src)
        suffix = Path(parsed.path).suffix or ".png"
        filename = f"figure-{int(fig['index']):03d}{suffix}"
        target = paper_assets / filename
        if not target.exists():
            try:
                resp = requests.get(src, timeout=30)
                resp.raise_for_status()
                target.write_bytes(resp.content)
            except requests.RequestException:
                # Keep the remote image if downloading fails.
                local_src = src
            else:
                local_src = f"../assets/{paper.key}/{filename}"
        else:
            local_src = f"../assets/{paper.key}/{filename}"
        copied = dict(fig)
        copied["src"] = local_src
        copied["original_src"] = src
        updated.append(copied)
    return updated


def extract_tables(soup: BeautifulSoup) -> list[dict[str, str]]:
    tables: list[dict[str, str]] = []
    for idx, table in enumerate(soup.find_all("table")):
        caption = ""
        prev = table.find_previous(["figcaption", "caption", "p", "div"])
        if prev:
            t = clean_text(prev.get_text(" "))
            if "Table" in t or "표" in t:
                caption = t[:500]
        preview = clean_text(table.get_text(" "))[:800]
        tables.append({"index": str(idx + 1), "caption": caption, "preview": preview})
    return tables


def read_note_summary(note_name: str) -> str:
    path = ROOT / note_name
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    chunks = []
    for heading in ["## 한 줄 요약", "## 우리 관점에서 읽는 법"]:
        match = re.search(rf"{re.escape(heading)}\n\n(.+?)(?=\n## |\Z)", text, re.S)
        if match:
            chunks.append(match.group(1).strip())
    return "\n\n".join(chunks)


def section_commentary(paper: Paper, heading: str) -> str:
    h = heading.lower()
    if "abstract" in h or "introduction" in h:
        return paper.thesis_ko
    if "dataset" in h or "data" in h or "benchmark" in h or "collection" in h:
        return "이 섹션은 데이터셋의 문서 출처, 질문 구성, evidence 단위, 품질 검증 방식을 확인하는 부분이다."
    if "evaluation" in h or "experiment" in h or "result" in h:
        return "이 섹션은 실제 입력 구성, 모델 비교, 채점 지표를 확인하는 부분이다. 특히 RAG 여부와 후보 context 구성 방식을 분리해서 봐야 한다."
    if "retrieval" in h:
        return "이 섹션은 검색기가 gold evidence를 top-k 안에 넣는지를 보는 retrieval 평가로 읽는다."
    if "conclusion" in h:
        return "이 섹션은 벤치마크가 보여주는 한계와 이후 연구 방향을 정리하는 부분이다."
    return "세부 논지는 원문 섹션 구조를 따라 읽고, 한국어 상세 노트의 해당 항목과 대조한다."


def render_html(
    paper: Paper,
    source_html_path: Path,
    headings: list[dict[str, str]],
    figures: list[dict[str, str]],
    tables: list[dict[str, str]],
) -> str:
    note_summary = read_note_summary(paper.note_md)
    toc_items = "\n".join(
        f'<li class="lv{h["level"]}"><a href="#sec-{i}">{html.escape(h["text"])}</a></li>'
        for i, h in enumerate(headings)
    )
    section_cards = "\n".join(
        f"""
        <section class="section-card" id="sec-{i}">
          <div class="section-kicker">원문 heading level {html.escape(h['level'])}</div>
          <h3>{html.escape(h['text'])}</h3>
          <p>{html.escape(section_commentary(paper, h['text']))}</p>
          <a class="source-link" href="{paper.url}#{html.escape(h['id'])}">원문 위치 열기</a>
        </section>
        """
        for i, h in enumerate(headings)
    )
    figure_cards = "\n".join(
        f"""
        <figure class="figure-card">
          <img src="{html.escape(fig['src'])}" alt="{html.escape(fig['alt'])}" loading="lazy">
          <figcaption><strong>Figure {html.escape(fig['index'])}</strong> {html.escape(fig['caption'])}</figcaption>
        </figure>
        """
        for fig in figures
    )
    table_cards = "\n".join(
        f"""
        <section class="table-card">
          <h3>Table {html.escape(table['index'])}</h3>
          <p>{html.escape(table['caption'] or '원문 HTML의 표 구조를 확인한다.')}</p>
          <pre>{html.escape(table['preview'])}</pre>
        </section>
        """
        for table in tables
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(paper.title)} Korean Structure Reader</title>
  <style>
    :root {{ color-scheme: light; --ink:#1d252c; --muted:#5c6975; --line:#d8dee5; --paper:#fbfcfd; --accent:#136f63; --soft:#eef6f4; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f4f6f8; line-height:1.65; }}
    header {{ padding:48px clamp(20px,5vw,72px) 28px; background:linear-gradient(180deg,#ffffff,#eef6f4); border-bottom:1px solid var(--line); }}
    main {{ display:grid; grid-template-columns:minmax(220px,300px) minmax(0,1fr); gap:24px; max-width:1440px; margin:0 auto; padding:24px; }}
    aside {{ position:sticky; top:16px; align-self:start; max-height:calc(100vh - 32px); overflow:auto; background:#fff; border:1px solid var(--line); border-radius:8px; padding:16px; }}
    h1 {{ font-size:clamp(30px,4vw,52px); line-height:1.12; margin:0 0 12px; letter-spacing:0; }}
    h2 {{ font-size:24px; margin:36px 0 12px; }}
    h3 {{ margin:0 0 8px; font-size:19px; }}
    a {{ color:#0e6157; }}
    .summary {{ max-width:920px; font-size:18px; color:#26323a; }}
    .meta {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:18px; }}
    .meta a, .pill {{ border:1px solid var(--line); background:#fff; border-radius:999px; padding:6px 10px; text-decoration:none; font-size:14px; color:#26323a; }}
    .content {{ min-width:0; }}
    .panel, .section-card, .table-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; margin-bottom:16px; }}
    .panel pre {{ white-space:pre-wrap; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; }}
    .toc {{ list-style:none; padding:0; margin:0; }}
    .toc li {{ margin:4px 0; font-size:14px; }}
    .toc .lv3 {{ padding-left:12px; }}
    .toc .lv4, .toc .lv5, .toc .lv6 {{ padding-left:24px; font-size:13px; }}
    .section-kicker {{ color:var(--muted); font-size:13px; margin-bottom:4px; }}
    .source-link {{ font-size:14px; }}
    .figure-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:18px; }}
    .figure-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; margin:0; }}
    .figure-card img {{ display:block; width:100%; max-height:760px; object-fit:contain; background:var(--paper); border:1px solid var(--line); }}
    figcaption {{ margin-top:10px; color:#3f4b55; font-size:14px; }}
    .table-card pre {{ white-space:pre-wrap; overflow:auto; background:#f8fafb; border:1px solid var(--line); padding:12px; border-radius:6px; }}
    @media (max-width:900px) {{ main {{ grid-template-columns:1fr; }} aside {{ position:static; max-height:none; }} .figure-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(paper.title)} 한국어 구조 리더</h1>
    <p class="summary">{html.escape(paper.thesis_ko)}</p>
    <p>{html.escape(paper.reading_lens)}</p>
    <div class="meta">
      <a href="{paper.url}">ar5iv HTML</a>
      <a href="{paper.arxiv}">arXiv</a>
      <a href="../{paper.note_md}">한국어 상세 노트</a>
      <a href="../{source_html_path.as_posix()}">저장된 원문 HTML</a>
      <span class="pill">Headings {len(headings)}</span>
      <span class="pill">Figures {len(figures)}</span>
      <span class="pill">Tables {len(tables)}</span>
    </div>
  </header>
  <main>
    <aside>
      <h2>목차</h2>
      <ul class="toc">{toc_items}</ul>
    </aside>
    <div class="content">
      <section class="panel">
        <h2>읽기 가이드</h2>
        <p>이 파일은 원문 논문 전체를 직역한 번역본이 아니라, 원문 HTML의 heading, figure, table 구조를 보존하면서 한국어로 읽기 흐름을 잡기 위한 리더다. 자세한 한국어 해설은 연결된 상세 노트를 함께 본다.</p>
        <pre>{html.escape(note_summary)}</pre>
      </section>
      <section>
        <h2>섹션 구조</h2>
        {section_cards}
      </section>
      <section>
        <h2>그림 모아보기</h2>
        <div class="figure-grid">{figure_cards or '<p>추출된 figure 이미지가 없습니다. 원문 HTML 링크를 확인하세요.</p>'}</div>
      </section>
      <section>
        <h2>표 미리보기</h2>
        {table_cards or '<p>추출된 table이 없습니다. 원문 HTML 링크를 확인하세요.</p>'}
      </section>
    </div>
  </main>
</body>
</html>
"""


def render_md(
    paper: Paper,
    headings: list[dict[str, str]],
    figures: list[dict[str, str]],
    tables: list[dict[str, str]],
) -> str:
    lines = [
        f"# {paper.title} 한국어 구조 리더",
        "",
        f"- 원문 HTML: {paper.url}",
        f"- arXiv: {paper.arxiv}",
        f"- 상세 노트: ../{paper.note_md}",
        "",
        "## 핵심",
        "",
        paper.thesis_ko,
        "",
        paper.reading_lens,
        "",
        "## 목차와 섹션 해설",
        "",
    ]
    for h in headings:
        level = min(int(h["level"]) + 1, 6)
        lines.extend(
            [
                f"{'#' * level} {h['text']}",
                "",
                section_commentary(paper, h["text"]),
                "",
                f"[원문 위치]({paper.url}#{h['id']})",
                "",
            ]
        )
    lines.extend(["## 그림 모아보기", ""])
    for fig in figures:
        lines.extend(
            [
                f"### Figure {fig['index']}",
                "",
                f"![{fig['alt']}]({fig['src']})",
                "",
                fig["caption"],
                "",
            ]
        )
    lines.extend(["## 표 미리보기", ""])
    for table in tables:
        lines.extend(
            [
                f"### Table {table['index']}",
                "",
                table["caption"] or "원문 HTML의 표 구조를 확인한다.",
                "",
                "```text",
                table["preview"],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    INPUTS.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)

    log_lines = ["# Translation/Reader Build Log", ""]
    index_lines = [
        "# 구조 보존 한국어 논문 리더 인덱스",
        "",
        "원문 전체 직역이 아니라, 이미지와 섹션 구조를 보존한 한국어 리딩본이다.",
        "",
    ]
    index_html_cards: list[str] = []

    for paper in PAPERS:
        source_path = INPUTS / f"{paper.key}.source.html"
        source_html = download(paper.url, source_path)
        soup = BeautifulSoup(source_html, "lxml")
        headings = extract_headings(soup)
        figures = extract_figures(soup, paper.url)
        figures = download_figures(paper, figures)
        tables = extract_tables(soup)

        html_out = OUTPUTS / f"{paper.key}.ko.reader.html"
        md_out = OUTPUTS / f"{paper.key}.ko.reader.md"
        html_out.write_text(render_html(paper, source_path.relative_to(ROOT), headings, figures, tables), encoding="utf-8")
        md_out.write_text(render_md(paper, headings, figures, tables), encoding="utf-8")

        log_lines.extend(
            [
                f"## {paper.title}",
                "",
                f"- Source HTML: {source_path}",
                f"- Reader HTML: {html_out}",
                f"- Reader Markdown: {md_out}",
                f"- Heading count: {len(headings)}",
                f"- Figure count: {len(figures)}",
                f"- Table count: {len(tables)}",
                "",
            ]
        )
        index_lines.extend(
            [
                f"## {paper.title}",
                "",
                f"- [HTML reader](./{html_out.name})",
                f"- [Markdown reader](./{md_out.name})",
                f"- 원문 HTML: {paper.url}",
                f"- headings: {len(headings)}, figures: {len(figures)}, tables: {len(tables)}",
                "",
            ]
        )
        index_html_cards.append(
            f"""
            <article>
              <h2>{html.escape(paper.title)}</h2>
              <p>{html.escape(paper.thesis_ko)}</p>
              <p>{html.escape(paper.reading_lens)}</p>
              <div class="links">
                <a href="./{html_out.name}">HTML reader</a>
                <a href="./{md_out.name}">Markdown reader</a>
                <a href="{paper.url}">ar5iv</a>
                <a href="{paper.arxiv}">arXiv</a>
              </div>
              <p class="meta">headings {len(headings)} · figures {len(figures)} · tables {len(tables)}</p>
            </article>
            """
        )

    (OUTPUTS / "translation_log.md").write_text("\n".join(log_lines), encoding="utf-8")
    (OUTPUTS / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    (OUTPUTS / "index.html").write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>구조 보존 한국어 논문 리더</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f5f7f8; color:#1d252c; line-height:1.65; }}
    header {{ padding:48px clamp(20px,5vw,72px); background:#fff; border-bottom:1px solid #d8dee5; }}
    main {{ max-width:1120px; margin:0 auto; padding:24px; display:grid; gap:18px; }}
    h1 {{ margin:0 0 10px; font-size:clamp(30px,4vw,48px); letter-spacing:0; }}
    article {{ background:#fff; border:1px solid #d8dee5; border-radius:8px; padding:20px; }}
    h2 {{ margin:0 0 8px; }}
    a {{ color:#0e6157; }}
    .links {{ display:flex; flex-wrap:wrap; gap:10px; margin:14px 0; }}
    .links a {{ border:1px solid #d8dee5; border-radius:999px; padding:6px 10px; text-decoration:none; }}
    .meta {{ color:#5c6975; font-size:14px; }}
  </style>
</head>
<body>
  <header>
    <h1>구조 보존 한국어 논문 리더</h1>
    <p>원문 전체 직역이 아니라, 이미지와 섹션 구조를 보존한 한국어 리딩본 모음입니다.</p>
  </header>
  <main>
    {''.join(index_html_cards)}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
