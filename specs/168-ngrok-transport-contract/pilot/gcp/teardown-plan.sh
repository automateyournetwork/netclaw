#!/usr/bin/env bash
# Prepare an exact destroy plan for owner review. This script never applies it.
set -euo pipefail
umask 077
if [[ $# -ne 4 ]]; then
  echo "Usage: $0 TOFU PRIVATE_STATE PRIVATE_TFVARS PRIVATE_PLAN_OUTPUT" >&2
  exit 2
fi
for value in "$@"; do
  [[ "$value" == /* ]] || { echo 'Use explicit absolute paths' >&2; exit 2; }
done
[[ -f "$2" && -f "$3" && ! -e "$4" ]] || {
  echo 'Existing state/tfvars and a new output path are required' >&2; exit 2;
}
module_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
# Token stays in the child environment, never printed or persisted in source.
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"
"$1" -chdir="$module_dir" plan -destroy -input=false -no-color \
  -state="$2" -var-file="$3" -out="$4"
echo 'Review the saved plan, retained evidence and secret disposition. No deletion was performed.'
