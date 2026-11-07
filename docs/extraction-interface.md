# Extraction interface

Status: schemas and configuration are done. Live API access was checked on 2026-11-06 and 2026-11-07 (see the access matrix); structured output is not tested yet.

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

Checked on 2026-11-06 and 2026-11-07 through the lab LiteLLM gateway (one short request per model, `LLM_BASE_URL=https://api.duckduck.cloud/v1`). Model IDs carry the `iairlab/` prefix. Structured (JSON) output has not been tested yet.

| Role | Model ID | Available | Structured response | Usage fields | Blocker |
| --- | --- | --- | --- | --- | --- |
| Extractor (roadmap) | `iairlab/qwen2.5-72b` | listed in `/v1/models`, chat fails | not tested | not tested | chat request returns "Invalid model name" (HTTP 400); reported to the lab |
| Extractor (proposed replacement) | `iairlab/qwen3.8-27b` | yes | not tested | yes | reasoning model; change pending curator confirmation |
| Judge | `iairlab/gpt-oss-120b` | yes | not tested | yes (prompt, completion, total tokens) | reasoning model: needs a large `max_tokens` (with 10 the content was empty) |
| Small model (proposed, replaces local Qwen3-8B) | `iairlab/qwen3-32b` | yes | not tested | yes | reasoning model; no T4 access; change pending curator confirmation |

Changes marked "proposed" are not approved yet. Mocked responses are not evidence of live access.
