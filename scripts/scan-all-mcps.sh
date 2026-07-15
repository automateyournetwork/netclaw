#!/bin/bash
# Scan all MCP servers configured in openclaw.json

CONFIG="$HOME/.openclaw/config/openclaw.json"
OUTPUT="${1:-DefenseClawMCPScan.md}"

echo "# DefenseClaw MCP Server Scan Report" > "$OUTPUT"
echo "" >> "$OUTPUT"
echo "Generated: $(date)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# Extract MCP server names from openclaw.json
SERVERS=$(python3 -c "import json; c=json.load(open('$CONFIG')); print('\n'.join(c.get('mcpServers', {}).keys()))")

TOTAL=0
CLEAN=0
WARNINGS=0
ERRORS=0

for server in $SERVERS; do
    echo "Scanning: $server"
    echo "## $server" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    
    # Run scan and capture output
    if result=$(defenseclaw mcp scan "$server" 2>&1); then
        echo "$result" >> "$OUTPUT"
        if echo "$result" | grep -q "No findings"; then
            ((CLEAN++))
        else
            ((WARNINGS++))
        fi
    else
        echo "Error scanning $server: $result" >> "$OUTPUT"
        ((ERRORS++))
    fi
    echo "" >> "$OUTPUT"
    ((TOTAL++))
done

echo "" >> "$OUTPUT"
echo "---" >> "$OUTPUT"
echo "## Summary" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "- Total servers scanned: $TOTAL" >> "$OUTPUT"
echo "- Clean: $CLEAN" >> "$OUTPUT"
echo "- With findings: $WARNINGS" >> "$OUTPUT"
echo "- Errors: $ERRORS" >> "$OUTPUT"

echo ""
echo "Done! Results saved to: $OUTPUT"
echo "Summary: $TOTAL scanned, $CLEAN clean, $WARNINGS warnings, $ERRORS errors"
