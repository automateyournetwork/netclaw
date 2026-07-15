"""Job runner — trigger Nautobot golden config jobs and poll until complete."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

from nautobot_client import NautobotClient, NautobotError

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.environ.get("GOLDEN_CONFIG_POLL_INTERVAL", "5"))
JOB_TIMEOUT = int(os.environ.get("GOLDEN_CONFIG_JOB_TIMEOUT", "300"))

# Golden config job class paths
JOB_INTENDED = "nautobot_golden_config.jobs.IntendedJob"
JOB_BACKUP = "nautobot_golden_config.jobs.BackupJob"
JOB_COMPLIANCE = "nautobot_golden_config.jobs.ComplianceJob"
JOB_DEPLOY = "nautobot_golden_config.jobs.DeployConfigPlans"

# Fallback: match by job name substring
_JOB_NAME_MAP = {
    JOB_INTENDED: "Generate Intended Configurations",
    JOB_BACKUP: "Backup Configurations",
    JOB_COMPLIANCE: "Perform Configuration Compliance",
    JOB_DEPLOY: "Deploy Config Plans",
}


async def find_job_id(client: NautobotClient, class_path: str) -> Optional[str]:
    """Find a job UUID by its class_path or name."""
    resp = await client.rest_get("extras/jobs", {"limit": 200})
    jobs = resp.get("results", [])

    # Try exact class_path match first
    for job in jobs:
        if job.get("class_path") == class_path:
            return job["id"]

    # Try module_name match
    module = class_path.rsplit(".", 1)[0] if "." in class_path else class_path
    class_name = class_path.rsplit(".", 1)[-1] if "." in class_path else ""
    for job in jobs:
        if module in (job.get("module_name", "") or ""):
            if class_name.lower() in (job.get("name", "") or "").lower().replace(" ", ""):
                return job["id"]

    # Fallback: match by known job name
    expected_name = _JOB_NAME_MAP.get(class_path, "")
    if expected_name:
        for job in jobs:
            if job.get("name") == expected_name:
                return job["id"]

    return None


async def run_job_and_wait(
    client: NautobotClient,
    class_path: str,
    data: Optional[dict] = None,
    timeout: int = JOB_TIMEOUT,
) -> dict[str, Any]:
    """Trigger a Nautobot job by class_path and poll until complete."""
    job_id = await find_job_id(client, class_path)
    if not job_id:
        raise NautobotError(f"Job '{class_path}' not found. Is the golden config plugin installed and jobs enabled?")

    payload = {"data": data or {}}
    result = await client.rest_post(f"extras/jobs/{job_id}/run", payload)

    # Extract job result ID
    job_result_id = None
    if isinstance(result, dict):
        # Could be nested under "job_result" or at top level
        jr = result.get("job_result") or result
        job_result_id = jr.get("id") if isinstance(jr, dict) else result.get("id")

    if not job_result_id:
        return {"status": "triggered", "raw": result}

    # Poll until complete
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        jr = await client.rest_get(f"extras/job-results/{job_result_id}")
        status_val = jr.get("status")
        if isinstance(status_val, dict):
            status_val = status_val.get("value", status_val.get("label", ""))

        if status_val in ("completed", "SUCCESS"):
            return {
                "status": "completed",
                "id": job_result_id,
                "result": jr.get("result"),
                "completed": jr.get("date_done"),
            }
        elif status_val in ("failed", "FAILURE", "errored"):
            return {
                "status": "failed",
                "id": job_result_id,
                "result": jr.get("result"),
                "traceback": jr.get("traceback"),
            }

    return {"status": "timeout", "id": job_result_id, "elapsed": elapsed}
