#!/bin/bash
# Scan MCP server source files directly with CodeGuard

OUTPUT="${1:-DefenseClawMCPScan.md}"
MCP_DIR="mcp-servers"

echo "# DefenseClaw MCP Server Scan Report" > "$OUTPUT"
echo "Generated: $(date)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for server_dir in "$MCP_DIR"/*/; do
    name=$(basename "$server_dir")
    echo "Scanning: $name"
    echo "## $name" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    
    # Find Python files and scan with codeguard
    if result=$(defenseclaw codeguard scan "$server_dir" 2>&1); then
        echo '```' >> "$OUTPUT"
        echo "$result" >> "$OUTPUT"
        echo '```' >> "$OUTPUT"
    else
        echo "Error: $result" >> "$OUTPUT"
    fi
    echo "" >> "$OUTPUT"
done

echo "Done! Results saved to: $OUTPUT"
