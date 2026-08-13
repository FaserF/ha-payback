# AI Agent Reference for ha-payback

---

## Token Efficiency Rules (CRITICAL — Read First)

These rules apply to **every response** without exception:

1. **Output minimal prose.** Bullet points only. No introductory sentences, no filler.
2. **No walkthrough unless explicitly asked.** Never create or update `walkthrough.md` unless requested.
3. **No implementation plan unless complex.** Skip planning artifacts for simple tweaks, single-file edits, bug fixes, or minor features.
4. **Short change summaries only.** Output ≤5 bullet points describing *what* changed and *why*.
5. **No repeating file content.** Never echo back code you just wrote or edited.
6. **No tool-call narration.** Do not describe what tool you are about to call.
7. **Targeted file reads only.** Use `grep_search` or `view_file` with `StartLine`/`EndLine`.
8. **Skip trivial confirmations.** Just proceed.
9. **No closing pleasantries.**
10. **Suppress test output noise.** Report failures only.

---

## Codebase Architecture

| Area | Path |
|---|---|
| Integration Entry | `custom_components/payback/__init__.py` |
| Coordinator | `custom_components/payback/coordinator.py` |
| API Client | `custom_components/payback/api.py` |
| Options Flow | `custom_components/payback/config_flow.py` |
| Tests | `tests/` |
| Workflows | `.github/workflows/` |
| Scripts | `.github/scripts/` |

---

## CLI Commands

| Task | Command | Dir |
|---|---|---|
| Run tests | `pytest` | Root |
| Ruff linter | `ruff check . --fix` | Root |
| mypy linter | `mypy .` | Root |

---

## Anti-Ban Safeguards & Security

- **Strict Request Locking**: Shared `asyncio.Lock` ensures zero concurrent requests per account.
- **TLS Fingerprinting**: `curl_cffi` (impersonate="chrome") bypasses cloud security & bot detection.
- **Randomized Jitter**: Delays between API requests (5–15 seconds).
- **Persistent Cache**: Restores last known good data across HA restarts on HTTP 429/403 errors.
- **Exponential Backoff**: Automatic cool-down state when rate-limited.
