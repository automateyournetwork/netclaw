#!/usr/bin/env bash
# Contract tests for analysis-mcp (spec 092, roadmap R17).
#
# R17 carries a hard constraint: a SQL surface must not expose ~/.openclaw/memory/ or
# ~/.openclaw/rag/rag.db. Most of this file exists to prove that boundary holds, and to
# prove it at the DuckDB level rather than only in the string screen -- because a screen
# is a convenience layer and the one spelling it misses is the one that matters.
#
# The DuckDB assertions need the `duckdb` package; CI installs nothing by design (spec 075
# SC-013), so those skip there while the pure-stdlib path checks always run. That gating
# mistake is exactly what broke spec 091's first CI run.
#
# Every exit code is captured DIRECTLY, never through a pipe.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRV="$REPO_ROOT/mcp-servers/analysis-mcp"
PASS=0
FAIL=0
SKIP=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ok()   { printf '  ok   %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL %s\n' "$1"; FAIL=$((FAIL + 1)); }
skip() { printf '  skip %s\n' "$1"; SKIP=$((SKIP + 1)); }

py() {
    local desc="$1" code="$2" out
    out="$(cd "$SRV" && python3 -c "$code" 2>&1)"
    if [ "$out" = "PASS" ]; then ok "$desc"; else bad "$desc -- got: ${out##*$'\n'}"; fi
}

if (cd "$SRV" && python3 -c 'import duckdb' 2>/dev/null); then HAVE_DUCKDB=1; else HAVE_DUCKDB=0; fi

echo "=== Path allowlist: NetClaw's own stores are never readable ==="

# Pure stdlib -- always runs, including in CI.
py "the memory store is denied" '
import loader
print("PASS" if loader.denied("/home/u/.openclaw/memory/memory.db") else "not denied")'

py "the RAG store is denied" '
import loader
print("PASS" if loader.denied("/home/u/.openclaw/rag/rag.db") else "not denied")'

py "the federation store is denied" '
import loader
print("PASS" if loader.denied("/home/u/.openclaw/n2n/federation.db") else "not denied")'

py "the GAIT audit trail is denied" '
import loader
print("PASS" if loader.denied("/home/u/.openclaw/gait/x.jsonl") else "not denied")'

py "ssh and cloud credential dirs are denied" '
import loader
missed = [p for p in ("/home/u/.ssh/id_rsa", "/home/u/.aws/credentials",
                      "/home/u/.kube/config", "/home/u/proj/.env") if not loader.denied(p)]
print("PASS" if not missed else f"missed: {missed}")'

py "the denial reason explains itself rather than just refusing" '
import loader
r = loader.denied("/home/u/.openclaw/memory/m.db")
print("PASS" if "backdoor" in r else r)'

py "an NSM run directory is NOT denied" '
import loader, os
p = os.path.join(os.path.expanduser("~"), ".openclaw", "nsm", "runs", "zeek-1", "conn.log")
print("PASS" if loader.denied(p) is None else loader.denied(p))'

py "a path outside every allowed root is rejected" '
import loader
print("PASS" if not loader.within_roots("/etc/passwd") else "accepted")'

echo
echo "=== Statement screen: only reads, one at a time ==="

py "SELECT is accepted" '
import sandbox
sandbox.screen("SELECT 1"); print("PASS")'

py "WITH is accepted" '
import sandbox
sandbox.screen("WITH x AS (SELECT 1) SELECT * FROM x"); print("PASS")'

py "a trailing semicolon is fine" '
import sandbox
sandbox.screen("SELECT 1;"); print("PASS")'

py "a stacked second statement is refused" '
import sandbox
try:
    sandbox.screen("SELECT 1; ATTACH \x27/etc/x\x27 AS y"); print("accepted")
except sandbox.QueryRefused as e: print("PASS" if "one statement" in str(e) else e)'

for pair in "DROP:DROP TABLE t" "INSERT:INSERT INTO t VALUES (1)" "UPDATE:UPDATE t SET a=1" \
            "DELETE:DELETE FROM t" "CREATE:CREATE TABLE t (a INT)" "ATTACH:ATTACH \x27/x\x27 AS y" \
            "COPY:COPY (SELECT 1) TO \x27/tmp/x\x27" "INSTALL:INSTALL httpfs" \
            "LOAD:LOAD httpfs" "SET:SET enable_external_access=true" "PRAGMA:PRAGMA database_list"; do
    kw="${pair%%:*}"; stmt="${pair#*:}"
    py "$kw is refused" "
import sandbox
try:
    sandbox.screen('''$stmt'''); print('accepted')
except sandbox.QueryRefused: print('PASS')"
done

