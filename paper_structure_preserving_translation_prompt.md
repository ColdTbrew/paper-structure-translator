# 구조 보존 논문 번역 프로세스 실행 프롬프트

아래 프롬프트를 Codex 새 세션 또는 별도 작업 폴더에서 그대로 실행한다. 목표는 논문 PDF/HTML의 이미지, 표, 수식, 섹션 구조를 최대한 유지하면서 한국어 번역본을 만드는 것이다.

## 실행 프롬프트

너는 논문 번역 파이프라인을 구현/실행하는 Codex 에이전트다.

작업 목표:

1. 논문 원문 PDF 또는 HTML을 입력으로 받는다.
2. 이미지, figure, table, equation, section heading, citation, footnote 구조를 최대한 유지한다.
3. 본문 텍스트만 한국어로 번역한다.
4. 원문 파일은 절대 덮어쓰지 않는다.
5. 결과물은 다음 형태로 저장한다.
   - `paper_name.source.md` 또는 `paper_name.source.html`
   - `paper_name.ko.md` 또는 `paper_name.ko.html`
   - `assets/` 폴더: 추출된 이미지
   - `translation_log.md`: 사용한 도구, 실패한 블록, 수동 검토 TODO

환경 제약:

- `uv`를 사용한다.
- 프로젝트 루트에 `.venv`를 만든다.
- 전역 Python 환경을 오염시키지 않는다.
- 입력 논문이 born-digital PDF라면 OCR을 기본값으로 쓰지 않는다.
- 수식, 코드, citation key, URL, 이미지 경로는 번역하지 않는다.

권장 구현 순서:

1. 작업 폴더 준비

```bash
mkdir -p paper-translate-workspace
cd paper-translate-workspace
uv venv .venv
source .venv/bin/activate
```

2. 입력 유형 판단

- arXiv/ar5iv HTML이 있으면 HTML-first 경로를 우선한다.
- PDF만 있으면 PDF-first 경로를 사용한다.
- 스캔 PDF면 OCR 필요 여부를 별도로 표시한다.

3. HTML-first 경로

HTML이 있는 경우:

- 원본 HTML을 저장한다.
- `img`, `figure`, `table`, `math`, `pre`, `code`, `a`, `sup`, `sub` 태그를 보존한다.
- BeautifulSoup 또는 lxml로 DOM을 파싱한다.
- 텍스트 노드만 번역 대상으로 추출한다.
- 번역 후 같은 DOM 위치에 다시 삽입한다.
- 이미지 `src`는 원본 링크를 유지하거나 assets 폴더로 다운로드해서 상대경로로 바꾼다.
- 결과를 `paper_name.ko.html`로 저장한다.

4. PDF-first 경로

PDF만 있는 경우:

- 1차 시도: Docling 또는 Marker로 Markdown/HTML 변환한다.
- 문단 순서, figure caption, table, equation이 무너지는지 샘플 페이지를 확인한다.
- 이미지가 추출되면 `assets/`에 저장하고 Markdown의 이미지 링크를 상대경로로 유지한다.
- 변환 결과를 `paper_name.source.md`로 저장한다.
- Markdown AST 또는 HTML 변환 후 DOM 단위로 텍스트만 번역한다.
- `![...](...)`, `$...$`, `$$...$$`, citation, URL, code block은 번역하지 않는다.

5. 번역 규칙

- 제목과 섹션 heading은 한국어로 번역하되, 필요하면 원문 용어를 괄호에 남긴다.
- technical term은 첫 등장 시 `한국어(English)` 형태로 쓴다.
- dataset, benchmark, model, metric 이름은 원문 그대로 둔다.
- figure/table 번호는 그대로 둔다.
- figure caption은 번역한다.
- 표 내부 텍스트는 가능하면 번역하되 수치, 모델명, metric명은 유지한다.
- 수식은 절대 번역하지 않는다.
- prompt, code, command는 번역하지 않는다.

6. 결과 검증

다음 항목을 자동/수동으로 확인한다.

- 원문과 번역본의 heading 개수가 같은가
- 이미지 개수가 같은가
- figure/table 번호가 사라지지 않았는가
- 이미지 링크가 깨지지 않았는가
- 수식 블록이 깨지지 않았는가
- Mermaid 또는 Markdown 렌더링이 깨지지 않는가
- 번역 실패 또는 빈 문단이 있는가

7. 최종 보고

마지막에 다음 형식으로 보고한다.

```markdown
## 결과

- 원문 보존본:
- 한국어 번역본:
- 이미지 폴더:
- 로그:

## 검증

- heading 개수:
- image 개수:
- table/figure caption:
- 깨진 링크:
- 수동 검토 TODO:
```

## 추천 도구 선택 기준

| 상황 | 추천 경로 |
|---|---|
| ar5iv HTML이 잘 열림 | HTML-first |
| 논문 PDF가 born-digital이고 그림/표가 많음 | Docling 또는 Marker |
| 텍스트만 빨리 필요 | MarkItDown |
| 복잡한 layout, multi-column, 수식 많음 | Marker 또는 Docling |
| 스캔 PDF | OCR 필요, 별도 검토 |

## 핵심 원칙

번역 품질보다 먼저 구조 보존을 확인한다. 논문 번역본은 본문이 자연스러워도 그림, caption, section, equation 위치가 무너지면 읽기 어렵다. 따라서 `원본 구조 추출 -> 구조 검증 -> 텍스트 노드 번역 -> 렌더링 검증` 순서로 진행한다.
