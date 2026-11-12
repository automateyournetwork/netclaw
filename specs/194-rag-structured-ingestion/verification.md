# Verification

Run 2026-11-12, 22:14–22:59 UTC, cfafa46c, branch 194-rag-structured-ingestion. Attempt 1 of 3. Baseline: .json is absent from supported formats, URL preview reports links and title, and the fetch tool has no TLS parameter. Verification covers FR1–FR4 with a temporary document store and offline fixtures.

## Results

- `python -m pytest -q tests/unit/test_rag_*.py` passed 109 tests using the RAG component runtime. Includes the HTTP/2-only loopback TLS fixture, self-signed rejection by default, explicit opt-out, redirect refusal and a compressed response exceeding the decoded limit. The staging test synchronized two requests for the same URL and verified distinct bytes and cleanup.
- `python -m pytest -q tests/integration/test_rag_mcp.py tests/integration/test_rag_eval.py` passed 19 tests. Three golden-set evaluations skipped because no operator corpus was supplied. A deterministic offline embedder exercised ingest through retrieval, including the cited method and path.
- `npm --prefix ui/netclaw-visual ci --ignore-scripts`, `npm --prefix ui/netclaw-visual test` (545 tests), and `npm --prefix ui/netclaw-visual run build` passed. Headless Chromium selected api.json in both actual HUD upload components. A loopback multipart handler observed the filename and original JSON body for each submission.
- `python3 scripts/verify-spec-artifacts.py`, `python3 scripts/prepare-release.py --check`, `python3 scripts/verify-catalog-coverage.py`, `python3 scripts/check-skill-limits.py`, `python3 scripts/check-catalog-metadata.py`, `node scripts/build-catalog.mjs --check` and `python3 scripts/build-catalog.py --check` passed.
- `python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability` passed all six surfaces.
- `python3 scripts/run-contract-tests.py --list` and `--matrix` exit 2 on both this branch and cfafa46c. Upstream's tests/gcp directory lacks a manifest entry. The component tests above ran directly.

No deployed service, authenticated appliance or production corpus was accessed. The browser check used a fixture upload endpoint. Full reference regeneration also reflected historical changes in unrelated components. Only the release entry and RAG reference were included.
