# Contract: Risk Posture (status surface)

The Border's truthful production/degraded/testing report. Exposed three ways (FR-003): the `n2n-mcp` status tool, the operator heartbeat, and the HUD. This is an **internal** contract — it does not cross the iN2N/eN2N wire (R8).

## Python (`posture.py`)

```python
def compute_posture(service) -> dict:
    """Return the current RiskPosture (data-model §1). Pure of side effects
    beyond reading control probes (which are cached ~3s in controls.py)."""

def posture_ok_for_delegation(posture: dict, *, strict_all: bool) -> dict:
    """Preflight decision for FR-019/020.
    Returns {"allow": bool, "enforcement": "enforced"|"audit-degraded"|"refused",
             "refused_control": str|None, "reason": str}.
    - containment gap (sandbox/model-guard missing) -> allow=False, refused
    - audit gap only (gait missing) -> allow=True, enforcement=audit-degraded
    - strict_all and any gap -> allow=False, refused
    - all present -> allow=True, enforcement=enforced"""
```

## Posture object (JSON, returned by the status tool)

```json
{
  "mode": "production",
  "state": "degraded",
  "controls": [
    {"name": "sandbox",     "kind": "containment", "available": true,  "detail": ""},
    {"name": "model-guard", "kind": "containment", "available": false, "detail": "defenseclaw proxy unreachable"},
    {"name": "audit",       "kind": "audit",       "available": true,  "detail": ""}
  ],
  "missing": ["model-guard"],
  "strict_all": false,
  "computed_at": 1752422400.0,
  "summary": "production — DEGRADED (model-guard missing)"
}
```

- `state == "enforced"` **requires** `mode=="production"` and all `controls[].available` true (FR-002).
- `state == "testing"` when `mode=="testing"` (no false production claim, FR-006).
- `summary` is the human string the heartbeat/HUD show verbatim.

## MCP tool (extends existing `n2n-mcp` status)

`n2n_status` (or a new `n2n_posture`) returns the posture object above alongside the existing status payload. No new server; extend the existing FastMCP tool (Constitution V).

## Acceptance mapping

- FR-001/002/003, SC-001: with any one control `available:false` in production, `state` is `degraded` and `missing` names it; never `enforced`.
