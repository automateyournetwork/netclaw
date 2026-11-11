# Quickstart
```bash
python3 scripts/check-skill-limits.py            # passes on the shipped repo
python3 scripts/reconcile-mcp.py --surface skill-limits
python3 -m pytest tests/skill-limits -q
```
To add skills beyond the headroom: raise the limits in `config/skill-limits.json`, re-run the check, re-run the installer (raise-only applies the new values).
