#!/bin/bash
# Sync new MCP servers, specs, and skills from upstream without touching
# personality files (SOUL.md, USER.md, TOOLS.md, AGENTS.md, etc.)
#
# This lets you pull new tools as they're contributed to the upstream netclaw
# repo while keeping your local personality/config customizations intact.
#
# Usage: bash scripts/sync-upstream-tools.sh

set -e
cd "$(dirname "$0")/.."

echo "Fetching upstream..."
git fetch upstream

echo ""
echo "=== New MCP servers (upstream has, you don't) ==="
comm -23 \
  <(git ls-tree --name-only upstream/main mcp-servers/ | sort) \
  <(ls -d mcp-servers/*/ 2>/dev/null | sed 's|/$||' | sort)

echo ""
echo "=== New specs ==="
comm -23 \
  <(git ls-tree --name-only upstream/main specs/ | sort) \
  <(ls -d specs/*/ 2>/dev/null | sed 's|/$||' | sort)

echo ""
echo "=== New skills ==="
comm -23 \
  <(git ls-tree --name-only upstream/main workspace/skills/ | sort) \
  <(ls -d workspace/skills/*/ 2>/dev/null | sed 's|/$||' | sort)

echo ""
read -p "Pull all new items? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

# Pull new MCP servers
for dir in $(comm -23 \
  <(git ls-tree --name-only upstream/main mcp-servers/ | sort) \
  <(ls -d mcp-servers/*/ 2>/dev/null | sed 's|/$||' | sort)); do
    echo "  Pulling $dir/"
    git checkout upstream/main -- "$dir/"
done

# Pull new specs
for dir in $(comm -23 \
  <(git ls-tree --name-only upstream/main specs/ | sort) \
  <(ls -d specs/*/ 2>/dev/null | sed 's|/$||' | sort)); do
    echo "  Pulling $dir/"
    git checkout upstream/main -- "$dir/"
done

# Pull new skills
for dir in $(comm -23 \
  <(git ls-tree --name-only upstream/main workspace/skills/ | sort) \
  <(ls -d workspace/skills/*/ 2>/dev/null | sed 's|/$||' | sort)); do
    echo "  Pulling $dir/"
    git checkout upstream/main -- "$dir/"
done

echo ""
echo "Done. New files staged. Review with 'git status' and commit when ready."
