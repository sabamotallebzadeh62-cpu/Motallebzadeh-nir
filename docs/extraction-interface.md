# Extraction interface

Status: schemas and configuration are done. Live API access was checked on 2026-11-06 (see the access matrix).

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

Checked on 2026-11-06 with one short plain-text request per model through the lab LiteLLM
gateway (`LLM_BASE_URL`, key in the local `.env`). Prompt: "Reply with the single word: ok".
Model IDs carry the `iairlab/` prefix in the gateway.

| Role | Model ID | Available | Usage fields | Tokens used (in + out) | Blocker or note |
| --- | --- | --- | --- | --- | --- |
| Extractor (roadmap) | `iairlab/qwen2.5-72b` | no | n/a | 0 | Listed in `/v1/models` but `/chat/completions` returns "Invalid model name". |
| Extractor (fallback) | `iairlab/qwen3.8-27b` | yes | yes | 59 + 25 = 84 | Suggested by Aleksandr Voskresenskii in Telegram on 2026-11-06; written confirmation from the curator is pending. Not the roadmap model. |
| Judge | `iairlab/gpt-oss-120b` | yes | yes | 76 + 42 = 118 | None. |
| Small model | `iairlab/qwen3-32b` | yes | yes | 15 + 50 = 65 and 15 + 89 = 104 | Reasoning model: with `max_tokens` 50 the content was empty (`finish_reason: length`); it answered with `max_tokens` 500. |

Total used by these checks: 371 tokens, counted toward the first-month cap.

Not tested yet: structured (JSON) output, context limits and generation controls. The checks
only show that each model answers a plain request and reports usage.

The extractor change from `qwen2.5-72b` to `qwen3.8-27b` is a recorded blocker, not a silent
substitution. Results from the fallback must not be described as 72B results.
