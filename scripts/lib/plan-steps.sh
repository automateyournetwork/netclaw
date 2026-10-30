#!/usr/bin/env bash
# Fixed Spec153 bridge. Invoked only for an engine-owned private source copy.
set -euo pipefail
umask 077
[ "$#" -eq 3 ] || exit 2
component="$1"; private_source="$2"; selected_home="$3"
[ -n "${HOME:-}" ] && [ "$HOME" = "$selected_home/.setup/os-home" ] || exit 7
[ "$private_source" = "$selected_home/.setup/source" ] || exit 7
[ -f "$selected_home/.netclaw-setup-owner.json" ] || exit 7
case "$component" in
  pyats) function_name=component_install_pyats ;;
  junos) function_name=component_install_junos ;;
  arista-cvp) function_name=component_install_arista_cvp ;;
  f5) function_name=component_install_f5 ;;
  catc) function_name=component_install_catc ;;
  aruba-cx) function_name=component_install_aruba_cx ;;
  gnmi) function_name=component_install_gnmi ;;
  radkit) function_name=component_install_radkit ;;
  multivendor-cli) function_name=component_install_multivendor_cli ;;
  percepxion) function_name=component_install_percepxion ;;
  slc) function_name=component_install_slc ;;
  netbox) function_name=component_install_netbox ;;
  nautobot) function_name=component_install_nautobot ;;
  nautobot-golden-config) function_name=component_install_nautobot_golden_config ;;
  nautobot-routing) function_name=component_install_nautobot_routing ;;
  infrahub) function_name=component_install_infrahub ;;
  infoblox) function_name=component_install_infoblox ;;
  aci) function_name=component_install_aci ;;
  nso) function_name=component_install_nso ;;
  itential) function_name=component_install_itential ;;
  meraki) function_name=component_install_meraki ;;
  analysis) function_name=component_install_analysis ;;
  redfish) function_name=component_install_redfish ;;
  anta) function_name=component_install_anta ;;
  sdwan) function_name=component_install_sdwan ;;
  prisma-sdwan) function_name=component_install_prisma_sdwan ;;
  aap) function_name=component_install_aap ;;
  ise) function_name=component_install_ise ;;
  fmc) function_name=component_install_fmc ;;
  panorama) function_name=component_install_panorama ;;
  fortinet) function_name=component_install_fortinet ;;
  zscaler) function_name=component_install_zscaler ;;
  claroty) function_name=component_install_claroty ;;
  nvd-cve) function_name=component_install_nvd_cve ;;
  cisco-psirt) function_name=component_install_cisco_psirt ;;
  fwrule) function_name=component_install_fwrule ;;
  azure) function_name=component_install_azure ;;
  gcp) function_name=component_install_gcp ;;
  equinix) function_name=component_install_equinix ;;
  cloudflare) function_name=component_install_cloudflare ;;
  terraform) function_name=component_install_terraform ;;
  vault) function_name=component_install_vault ;;
  grafana) function_name=component_install_grafana ;;
  prometheus) function_name=component_install_prometheus ;;
  datadog) function_name=component_install_datadog ;;
  splunk) function_name=component_install_splunk ;;
  pagerduty) function_name=component_install_pagerduty ;;
  te-community) function_name=component_install_te_community ;;
  te-official) function_name=component_install_te_official ;;
  suzieq) function_name=component_install_suzieq ;;
  kubeshark) function_name=component_install_kubeshark ;;
  k8s) function_name=component_install_k8s ;;
  zabbix) function_name=component_install_zabbix ;;
  bgp-intel) function_name=component_install_bgp_intel ;;
  globalping) function_name=component_install_globalping ;;
  topolograph) function_name=component_install_topolograph ;;
  telemetry-receivers) function_name=component_install_telemetry_receivers ;;
  auvik) function_name=component_install_auvik ;;
  cml) function_name=component_install_cml ;;
  gns3) function_name=component_install_gns3 ;;
  containerlab) function_name=component_install_containerlab ;;
  protocol) function_name=component_install_protocol ;;
  peering) function_name=component_install_peering ;;
  servicenow) function_name=component_install_servicenow ;;
  gitlab) function_name=component_install_gitlab ;;
  jenkins) function_name=component_install_jenkins ;;
  forward) function_name=component_install_forward ;;
  atlassian) function_name=component_install_atlassian ;;
  msgraph) function_name=component_install_msgraph ;;
  halo) function_name=component_install_halo ;;
  markmap) function_name=component_install_markmap ;;
  drawio-rfc) function_name=component_install_drawio_rfc ;;
  uml) function_name=component_install_uml ;;
  subnet-calc) function_name=component_install_subnet_calc ;;
  wikipedia) function_name=component_install_wikipedia ;;
  devnet-content-search) function_name=component_install_devnet_content_search ;;
  blender) function_name=component_install_blender ;;
  ue5) function_name=component_install_ue5 ;;
  chrome-devtools) function_name=component_install_chrome_devtools ;;
  tts) function_name=component_install_tts ;;
  tavus-pal) function_name=component_install_tavus_pal ;;
  twitter) function_name=component_install_twitter ;;
  twilio) function_name=component_install_twilio ;;
  zoom-rtms) function_name=component_install_zoom_rtms ;;
  gait) function_name=component_install_gait ;;
  mempalace) function_name=component_install_mempalace ;;
  memory-mcp) function_name=component_install_memory_mcp ;;
  document) function_name=component_install_document ;;
  ollama) function_name=component_install_ollama ;;
  jev) function_name=component_install_jev ;;
  netconverter) function_name=component_install_netconverter ;;
  humanrail) function_name=component_install_humanrail ;;
  *) exit 2 ;;
esac
NETCLAW_DIR="$private_source"
NETCLAW_INSTALL_COMPONENT="$component"
NETCLAW_RUNTIME_ROOT="$selected_home/python-runtimes"
NETCLAW_MANIFEST="$selected_home/netclaw-components.conf"
export NETCLAW_DIR NETCLAW_INSTALL_COMPONENT NETCLAW_RUNTIME_ROOT NETCLAW_MANIFEST
source "$NETCLAW_DIR/scripts/lib/common.sh"
source "$NETCLAW_DIR/scripts/lib/install-steps.sh"
define_paths
[ "$RUNTIME_HOME" = "$selected_home" ] || exit 7
# Credentials/settings are written once by the classified engine phase.
# Legacy incidental defaults must not replace reviewed plan values.
_set_env_var() { return 0; }
_set_env_default() { return 0; }
_import_runtime_env() { return 7; }
openclaw() { return 7; }
hermes() { return 7; }
# pyATS has an explicit dependency-only Python adapter. Its legacy migration
# writes .env and must never be called through this bridge.
component_install_pyats() { return 7; }
# No system/global remedies are allowed in the isolated dependency phase.
sudo() { return 7; }
brew() { return 7; }
apt-get() { return 7; }
systemctl() { return 7; }
launchctl() { return 7; }
docker() { return 7; }
cd "$NETCLAW_DIR"
"$function_name" </dev/null
# Exit 0 is only completion; the Python adapter observes real artifacts next.
