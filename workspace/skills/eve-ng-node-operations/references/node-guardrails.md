# Node guardrails

## Single-user rule
Do not start a lab if another lab is already running.

## Node-ID rule
Before creating nodes, verify the target lab's node-ID block is reserved and does not collide with other saved labs.

## Boot-state rule
After `eve_start_node`, the API may say `running` before the console is truly ready. Use console discovery before sending config commands.

## Missing-image rule
Before creating a node:
1. Check local images.
2. Check `ishare2` inventory if missing.
3. Offer exact matching image names.
4. Do not create placeholder nodes if the image dependency is unresolved.

## Destructive actions
Stop nodes before delete or wipe operations.
