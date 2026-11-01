# Plan

T001 Reproduce on the operator Risk (OpenClaw 2026.10.6, system member units): routed
task per member; capture the CLI reason outside and inside the unit sandbox.
T002 `gateway.py`: on the embedded path, pass `--agent main` when the home's config
lists several agents including `main`, or `--agent $N2N_MEMBER_AGENT`; otherwise keep
the unnamed command. Surface the CLI's structured error message on failure. Tests for
each config shape, override and error detail.
T003 `install-steps.sh` `core_deploy`: replace a bootstrap-file symlink that resolves
inside `$NETCLAW_DIR` with a copy (portable: Python realpath, copy then rename);
preserve everything else. Test in `tests/unit/test_core_deploy_preservation.py`.
T004 Live verification: routed task per member on 2026.10.6 and after the upgrade to
2026.10.9; a no-entries home on 2026.10.9; bootstrap warnings gone. Docs, release
1.18.1, PR.
