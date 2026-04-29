# GPT-5.4-mini 청크 단위 논문 HTML 직역 프로세스

목표: 논문 HTML의 DOM 구조, 이미지, 표, 수식, 링크를 유지하고 태그 사이의 본문 텍스트만 청크 단위로 한국어 직역한다.

현재 권장 경로는 `scripts/translate_html_blocks.py`이다. 이 스크립트는 HTML 태그를 placeholder로 마스킹한 뒤 LLM에는 태그 사이 텍스트 중심의 masked fragment만 보낸다. `figure.ltx_table` 내부 표 HTML은 LLM에 보내지 않고 원문 그대로 유지한다.

## 비밀값 관리

API 키는 저장소에 커밋하지 않는다. 로컬 실행용 `.env`를 만들고, `.gitignore`로 제외한다.

```bash
cp .env.example .env
# .env 파일을 열어서 OPENAI_API_KEY / OPENAI_BASE_URL 값을 채운다.
```

## 사전 확인

```bash
uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --dry-run
```

## 실행 예시

```bash
uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0
```

## 세 논문 실행

```bash
uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0

uv run scripts/translate_html_chunks.py \
  --input inputs/longdocurl.source.html \
  --output outputs/longdocurl.ko.literal.html \
  --cache outputs/cache/longdocurl.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0

uv run scripts/translate_html_chunks.py \
  --input inputs/mmdocrag.source.html \
  --output outputs/mmdocrag.ko.literal.html \
  --cache outputs/cache/mmdocrag.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --max-chars 6000 \
  --temperature 0
```

## 부분 테스트

먼저 20개 텍스트 노드만 번역해 품질과 API 호환성을 확인한다.

```bash
uv run scripts/translate_html_chunks.py \
  --input inputs/mmlongbench-doc.source.html \
  --output outputs/mmlongbench-doc.ko.literal.sample.html \
  --cache outputs/cache/mmlongbench-doc.translation.jsonl \
  --model gpt-5.4-mini \
  --env-file .env \
  --limit 20 \
  --max-chars 6000 \
  --temperature 0
```

## 구현 방식

- BeautifulSoup으로 HTML을 파싱한다.
- `script`, `style`, `code`, `pre`, `math`, `svg` 내부 텍스트는 건드리지 않는다.
- 번역 대상 텍스트 노드를 순서대로 수집한다.
- 여러 텍스트 노드를 JSON 배열로 묶어 `chat/completions`에 보낸다.
- 모델은 `{"translations":[{"i":0,"ko":"..."}]}` 형식의 JSON만 반환해야 한다.
- 번역 결과를 원래 텍스트 노드 위치에 다시 삽입한다.
- 번역 캐시는 JSONL로 저장해 중단 후 재개할 수 있게 한다.

## 주의

이 파이프라인은 사용자가 번역 권한을 가진 문서에 대해 실행하는 것을 전제로 한다. 공개 논문이라도 전체 직역본을 재배포하면 권리 문제가 생길 수 있으므로, 개인 열람/검토 범위에서 사용한다.
