# Azure driver for ha-cloud.sh (sourced). One resource group per phase; everything tagged netclaw-spec=198 phase=<id>.
# Management: SSH key auth to the public IP, allowed only from R10_SSH_ALLOW_CIDR (no Bastion, see research R3).
AZ_SSH_USER="${AZ_SSH_USER:-ncadmin}"
AZ_SSH_KEY="${AZ_SSH_KEY:-$HOME/.ssh/id_ed25519}"
AZ_IMAGE="${AZ_IMAGE:-Canonical:ubuntu-24_04-lts:server:latest}"
az_ssh_options() {
  if [ -n "${R10_SSH_KNOWN_HOSTS:-}" ]; then
    AZ_SSH_OPTIONS=(-o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$R10_SSH_KNOWN_HOSTS" -o GlobalKnownHostsFile=/dev/null)
  else
    AZ_SSH_OPTIONS=(-o StrictHostKeyChecking=accept-new)
  fi
}
az_region() { case "$1" in nne1) echo "${R10_AZ_REGION_NNE1:-canadacentral}";; ew1) echo "${R10_AZ_REGION_EW1:-westeurope}";; ase1) echo "${R10_AZ_REGION_ASE1:-southeastasia}";; *) echo "unknown code $1" >&2; return 2;; esac; }
az_cidr() { case "$1" in nne1) echo 10.198.1.0/24;; ew1) echo 10.198.2.0/24;; ase1) echo 10.198.3.0/24;; *) return 2;; esac; }
az_rg() { echo "rg-nc198-$1"; }
az_vm() { echo "nc198-$1-$2"; }
az_ssh_cidr() { if [ -n "${R10_SSH_ALLOW_CIDR:-}" ]; then echo "$R10_SSH_ALLOW_CIDR"; elif [ "$HA_DRY" = 1 ]; then echo "<owner-ip>/32"; else echo "R10_SSH_ALLOW_CIDR is required (owner public IP /32)" >&2; return 2; fi; }
az_tags() { echo "netclaw-spec=198 phase=$1${R10_RUN_ID:+ run-id=$R10_RUN_ID}"; }
cloud_up() { # <phase> <code> <region-override|-> <size>
  local phase="$1" code="$2" region="${3:--}" size="${4:-Standard_B2s}"
  [ "$region" = "-" ] && region="$(az_region "$code")"
  local rg vm cidr ssh https; rg="$(az_rg "$phase")"; vm="$(az_vm "$phase" "$code")"; cidr="$(az_cidr "$code")"
  ssh="$(az_ssh_cidr)"; https="${R10_HTTPS_ALLOW_CIDR:-$ssh}"
  # The group keeps its first region; later nodes in other regions reuse it (az rejects a re-create at another location).
  if [ "$HA_DRY" = 1 ] || [ "$(az group exists --name "$rg")" = "false" ]; then
    run az group create --name "$rg" --location "$region" --tags $(az_tags "$phase") --output none
  fi
  run az network vnet create -g "$rg" -n "vnet-$vm" -l "$region" --address-prefixes "$cidr" --subnet-name default --subnet-prefixes "$cidr" --tags $(az_tags "$phase") --output none
  run az network nsg create -g "$rg" -n "nsg-$vm" -l "$region" --tags $(az_tags "$phase") --output none
  run az network nsg rule create -g "$rg" --nsg-name "nsg-$vm" -n ssh-owner --priority 100 --access Allow --protocol Tcp --destination-port-ranges 22 --source-address-prefixes "$ssh" --output none
  run az network nsg rule create -g "$rg" --nsg-name "nsg-$vm" -n https-owner --priority 110 --access Allow --protocol Tcp --destination-port-ranges 443 --source-address-prefixes "$https" --output none
  # Public federation ingress is limited to the operator until explicit peers are added.
  # Private etcd/cluster traffic uses VNet peering and Azure's VirtualNetwork rule.
  run az network nsg rule create -g "$rg" --nsg-name "nsg-$vm" -n in2n --priority 120 --access Allow --protocol Tcp --destination-port-ranges 7444 7443 --source-address-prefixes "$ssh" --output none
  run az network public-ip create -g "$rg" -n "pip-$vm" -l "$region" --sku Standard --allocation-method Static --tags $(az_tags "$phase") --output none
  run az vm create -g "$rg" -n "$vm" -l "$region" --size "$size" --image "$AZ_IMAGE" --admin-username "$AZ_SSH_USER" \
    --ssh-key-values "${AZ_SSH_KEY}.pub" --authentication-type ssh --vnet-name "vnet-$vm" --subnet default --nsg "nsg-$vm" --public-ip-address "pip-$vm" \
    --os-disk-size-gb "${R10_OS_DISK_GB:-40}" --storage-sku StandardSSD_LRS --tags $(az_tags "$phase") --output none
}
cloud_firewall() { echo "azure: NSG rules are created by up"; }
cloud_ip() { run az network public-ip show -g "$(az_rg "$1")" -n "pip-$(az_vm "$1" "$2")" --query ipAddress -o tsv; }
cloud_ssh() { # <phase> <code> <command>
  local ip; if [ "$HA_DRY" = 1 ]; then ip="<ip>"; else ip="$(cloud_ip "$1" "$2")"; fi
  az_ssh_options
  run ssh -i "$AZ_SSH_KEY" "${AZ_SSH_OPTIONS[@]}" -o ServerAliveInterval=20 "$AZ_SSH_USER@$ip" "$3"
}
cloud_scp() { # <phase> <code> <files...>
  local phase="$1" code="$2" ip; shift 2
  if [ "$HA_DRY" = 1 ]; then ip="<ip>"; else ip="$(cloud_ip "$phase" "$code")"; fi
  az_ssh_options
  run scp -i "$AZ_SSH_KEY" "${AZ_SSH_OPTIONS[@]}" "$@" "$AZ_SSH_USER@$ip:/tmp/"
}
cloud_peer() { # <phase> <code...>: full-mesh global VNet peering so etcd peers reach each other on private addresses
  local phase="$1"; shift; local rg a b va vb
  rg="$(az_rg "$phase")"
  for a in "$@"; do for b in "$@"; do [ "$a" = "$b" ] && continue
    va="vnet-$(az_vm "$phase" "$a")"; vb="vnet-$(az_vm "$phase" "$b")"
    local remote
    if [ "$HA_DRY" = 1 ]; then remote="<resource-id:$vb>"; else remote="$(az network vnet show -g "$rg" -n "$vb" --query id -o tsv)"; fi
    run az network vnet peering create -g "$rg" -n "$va-to-$vb" --vnet-name "$va" --remote-vnet "$remote" --allow-vnet-access --output none
  done; done
}
cloud_stop() { run az vm deallocate -g "$(az_rg "$1")" -n "$(az_vm "$1" "$2")" --output none; }
cloud_start() { run az vm start -g "$(az_rg "$1")" -n "$(az_vm "$1" "$2")" --output none; }
cloud_down() { # <phase>: delete the group, then verify nothing tagged remains
  local rg; rg="$(az_rg "$1")"
  run az group delete --name "$rg" --yes --no-wait
  [ "$HA_DRY" = 1 ] && { echo "poll: az group exists -n $rg ; az resource list --tag netclaw-spec=198 -o table"; return; }
  for _ in $(seq 1 60); do [ "$(az group exists --name "$rg")" = "false" ] && break; sleep 10; done
  [ "$(az group exists --name "$rg")" = "false" ] || { echo "group $rg still exists" >&2; return 1; }
  echo "deleted $rg"
}
cloud_list() { run az resource list --tag netclaw-spec=198 --query "[${1:+?tags.phase=='$1'}].{name:name,type:type,loc:location,phase:tags.phase}" -o table; }
cloud_get() { # <phase> <code> <localdir> <remote files...>
  local phase="$1" code="$2" dir="$3" ip f srcs=(); shift 3
  if [ "$HA_DRY" = 1 ]; then ip="<ip>"; else ip="$(cloud_ip "$phase" "$code")"; fi
  for f in "$@"; do srcs+=("$AZ_SSH_USER@$ip:$f"); done
  az_ssh_options
  run scp -i "$AZ_SSH_KEY" "${AZ_SSH_OPTIONS[@]}" "${srcs[@]}" "$dir/"
}
