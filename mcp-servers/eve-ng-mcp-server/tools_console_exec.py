"""Console execution (6) MCP tools — telnet-based command execution per OS."""

import os

from mcp_init import mcp
from eve_client import (
    get_client, EVEError, handle_eve_response, success_response, error_response,
    with_gait_logging, normalize_lab_path, resolve_node_id, node_is_running,
    get_console_port,
)
from eve_console import (
    TelnetSession, VPCS_PROMPT_RE,
    bootstrap_ios, ensure_ios_privileged, ensure_ios_config, run_ios_command, detect_ios_mode,
    ensure_junos_operational, run_junos_command, detect_junos_mode,
    ensure_eos_privileged, ensure_eos_config, run_eos_command, detect_eos_mode,
    ensure_nxos_privileged, ensure_nxos_config, run_nxos_command, detect_nxos_mode,
)

EVE_CONSOLE_HOST = os.getenv("EVE_CONSOLE_HOST", "127.0.0.1")


@mcp.tool()
@with_gait_logging("eve_discover_node")
def eve_discover_node(lab_path: str, node: str) -> str:
    """
    Resolve a node by name or ID and return its console connection details.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name (e.g. 'R1') or numeric ID
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        data = handle_eve_response(c.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}"))
        port = get_console_port(c, lab_path, node_id)
        return success_response({
            "node_id": node_id,
            "name": data.get("name") if isinstance(data, dict) else node,
            "type": data.get("type") if isinstance(data, dict) else None,
            "status": data.get("status") if isinstance(data, dict) else None,
            "running": node_is_running(data) if isinstance(data, dict) else None,
            "console_host": EVE_CONSOLE_HOST,
            "console_port": port,
            "telnet": f"telnet://{EVE_CONSOLE_HOST}:{port}",
        })
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_exec_ios")
def eve_exec_ios(
    lab_path: str,
    node: str,
    commands: list[str],
    config_mode: bool = False,
    save: bool = False,
    command_timeout: float = 15.0,
    wait: float = 0.8,
) -> str:
    """
    Execute commands on an IOS / IOL / IOS-XE node via telnet console.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        commands: Commands to run (e.g. ['show ip route', 'show interfaces'])
        config_mode: Enter global config mode before running (for config commands)
        save: Run 'write memory' after all commands
        command_timeout: Seconds to wait for each command's output (default 15)
        wait: Inter-command pause in seconds (default 0.8)
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        port = get_console_port(c, lab_path, node_id)
        transcript: list = []
        with TelnetSession(EVE_CONSOLE_HOST, port) as sess:
            transcript.extend(bootstrap_ios(sess))
            if config_mode:
                transcript.extend(ensure_ios_config(sess))
            else:
                transcript.extend(ensure_ios_privileged(sess))
            for cmd in commands:
                out = run_ios_command(sess, cmd, wait=wait, timeout=command_timeout)
                transcript.append({"command": cmd, "output": out, "mode_after": detect_ios_mode(out)})
            transcript.extend(ensure_ios_privileged(sess))
            if save:
                out = sess.send("write memory", wait=2.0)
                transcript.append({"command": "write memory", "output": out,
                                   "mode_after": detect_ios_mode(out)})
        return success_response({"node_id": node_id, "node": node,
                                  "config_mode": config_mode, "saved": save,
                                  "transcript": transcript})
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_exec_junos")
def eve_exec_junos(
    lab_path: str,
    node: str,
    commands: list[str],
    command_timeout: float = 15.0,
    wait: float = 0.8,
) -> str:
    """
    Execute operational mode commands on a Junos node via telnet console.
    'show' commands get '| no-more' appended automatically.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        commands: Junos operational commands (e.g. ['show route', 'show interfaces terse'])
        command_timeout: Seconds to wait for each command's output (default 15)
        wait: Not used for Junos (prompt-based timing), kept for API consistency
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        port = get_console_port(c, lab_path, node_id)
        transcript: list = []
        with TelnetSession(EVE_CONSOLE_HOST, port) as sess:
            transcript.extend(ensure_junos_operational(sess))
            for cmd in commands:
                out = run_junos_command(sess, cmd, timeout=command_timeout)
                transcript.append({"command": cmd, "output": out, "mode_after": detect_junos_mode(out)})
        return success_response({"node_id": node_id, "node": node, "transcript": transcript})
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_exec_vpcs")
def eve_exec_vpcs(
    lab_path: str,
    node: str,
    commands: list[str],
    command_timeout: float = 8.0,
    dhcp_timeout: float = 10.0,
    prompt_timeout: float = 5.0,
) -> str:
    """
    Execute commands on a VPCS node via telnet console.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        commands: VPCS commands (e.g. ['ip dhcp', 'show ip', 'ping 10.0.0.1'])
        command_timeout: Seconds to wait for command output
        dhcp_timeout: Extra wait seconds for 'ip dhcp' command
        prompt_timeout: Seconds to wait for initial VPCS> prompt
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        port = get_console_port(c, lab_path, node_id)
        transcript: list = []
        with TelnetSession(EVE_CONSOLE_HOST, port) as sess:
            banner = sess.recv_until(VPCS_PROMPT_RE, timeout=prompt_timeout)
            if not VPCS_PROMPT_RE.search(banner):
                banner += sess.send("", wait=0.8)
            transcript.append({"command": None, "output": banner})
            for cmd in commands:
                timeout = dhcp_timeout if cmd.strip() == "ip dhcp" else command_timeout
                out = sess.send_until(cmd, VPCS_PROMPT_RE, timeout=timeout)
                transcript.append({"command": cmd, "output": out})
        return success_response({"node_id": node_id, "node": node, "transcript": transcript})
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_exec_eos")
def eve_exec_eos(
    lab_path: str,
    node: str,
    commands: list[str],
    config_mode: bool = False,
    save: bool = False,
    command_timeout: float = 15.0,
    wait: float = 0.8,
) -> str:
    """
    Execute commands on an Arista EOS node via telnet console.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        commands: EOS commands (e.g. ['show ip bgp summary', 'show interfaces status'])
        config_mode: Enter global config mode before running
        save: Run 'copy running-config startup-config' after commands
        command_timeout: Seconds to wait for each command's output
        wait: Inter-command pause in seconds
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        port = get_console_port(c, lab_path, node_id)
        transcript: list = []
        with TelnetSession(EVE_CONSOLE_HOST, port) as sess:
            if config_mode:
                transcript.extend(ensure_eos_config(sess))
            else:
                transcript.extend(ensure_eos_privileged(sess))
            for cmd in commands:
                out = run_eos_command(sess, cmd, wait=wait, timeout=command_timeout)
                transcript.append({"command": cmd, "output": out, "mode_after": detect_eos_mode(out)})
            transcript.extend(ensure_eos_privileged(sess))
            if save:
                out = sess.send("copy running-config startup-config", wait=3.0)
                transcript.append({"command": "copy running-config startup-config", "output": out,
                                   "mode_after": detect_eos_mode(out)})
        return success_response({"node_id": node_id, "node": node,
                                  "config_mode": config_mode, "saved": save,
                                  "transcript": transcript})
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)


@mcp.tool()
@with_gait_logging("eve_exec_nxos")
def eve_exec_nxos(
    lab_path: str,
    node: str,
    commands: list[str],
    config_mode: bool = False,
    save: bool = False,
    command_timeout: float = 15.0,
    wait: float = 0.8,
) -> str:
    """
    Execute commands on a Cisco NX-OS node via telnet console.

    Args:
        lab_path: Lab path like '/Labs/demo.unl'
        node: Node name or numeric ID
        commands: NX-OS commands (e.g. ['show ip route', 'show vlan brief'])
        config_mode: Enter global config mode before running
        save: Run 'copy running-config startup-config' after commands
        command_timeout: Seconds to wait for each command's output
        wait: Inter-command pause in seconds
    """
    try:
        c = get_client()
        node_id = resolve_node_id(c, lab_path, node)
        port = get_console_port(c, lab_path, node_id)
        transcript: list = []
        with TelnetSession(EVE_CONSOLE_HOST, port) as sess:
            if config_mode:
                transcript.extend(ensure_nxos_config(sess))
            else:
                transcript.extend(ensure_nxos_privileged(sess))
            for cmd in commands:
                out = run_nxos_command(sess, cmd, wait=wait, timeout=command_timeout)
                transcript.append({"command": cmd, "output": out, "mode_after": detect_nxos_mode(out)})
            transcript.extend(ensure_nxos_privileged(sess))
            if save:
                out = sess.send("copy running-config startup-config", wait=3.0)
                transcript.append({"command": "copy running-config startup-config", "output": out,
                                   "mode_after": detect_nxos_mode(out)})
        return success_response({"node_id": node_id, "node": node,
                                  "config_mode": config_mode, "saved": save,
                                  "transcript": transcript})
    except EVEError as e:
        return error_response(e)
    except Exception as e:
        return error_response(e)
