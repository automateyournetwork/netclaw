# Plan

- `scripts/systemd/defenseclaw-sidecar.service`: `Type=forking`;
  `ExecStartPre=-defenseclaw-gateway stop` (take over a hand-started gateway);
  `ExecStart=` the helper; `ExecStop=defenseclaw-gateway stop`;
  `RuntimeDirectory=defenseclaw-sidecar`, `PIDFile=%t/defenseclaw-sidecar/gateway.pid`;
  `Restart=always`, `TimeoutStartSec=180`. Paths quoted.
- `scripts/systemd/defenseclaw-sidecar-start.py` (new): runs `defenseclaw-gateway
  start`, reads the `pid` from `$DEFENSECLAW_HOME/gateway.pid` (default
  `~/.defenseclaw`), writes it to `$RUNTIME_DIRECTORY/gateway.pid`. Never touches
  DefenseClaw's record. Fails if `start` fails or the record is unusable.
- `scripts/in2n-services.py`: substitute the Python and helper paths.
- Docs: `docs/DEFENSECLAW.md` (status check, update steps, other service managers),
  `docs/N2N-RISK.md` operational note. Release 1.18.7.
