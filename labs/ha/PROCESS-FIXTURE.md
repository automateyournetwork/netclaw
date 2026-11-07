# R08 process restart fixture

`process_fixture.py` is coordinator-only qualification source. Import and protocol
tests launch nothing. The actual driver launches three separate production
ClusterNode processes and a fourth process containing production MemberAttachments
and MemberAdmission. All use existing authenticated NCFED cluster and iN2N paths
against the exact owned voters. Only the callback is controlled: model and native
tool counters remain zero. This does not qualify guarded runtime, signed-result,
browser/editor/Mobile, geographic or Raft partition behavior by itself.

Use a reviewed, running, healthy owned EtcdLab with its signed cluster identity
and separate transport certificates. No other harness may hold those cluster or
iN2N ports. Keep the source closure fixed during the run. The driver verifies the
owned voter inventory before creating workers and never replaces occupied ports
or existing identities. Its evidence directory must be a fresh absolute path
under an owned private parent; everything retained is0700/0600.

The coordinator runs, with the selected qualified protocol Python:

```text
python -I -B labs/ha/process_fixture.py run \
  --fixture /absolute/owned/etcd-fixture \
  --evidence /absolute/private/fresh-process-evidence \
  --allow-owned-voter-restart
```

The last flag delegates the existing OwnedVoterRestart helper after a durable,
quorum-consistent snapshot and after all four workers are stopped. It performs
the exact owned voter stop/start sequence; it never creates/replaces voters or
clears state. Without the flag, the process-only run explicitly reports
`full_voter_restart_qualified:false`. That result cannot close the full restart
row. Only the coordinator executes either form; this source lane has run neither.

The bounded sequence is:

1. Record source, Python, command, PID, boot/incarnation and private socket
   identities; start the three Borders and verify the complete NCFED mesh.
2. Enroll a fresh controlled member and verify its actual outbound attachments to
   all three Borders. Create one original approved/dispatched operation. Admit
   model1 through a follower, requiring real cluster forwarding.
3. SIGKILL the actual elected Border PID, observe a different elected survivor,
   and admit model2 through the surviving follower. Kill that elected Border,
   elect the final survivor, then enter the original tool1 controlled callback.
4. Hold that callback after its durable effect record; SIGKILL the member. Retain
   the consumed journal claim and mark the original quorum operation unknown.
   Export the actual snapshot, then kill the final elected Border. Each fault has
   an exclusive durable claim and an independently observed process exit code.
5. Optionally restart the exact owned voters. Restart all original worker homes,
   keys and identities; verify different PIDs/incarnations, all three attachments,
   identical original journal/effect digests and the original unknown operation.
6. Prove the original tool claim cannot run again and a new operation ID cannot
   bypass the original member/runner reservation. No extra callback may occur.

Control uses a dedicated fresh `/tmp/nc179-*` directory (0700) and0600 Unix sockets
to avoid the Mac socket path-length limit. A per-boot private capability and exact
run/request identity protect the bounded JSON protocol. The allowlist contains
status, fixture enrollment/preparation, dispatch, original lookup/snapshot,
unknown marking and one controlled admission; there is no shell/general exec,
arbitrary destination or product MCP endpoint. Every mutation request claims its
original ID before handling; lost replies are not retried. Member configuration
contains its own key and public trust only, with no consensus credentials.

The coordinator has a480s overall bound; workers stop if their coordinator dies
or after600s. RPC, admission callback and shutdown waits are separately bounded.
Cleanup stops only owned worker processes and removes only their recorded socket
inodes. Voters are preserved. Complete evidence is written after process cleanup;
failures retain their one-shot claims, original IDs and private artifacts for
inspection. Source tests and a successful help command are not execution evidence.
