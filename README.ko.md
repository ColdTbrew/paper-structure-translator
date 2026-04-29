# 구조 보존 논문 번역기

[English](README.md) | [한국어](README.ko.md)

ar5iv HTML을 입력으로 받아, 깔끔한 한국어 논문 리더 HTML을 만드는 OpenAI 호환 파이프라인입니다.

목표는 논문 요약이 아닙니다. 원문 논문의 구조와 읽는 흐름을 최대한 유지하면서, 본문 텍스트를 가능한 한 직역에 가깝게 번역하는 것이 목표입니다.

## 미리보기

생성된 HTML은 조용한 논문 리더처럼 보이도록 설계되어 있습니다. 그림과 표는 제자리에 남고, 인용과 링크는 유지되며, 번역된 본문은 한 줄씩 읽기 좋게 표시됩니다.

| 한국어 리더 | 영어/한국어 병행 리더 |
| --- | --- |
| ![한국어 논문 리더](docs/korean-reader.png) | ![영어와 한국어 병행 논문 리더](docs/parallel-reader.png) |

병행 출력에는 `원본 보기` 모드가 포함됩니다. 이 모드에서는 왼쪽에 영어 원문, 오른쪽에 한국어 번역이 표시됩니다. 스크롤 동기화는 기본으로 켜져 있으며, 필요할 때 끄고 양쪽 위치를 직접 맞춘 뒤 다시 켤 수 있습니다. 다시 켜는 순간 화면은 움직이지 않고, 그 상태를 기준으로 이후 스크롤부터 함께 움직입니다.

## 주요 기능

- PDF 파싱 대신 ar5iv HTML을 사용합니다.
- 모델 호출 전에 HTML 태그를 마스킹하고, 번역 후 같은 태그를 복원합니다.
- 번역 가능한 텍스트 블록만 모델에 보냅니다.
- `figure.ltx_table` 표 HTML은 모델에 보내지 않고 원본 그대로 유지해 토큰을 절약하고 표 깨짐을 줄입니다.
- 링크, 인용, 그림, 수식, 코드/pre/math 블록, 문서 구조를 보존합니다.
- 흰 배경, 중앙 정렬, 읽기 좋은 타이포그래피를 가진 논문 리더 스타일을 적용합니다.
- 한국어 단독 HTML과 영어/한국어 병행 HTML을 모두 생성합니다.
- 병행 리더에서 선택 가능한 스크롤 동기화를 제공합니다.
- JSONL 캐시를 작성해 중단된 번역 작업을 이어서 실행할 수 있습니다.

## 설정

```bash
uv sync
cp .env.example .env
```

로컬 `.env`를 채웁니다.

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://host:port/v1
```

`.env`, 다운로드한 소스, 캐시, 생성된 HTML 출력물은 git에서 무시됩니다.

## 빠른 시작

설정된 전체 파이프라인을 실행합니다.

```bash
./scripts/run_all_block_translations.sh
```

이 명령은 다음 작업을 수행합니다.

1. 설정된 ar5iv HTML 파일을 `inputs/` 아래에 다운로드합니다.
2. 표가 아닌 텍스트 블록을 마스킹한 뒤 번역합니다.
3. 원본 HTML 태그를 복원합니다.
4. 표 HTML은 원본 그대로 유지합니다.
5. 최종 논문 리더 HTML을 `outputs/` 아래에 작성합니다.

현재 설정된 출력물은 다음과 같습니다.

```text
outputs/mmlongbench-doc.ko.paper.html
outputs/mmlongbench-doc.ko-en.paper.html
outputs/longdocurl.ko.paper.html
outputs/longdocurl.ko-en.paper.html
outputs/mmdocrag.ko.paper.html
outputs/mmdocrag.ko-en.paper.html
```

`*.ko.paper.html`은 한국어 단독 리더입니다.  
`*.ko-en.paper.html`은 처음에는 한국어 단독 보기로 열립니다. `원본 보기`를 클릭하면 왼쪽 영어, 오른쪽 한국어의 2열 병행 리더로 전환됩니다.

## 논문 하나만 실행하기

먼저 소스 HTML을 가져옵니다.

```bash
uv run scripts/fetch_sources.py
```

드라이런:

```bash
uv run scripts/translate_html_blocks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.paper.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html \
  --cache outputs/cache/mmdocrag.masked.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.masked.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --dry-run
```

실제 실행:

```bash
PYTHONUNBUFFERED=1 uv run scripts/translate_html_blocks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.paper.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html \
  --cache outputs/cache/mmdocrag.masked.translation.jsonl \
  --progress-log outputs/cache/mmdocrag.masked.progress.log \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 5000
```

## 리더 스타일 재적용 또는 표 복원

이미 번역된 HTML이 있고, 리더 CSS를 새로 적용하거나 원본 표를 다시 복원하고 싶다면 다음 명령을 사용합니다.

```bash
uv run scripts/apply_paper_viewer_style.py \
  outputs/mmdocrag.ko.paper.html \
  outputs/mmdocrag.ko.paper.html \
  inputs/mmdocrag.source.html \
  --bilingual-output outputs/mmdocrag.ko-en.paper.html
```

## 스크립트

- `scripts/fetch_sources.py`: 설정된 ar5iv HTML 소스를 다운로드합니다.
- `scripts/translate_html_blocks.py`: 태그를 마스킹하고, 텍스트 블록을 번역하고, 태그를 복원한 뒤 논문 리더 HTML을 작성합니다.
- `scripts/apply_paper_viewer_style.py`: 리더 CSS를 다시 적용하고, ar5iv asset 링크를 고치며, 선택적으로 원본 표 HTML을 복원합니다.
- `scripts/run_all_block_translations.sh`: 설정된 전체 워크플로를 실행합니다.

## 참고

번역할 권리가 있는 문서에 사용하세요. 전체 번역 논문 출력물은 재배포가 허용된 경우가 아니라면 로컬에 보관하는 것이 좋습니다.
