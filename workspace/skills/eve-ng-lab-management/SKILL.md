---
name: eve-ng-lab-management
description: Manage EVE-NG labs and platform inventory. Use when listing labs, checking lab metadata, creating or deleting labs, importing or exporting lab archives, checking EVE-NG health or auth, or verifying available node images before build work.
user-invocable: true
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["EVE_URL","EVE_USER","EVE_PASSWORD"]}}}
---

# EVE-NG Lab Management

Use this skill for **lab inventory, lifecycle, health, and image checks**.

## Workflow

1. Use `eve_status` and `eve_auth` to verify platform state when needed.
2. Use `eve_list_labs` / `eve_get_lab` for lab discovery and metadata.
3. Before creating, starting, or deleting labs, apply `{baseDir}/references/operational-guardrails.md`.
4. For image questions, follow `{baseDir}/references/image-and-pagination.md`.
5. For import/export work, use native lab ZIP workflows first.

## Available tools

- `eve_status`
- `eve_auth`
- `eve_list_images`
- `eve_list_labs`
- `eve_get_lab`
- `eve_create_lab`
- `eve_delete_lab`
- `eve_export_lab`
- `eve_import_lab`

## Notes

- Lab paths should include the folder prefix, for example `/Labs/BGP.unl`.
- `.unl` is added automatically if omitted.
- ZIP lab export includes the lab package, not node images.
