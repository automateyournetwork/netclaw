"""Alert workflow tools — labels and assignees (ITSM-gated writes).

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/user-actions/labels/set       -> label_alerts (write, add/remove labels)
  POST /api/v1/user-actions/labels/replace   -> label_alerts (replace=True)
  POST /api/v1/user-actions/assignees/set    -> assign_alerts (write, add/remove assignees)

The xDome ``target_specification`` accepts ``alert_ids`` + ``target_type``
for alert-scoped operations. ``labels_to_add`` / ``labels_to_remove``
and ``usernames_to_add`` / ``usernames_to_remove`` /
``group_names_to_add`` / ``group_names_to_remove`` are list-typed and
optional individually but at least one must be non-empty.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from utils.itsm_gate import validate_change_request
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import ENDPOINTS

logger = logging.getLogger("claroty-mcp.user_actions")


async def label_alerts(
    alert_ids: list,
    cr_number: str,
    labels_to_add: Optional[list[str]] = None,
    labels_to_remove: Optional[list[str]] = None,
    replace: bool = False,
) -> str:
    """Add, remove, or replace labels on a batch of alerts (ITSM-gated write).

    Args:
        alert_ids: One or more alert ids.
        cr_number: ServiceNow CR (``CHG\\d+``) authorising the change.
        labels_to_add: Labels to apply.
        labels_to_remove: Labels to remove.
        replace: When True, route to the ``/replace`` endpoint instead of
            ``/set`` (which replaces the full label set on the targeted
            alerts rather than incrementally adding/removing).
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not alert_ids:
        return json.dumps({"error": "alert_ids is required"}, indent=2)
    if not labels_to_add and not labels_to_remove:
        return json.dumps(
            {"error": "Provide at least one of labels_to_add or labels_to_remove"},
            indent=2,
        )

    endpoint = ENDPOINTS["replace_labels"] if replace else ENDPOINTS["set_labels"]
    body: dict = {
        "target_specification": {
            "alert_ids": list(alert_ids),
            "target_type": "alert",
        },
    }
    if labels_to_add:
        body["labels_to_add"] = list(labels_to_add)
    if labels_to_remove:
        if replace:
            # PublicLabelsReplace only has target_specification + labels_to_add.
            # Passing labels_to_remove here would either be silently dropped
            # or rejected by xDome; surface the conflict to the caller.
            logger.warning(
                "label_alerts: labels_to_remove is ignored when replace=True "
                "(the /replace endpoint sets the full label set to labels_to_add only)"
            )
        else:
            body["labels_to_remove"] = list(labels_to_remove)
    try:
        raw = await client.post(endpoint, body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("label_alerts failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )


async def assign_alerts(
    alert_ids: list,
    cr_number: str,
    usernames_to_add: Optional[list[str]] = None,
    group_names_to_add: Optional[list[str]] = None,
    usernames_to_remove: Optional[list[str]] = None,
    group_names_to_remove: Optional[list[str]] = None,
) -> str:
    """Assign / unassign a batch of alerts to users or groups (ITSM-gated write).

    Args:
        alert_ids: One or more alert ids.
        cr_number: ServiceNow CR authorising the change.
        usernames_to_add: Individual usernames to assign.
        group_names_to_add: Group names to assign.
        usernames_to_remove: Individual usernames to unassign.
        group_names_to_remove: Group names to unassign.

    At least one of the four list parameters must be non-empty.
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not alert_ids:
        return json.dumps({"error": "alert_ids is required"}, indent=2)
    if not any([usernames_to_add, group_names_to_add, usernames_to_remove, group_names_to_remove]):
        return json.dumps(
            {
                "error": "Provide at least one of usernames_to_add, group_names_to_add, "
                "usernames_to_remove, group_names_to_remove"
            },
            indent=2,
        )

    body: dict = {
        "target_specification": {
            "alert_ids": list(alert_ids),
            "target_type": "alert",
        },
    }
    if usernames_to_add:
        body["usernames_to_add"] = list(usernames_to_add)
    if group_names_to_add:
        body["group_names_to_add"] = list(group_names_to_add)
    if usernames_to_remove:
        body["usernames_to_remove"] = list(usernames_to_remove)
    if group_names_to_remove:
        body["group_names_to_remove"] = list(group_names_to_remove)
    try:
        raw = await client.post(ENDPOINTS["set_assignees"], body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("assign_alerts failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )
