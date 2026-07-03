# Console guardrails

## Prompt/state rule
Always determine whether you landed in login, shell, exec, privileged, config, or OS-specific modes. Do not assume the mode from node type alone.

## Boot-state rule
After `eve_start_node`, a node may report `running` while still booting. Use console discovery before sending CLI commands.

## Live-change rule
Do not reboot a node as the default way to apply a live console change.

### Junos live-change flow
1. Enter `configure`
2. Apply candidate changes
3. `commit`
4. Inspect commit output directly in the transcript
5. Verify there is no commit error or rejected statement
6. Run post-change verification commands

## Timeout tuning
Increase `command_timeout`, `wait`, `dhcp_timeout`, or `prompt_timeout` for slow VMs or overloaded hosts.
