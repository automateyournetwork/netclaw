#!/bin/bash
# Scan MCP server source code (static analysis) without running the servers

OUTPUT="${1:-DefenseClawMCPScan.md}"
MCP_DIR="mcp-servers"
cd "$(dirname "$0")/.." || exit 1

echo "# DefenseClaw MCP Source Code Scan Report" > "$OUTPUT"
echo "Generated: $(date)" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "Scanning MCP server source files (static analysis)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

TOTAL=0
CLEAN=0
WARNINGS=0
ERRORS=0

for server_dir in "$MCP_DIR"/*/; do
    [ -d "$server_dir" ] || continue
    name=$(basename "$server_dir")
    
    echo "Scanning: $name"
    echo "## $name" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo '```' >> "$OUTPUT"
    
    # Count Python files
    py_count=$(find "$server_dir" -name "*.py" 2>/dev/null | wc -l)
    
    if [ "$py_count" -eq 0 ]; then
        echo "No Python files found" >> "$OUTPUT"
        echo '```' >> "$OUTPUT"
        echo "" >> "$OUTPUT"
        continue
    fi
    
    echo "Files: $py_count Python files" >> "$OUTPUT"
    
    # Run skill scanner on directory (it will scan all source files)
    if result=$(defenseclaw skill scan "$server_dir" --json 2>&1); then
        # Parse JSON result
        echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    findings = data.get('findings', [])
    if not findings:
        print('Verdict: CLEAN')
        print('No security findings')
    else:
        for f in findings:
            sev = f.get('severity', '?')
            title = f.get('title', f.get('id', '?'))
            loc = f.get('location', '')
            print(f'[{sev}] {title}')
            if loc:
                print(f'  at {loc}')
except:
    print(sys.stdin.read())
" >> "$OUTPUT" 2>&1
        ((CLEAN++))
    else
        # Fall back to basic grep check for common issues
        echo "Scanning with grep patterns..." >> "$OUTPUT"
        
        # Check for common security issues
        issues=0
        
        if grep -rn "os\.system\|subprocess.*shell=True\|eval(" "$server_dir"/*.py 2>/dev/null; then
            echo "[WARN] Potential shell/eval usage found" >> "$OUTPUT"
            ((issues++))
        fi
        
        if grep -rn "password.*=.*['\"]" "$server_dir"/*.py 2>/dev/null | grep -v "password.*=.*\$" | head -3; then
            echo "[WARN] Potential hardcoded password" >> "$OUTPUT"
            ((issues++))
        fi
        
        if [ "$issues" -eq 0 ]; then
            echo "Basic scan: No obvious issues found" >> "$OUTPUT"
            ((CLEAN++))
        else
            ((WARNINGS++))
        fi
    fi
    
    echo '```' >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    ((TOTAL++))
done

echo "---" >> "$OUTPUT"
echo "## Summary" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "- Total MCP servers scanned: $TOTAL" >> "$OUTPUT"
echo "- Clean: $CLEAN" >> "$OUTPUT"
echo "- With warnings: $WARNINGS" >> "$OUTPUT"
echo "- Errors: $ERRORS" >> "$OUTPUT"

echo ""
echo "Done! Results saved to: $OUTPUT"
echo "Summary: $TOTAL scanned, $CLEAN clean, $WARNINGS warnings"
