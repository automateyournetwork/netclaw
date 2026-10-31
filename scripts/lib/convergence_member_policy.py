"""Native OpenClaw policy for a focused Convergence evidence member.

This configures tool restrictions and workspace reads. It does not claim OS
confinement or grant the Border's other investigation capabilities to the member.
"""


def native_tool_policy():
    return {
        'allow': ['read', 'convergence-read-mcp__convergence_flow_summary',
                  'convergence-read-mcp__convergence_flow_evidence'],
        'deny': ['exec', 'write', 'edit', 'apply_patch', 'browser'],
        'fs': {'workspaceOnly': True},
        'elevated': {'enabled': False},
        'toolSearch': False,
    }
