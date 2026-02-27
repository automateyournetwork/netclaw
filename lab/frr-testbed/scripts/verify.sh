#!/usr/bin/env bash
# Verify FRR lab testbed is operational
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}PASS${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo -e "  ${YELLOW}SKIP${NC}  $1"; }

ERRORS=0

echo "=== NetClaw FRR Lab Verification ==="
echo ""

# --- Container health ---
echo "--- Container Status ---"
for c in netclaw-edge1 netclaw-core netclaw-edge2; do
  if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
    pass "$c running"
  else
    fail "$c not running"
  fi
done
echo ""

# --- OSPF convergence ---
echo "--- OSPF Neighbors ---"
EDGE1_OSPF=$(docker exec netclaw-edge1 vtysh -c "show ip ospf neighbor" 2>/dev/null || echo "")
if echo "$EDGE1_OSPF" | grep -q "Full"; then
  pass "Edge1 has OSPF Full adjacency"
else
  fail "Edge1 OSPF not converged"
fi

CORE_OSPF=$(docker exec netclaw-core vtysh -c "show ip ospf neighbor" 2>/dev/null || echo "")
CORE_FULL=$(echo "$CORE_OSPF" | grep -c "Full" || echo "0")
if [ "$CORE_FULL" -ge 2 ]; then
  pass "Core has $CORE_FULL OSPF Full adjacencies"
else
  fail "Core has only $CORE_FULL OSPF Full adjacencies (expected 2)"
fi
echo ""

# --- BGP convergence ---
echo "--- BGP Sessions ---"
CORE_BGP=$(docker exec netclaw-core vtysh -c "show bgp summary" 2>/dev/null || echo "")
if echo "$CORE_BGP" | grep -q "1.1.1.1"; then
  pass "Core sees Edge1 BGP peer"
else
  fail "Core missing Edge1 BGP peer"
fi
if echo "$CORE_BGP" | grep -q "3.3.3.3"; then
  pass "Core sees Edge2 BGP peer"
else
  fail "Core missing Edge2 BGP peer"
fi
echo ""

# --- GRE tunnel (optional, only if setup-gre.sh was run) ---
echo "--- GRE Tunnel (host side) ---"
if ip tunnel show gre-netclaw &>/dev/null; then
  pass "GRE tunnel gre-netclaw exists"
  if ping -c 1 -W 2 172.16.0.1 &>/dev/null; then
    pass "GRE tunnel reachable (172.16.0.1)"
  else
    fail "GRE tunnel unreachable"
  fi
else
  warn "GRE tunnel not configured (run scripts/setup-gre.sh)"
fi
echo ""

# --- eBGP to NetClaw (only if GRE is up) ---
echo "--- eBGP to NetClaw ---"
EDGE1_BGP=$(docker exec netclaw-edge1 vtysh -c "show bgp summary" 2>/dev/null || echo "")
if echo "$EDGE1_BGP" | grep -q "172.16.0.2"; then
  if echo "$EDGE1_BGP" | grep "172.16.0.2" | grep -qE "[0-9]+$"; then
    pass "Edge1 sees NetClaw eBGP peer at 172.16.0.2"
  else
    warn "Edge1 knows NetClaw peer but session not Established"
  fi
else
  warn "NetClaw eBGP peer not configured (GRE tunnel required)"
fi
echo ""

# --- Summary ---
echo "==========================="
if [ "$ERRORS" -eq 0 ]; then
  echo -e "${GREEN}All checks passed${NC}"
else
  echo -e "${RED}$ERRORS check(s) failed${NC}"
fi
exit "$ERRORS"
