# Quickstart

```bash
gcloud auth login && gcloud config set project MY_PROJECT
python3 scripts/netclaw-gcp.py plan --topology gcp-border --project MY_PROJECT --region us-central1 --ack-no-auth
python3 scripts/netclaw-gcp.py apply --plan-sha256 <sha> --confirm-cost
python3 scripts/netclaw-gcp.py status --deployment <id>
python3 scripts/netclaw-gcp.py teardown --deployment <id>            # lists
python3 scripts/netclaw-gcp.py teardown --deployment <id> --confirm-list-sha256 <sha>
```
Or choose "Deploy to GCP" in `scripts/install.sh`, or the VS Code "NetClaw: Deploy to GCP" command.