py "the ATTACH refusal names the stores it protects" '
import sandbox
try: sandbox.screen("ATTACH \x27/x\x27 AS y")
except sandbox.QueryRefused as e: print("PASS" if "memory and RAG" in str(e) else e)'

echo
echo "=== DuckDB-level lockdown (the real boundary) ==="

if [ "$HAVE_DUCKDB" != "1" ]; then
    skip "lockdown enforcement (the duckdb package is not installed here)"
    skip "materialised tables survive lockdown"
    skip "query timeout interrupts a runaway scan"
    skip "truncation is reported honestly"
else
    # The central assertion: after lockdown DuckDB itself refuses every escape, so the
    # screen above is defence in depth rather than the only thing standing there.
    py "after lockdown DuckDB refuses every filesystem and network escape" '
import sandbox, tempfile, os
d = tempfile.mkdtemp()
open(os.path.join(d, "a.csv"), "w").write("x\n1\n")
sb = sandbox.Sandbox()
sb.load_sql(f"CREATE TABLE t AS SELECT * FROM read_csv(\x27{d}/a.csv\x27)")
sb.lock()
escapes = [
    "SELECT * FROM read_csv(\x27/etc/passwd\x27)",
    "SELECT * FROM glob(\x27/home/**\x27)",
    "ATTACH \x27/home/u/.openclaw/rag/rag.db\x27 AS r",
    "COPY (SELECT 1) TO \x27/tmp/exfil.csv\x27",
    "SET enable_external_access=true",
    "SET lock_configuration=false",
    "INSTALL httpfs",
    "LOAD httpfs",
]
allowed = []
for s in escapes:
    try:
        sb.conn.execute(s); allowed.append(s)
    except Exception: pass
print("PASS" if not allowed else f"ALLOWED: {allowed}")'

    # A VIEW would not survive -- it is lazily evaluated and reopens the file. This asserts
    # the loader uses TABLE, which is the reason the row cap exists.
    py "a materialised table is still queryable after lockdown" '
import sandbox, tempfile, os
d = tempfile.mkdtemp()
open(os.path.join(d, "a.csv"), "w").write("x\n1\n2\n")
sb = sandbox.Sandbox()
sb.load_sql(f"CREATE TABLE t AS SELECT * FROM read_csv(\x27{d}/a.csv\x27)")
sb.lock()
cols, rows, trunc = sb.query("SELECT count(*) FROM t", 10, 100)
print("PASS" if rows[0][0] == 2 else rows)'

    py "the loader builds a TABLE, never a VIEW (a view dies at lockdown)" '
import loader
sql = loader.load_statement({"table": "t", "path": "/x/y.csv", "reader": "read_csv", "bytes": 1})
print("PASS" if sql.startswith("CREATE TABLE") and "VIEW" not in sql else sql)'

    py "a runaway query is interrupted rather than hanging forever" '
import sandbox, time
sb = sandbox.Sandbox(); sb.lock()
t0 = time.time()
try:
    sb.query("SELECT count(*) FROM range(100000000000)", 2, 10); print("completed")
except sandbox.QueryTimeout:
    print("PASS" if time.time() - t0 < 20 else "too slow")'

    py "truncation is reported, not silently hidden" '
import sandbox
sb = sandbox.Sandbox(); sb.lock()
cols, rows, trunc = sb.query("SELECT * FROM range(50)", 10, 5)
print("PASS" if trunc and len(rows) == 5 else f"trunc={trunc} n={len(rows)}")'

    py "a query before lockdown is refused outright" '
import sandbox
sb = sandbox.Sandbox()
try:
    sb.query("SELECT 1", 5, 5); print("ran unlocked")
except RuntimeError as e: print("PASS" if "before lockdown" in str(e) else e)'

    py "loading a dataset after lockdown is refused" '
import sandbox
sb = sandbox.Sandbox(); sb.lock()
try:
    sb.load_sql("CREATE TABLE z AS SELECT 1"); print("loaded after lock")
except RuntimeError as e: print("PASS" if "locked" in str(e) else e)'
fi

echo
echo "=== Empty-input honesty ==="

py "an empty file is skipped rather than loaded as a rowless dataset" '
import loader, os, tempfile
d = tempfile.mkdtemp()
open(os.path.join(d, "empty.csv"), "w").close()
os.environ["ANALYSIS_EXTRA_ROOTS"] = d
found, notes = loader.discover()
hit = [f for f in found if f["path"].endswith("empty.csv")]
print("PASS" if not hit and any("empty" in n for n in notes) else f"found={hit}")'

echo
echo "=== Summary ==="
printf '  passed: %d\n  failed: %d\n  skipped: %d\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] || exit 1
echo "  all analysis-mcp contract tests passed"
