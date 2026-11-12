// NetClaw in GCP (spec 193 / R09C). The extension never provisions anything itself: it collects the choices, shows the
// Standard Warning, and runs the repository's scripts/netclaw-gcp.py in a visible terminal so names, gates and warning text
// are identical to the install.sh TUI. Pure helpers are exported for tests.
export const GCP_TOPOLOGIES = [
  { id: "gcp-border", label: "GCP Border", description: "One Border in GCP" },
  { id: "gcp-member", label: "GCP Member", description: "One Member in GCP (attach to any Border)" },
  { id: "gcp-border-onprem-members", label: "GCP Border + on-prem Members", description: "Border in GCP, attach on-prem pyATS/CML Members" },
  { id: "onprem-border-gcp-members", label: "On-prem Border + GCP Members", description: "Two Members in GCP for your on-prem Border" },
  { id: "ha-risk", label: "HA Risk", description: "Two Borders + etcd witness in one region" },
  { id: "distributed-risk", label: "Distributed Risk", description: "A Border in each of three regions" },
] as const;
export const GCP_SCRIPT = "scripts/netclaw-gcp.py";
export const GCP_WARNING_FILE = "scripts/lib/gcp_warning.txt";
const PROJECT = /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/, REGION = /^[a-z]+-[a-z]+[0-9]+$/, CIDR = /^\d{1,3}(\.\d{1,3}){3}\/\d{1,2}$/;

export function validateGcpChoices(c: { topology: string; project: string; regions: string[]; httpsCidr: string }) {
  if (!GCP_TOPOLOGIES.some((t) => t.id === c.topology)) throw Error("Choose a listed GCP topology.");
  if (!PROJECT.test(c.project)) throw Error("Enter a valid GCP project id; none is ever assumed.");
  if (!c.regions.length || !c.regions.every((r) => REGION.test(r))) throw Error("Enter valid GCP region names.");
  if (c.topology === "distributed-risk" && new Set(c.regions).size !== 3) throw Error("A distributed Risk needs exactly three distinct regions.");
  if (!CIDR.test(c.httpsCidr)) throw Error("Enter an IPv4 CIDR for HTTPS access.");
  if (c.httpsCidr === "0.0.0.0/0") throw Error("0.0.0.0/0 is refused: this deployment has no authentication.");
}

const shq = (s: string) => `'${s.replace(/'/g, `'\\''`)}'`;
/** Command run in the terminal. The terminal CLI re-prompts for the acknowledgement; the modal only gates opening it. */
export function gcpPlanCommand(root: string, c: { topology: string; project: string; regions: string[]; httpsCidr: string }) {
  validateGcpChoices(c);
  return ["python3", shq(`${root}/${GCP_SCRIPT}`), "plan", "--topology", c.topology, "--project", shq(c.project),
    ...c.regions.flatMap((r) => ["--region", shq(r)]), "--https-cidr", shq(c.httpsCidr)].join(" ");
}
