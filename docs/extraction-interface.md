# Extraction interface

Status: schemas and configuration are done. Live API access is not yet verified.

## Credentials and settings

Values come from `.env` (never committed) or the environment. See `.env.example`.

| Variable | Meaning |
| --- | --- |
| `LLM_BASE_URL` | Authorised endpoint, supplied by the curator |
| `LLM_API_KEY` | Key, kept only in the local `.env` |
| `EXTRACTOR_MODEL` | Extractor model ID (roadmap: `qwen2.5-72b`) |
| `JUDGE_MODEL` | Distinct judge model ID (roadmap: `gpt-oss-120b`) |
| `LLM_TIMEOUT_S` | Timeout of one request, in seconds |
| `LLM_MAX_RETRIES` | Maximum retries per call |

## Records

Defined in `src/motallebzadeh_nir/extraction_types.py`.

- `Chunk`: `document_id`, `chunk_id`, `text`. Gold references are stored separately.
- `Triple`: `triple_id`, `document_id`, `subject`, `predicate`, `object`, optional `evidence`.
  `triple_id` comes from `make_triple_id`, so the same fact in the same document always gets the same ID.
- `Usage`: `input_tokens`, `output_tokens`. `None` means the provider did not report it; it is never 0.
- `ExtractionResult`: `document_id`, `chunk_id`, `model_id`, `status`, `triples`, `error`, `usage`.

## Empty success versus failure

- `status = ok`, `triples = []`: a valid empty graph. No error.
- `status = failed`: a failed extraction. `error` is required and `triples` must be empty.

The schema rejects any other combination.

## Timeout and retries

Each request uses `LLM_TIMEOUT_S`. A failed call is retried at most `LLM_MAX_RETRIES` times.
After the last retry the chunk is recorded as `failed` with the error message; it is never
silently turned into an empty graph. Every attempt counts toward the first-month token cap.

## Settings fixed for comparison

Model IDs, the seed (`SEED`), the timeout, the retry limit, and generation controls
(to be fixed after the first API check) stay identical across compared methods.

## Access matrix

Not filled yet. Live access has not been verified.

| Role | Model ID | Available | Structured response | Usage fields | Blocker |
| --- | --- | --- | --- | --- | --- |
| Extractor | `qwen2.5-72b` | unknown | unknown | unknown | waiting for access from the curator |
| Judge | `gpt-oss-120b` | unknown | unknown | unknown | waiting for access from the curator |

Until access is confirmed, the schemas are tested with mocked responses only.
A mock is not evidence of live access.
