# Website agent handoff: one measured network, five imagined worlds

Build a compelling homepage feature from the supplied **prerecorded Google Genie 4 walkthroughs**. Use the assets in this package. Do not generate new worlds, add a live-generation button, call a paid API, or expose credentials. The visitor experience is video playback, seeking, replay and factual inspection. Visitors cannot choose a new route inside an already recorded movie.

The story is **Cisco pyATS Genie → NetClaw → Google Genie 4**. Cisco Genie provides measured network evidence; Google Genie provides a creative illustration. The distinction belongs in the experience, not only in fine print. These are actual Google-generated video streams recorded while navigating, not Three.js scenes, image previews or prompts presented as finished worlds.

## Assets and visual direction

Use `index.html` as the working static reference. Each detail page contains a native HTML video player, a download link and the authoritative network panel. All assets use relative paths and can be hosted together under a website subdirectory. Maintain five clearly differentiated treatments:

| World | Theme and interpretation | MP4 | Poster | Playback page |
| --- | --- | --- | --- | --- |
| 1 | Futuristic technical blueprint: dark drafting space, luminous interface rings and connection conduits | `media/world-01-blueprint.mp4` | `media/world-01-blueprint.jpg` | `worlds/blueprint.html` |
| 2 | Living fantasy: floating islands, crystalline citadels, trees, port arches and illuminated bridges | `media/world-02-fantasy.mp4` | `media/world-02-fantasy.jpg` | `worlds/fantasy.html` |
| 3 | Network city: routing towers, switching stations and transit-like connections | `media/world-03-network-city.mp4` | `media/world-03-network-city.jpg` | `worlds/network-city.html` |
| 4 | Packet-scale machinery: porcelain and brass mechanisms, interface gates and transparent conduits | `media/world-04-packet-scale.mp4` | `media/world-04-packet-scale.jpg` | `worlds/packet-scale.html` |
| 5 | Realistic future data center: equipment cabinets and luminous overhead connections | `media/world-05-data-center.mp4` | `media/world-05-data-center.jpg` | `worlds/data-center.html` |

The production target is 120 seconds per video, 1280 × 720, 24 fps, H.264 MP4 with fast-start metadata. **These browser captures are silent.** Consult `asset-manifest.json` for actual delivered files, durations and hashes; never label a missing asset complete. Do not add fabricated network sounds or narration that implies measured traffic.

Suggested headline: **One measured network. Five imagined worlds.** Suggested supporting copy: “Explore five recorded journeys inspired by the same real Cisco network. Inspect the evidence behind the imagination.” Avoid claims of an exact digital twin, real-time network health, packet simulation, fault simulation or persistent playable game export.

Make a strong poster-led gallery. Load video metadata on detail pages and full video only on demand. Use native controls, `playsinline`, meaningful poster alternatives, keyboard-accessible navigation, good contrast and mobile layouts. Avoid autoplaying five downloads. If using an introductory montage, derive it from these recordings and label it a montage; keep the complete originals accessible. Standard hosting bandwidth/storage may cost money, but playback must make **zero Google generation API calls**.

## The real network behind the images

The four core devices are R1, R2, SW1 and SW2. The following are historical measured physical connections, corroborated in the retained evidence:

| Device | Data port | Peer | Peer data port |
| --- | --- | --- | --- |
| R1 | Ethernet0/1 | R2 | Ethernet0/1 |
| R1 | Ethernet0/2 | SW1 | Ethernet0/1 |
| R2 | Ethernet0/2 | SW2 | Ethernet0/1 |

R1–R2 uses a /31 point-to-point data link, OSPF underlay and loopback-based iBGP overlay. The data network has no static routes. R1 supplies router-on-stick gateways for VLANs 10 and 20 through SW1; R2 does the same for VLANs 30 and 40 through SW2. The switch uplinks are trunks and Ethernet0/2 and Ethernet0/3 are access ports. Rapid-PVST, appropriate edge PortFast/BPDU Guard, explicit allowed VLANs and disabled DTP were part of the lab configuration. CDP and LLDP were enabled on data ports; management interfaces were excluded and preserved. This is a description of the retained lab state, not a current health claim.

Four host links are separately **declared by the saved CML topology**: SW1 Ethernet0/2–PC1, SW1 Ethernet0/3–PC2, SW2 Ethernet0/2–PC3 and SW2 Ethernet0/3–PC4. They must not be portrayed as four verified healthy hosts. PC2–PC4 were not running in the retained controller observation. SW1's later enrichment connection failed; its earlier complete, verified baseline is retained with that limitation.

The earlier lab verification retained 78 behavior checks and eight five-packet probes, 40/40 packets successful within that tested scope. It did not establish current state or all-host reachability. No device configuration was changed during video production.

The snapshot manifest hash is:

`08a163e056c9e195d881b5fee24aef5fc64db7de17a6dabf4a96f633b69ef51d`

The sealed snapshot contains 1,011 manifested files. The expanded catalog has 152 command entries: 120 were issued (119 successful responses and one SW1 connection failure), and 32 were unissued. Parsing coverage is recorded as 100 parsed, 17 raw-only, two empty and 33 unavailable. Counts describe this capture inventory; they are not 152 successful measurements. Raw command output, configuration, IP addressing, credentials, raw counters and management topology remain local and are absent from this website package.

### Collection commands and provenance

Collection used bounded role-specific pyATS operations and offline parsing, not an unrestricted `learn all`. Commands cover identity (`show version`); interfaces (`show ip interface brief`, `show interfaces description`, timed `show interfaces`); CDP/LLDP global, interface and detailed-neighbor views; OSPF process, neighbor, interface and router-LSA views; BGP summary, neighbors, advertisements, routes and filters; route tables and CEF; router-on-stick subinterfaces; VLANs, trunks and switchport state; STP root, VLAN and interface details; error-disabled ports and counters; MAC/ARP and logs. Running/startup configuration was retained only for local change audit. Explicit source-addressed pings were separate active verification.

The complete maintainer command table is `specs/200-genie-network-worlds/collection-commands.md` in the source repository. Do not upload its private argument expansions or the raw snapshot. A counter is not a rate unless sample continuity and timing support that calculation; the Google worlds' moving lights are fictional, not counter-driven animation.

### CML topology image

Use `media/cml-topology.png` and its editable vector source `media/cml-topology.svg`. They show eight nodes and seven data links, excluding management. Solid core links are measured; dashed host links are controller-declared. `network-facts.json` carries the same distinction.

**Caption it accurately:** “2D reconstruction from the saved Cisco CML topology and frozen network evidence.” This is a screenshot of our reconstructed diagram, **not a screenshot of the native live CML application**. Native CML screenshot access was unavailable during packaging. Do not remove that provenance label or present host declarations as measurements.

## How the Google worlds were produced

The source implements the documented Google `genie-4` Interactions API behind a thin execution MCP and a scoped workflow skill. The MCP and skill orchestrate the API; they do not replace the underlying Google service. A Node backend owns the API credential, exact reviewed projection, lifecycle worker, recording evidence and SQLite cost ledger. The local browser receives generated media and sends navigation/event controls. It does not receive the Google key.

The six source MCP tools are `genie_world_prepare`, `genie_world_start`, `genie_world_status`, `genie_world_event`, `genie_world_stop` and `genie_world_evidence`. Implementation is in `scripts/genie-worlds/mcp_server.py`, with the canonical source registration at `mcp-servers/genie-worlds-mcp/server.py`. The workflow skill is `workspace/skills/netclaw-genie-worlds/SKILL.md`; the detailed tool contract is its `references/tools.md`.

The first hosted production qualification used an independent synthetic scenario. The five themed recordings then used exact, operator-pinned private-derived projections of the real snapshot: reviewed core labels, measured data-port pairings, VLAN IDs and OSPF/iBGP relationships. Style and composition are fictional. Source-file hashes, manifest identity, projection hash and explicit budget are pinned before admission. Tools cannot accept arbitrary prompts, credential paths or export-approval booleans.

Each tour used navigation and one fictional text-steered lighting event: a selected cyan connection was asked to turn amber while preserving the topology. The single semantic event used ten identical, closely spaced text impulses as one bounded delivery. Sending it is not proof of the intended visible change. The packet-scale capture visibly changed a foreground light capsule to amber; the exact target and full-link effect were not confirmed in every style. The factual snapshot was never altered.

Keep the visual limitations visible: the blueprint can repeat background structures; fantasy and city are metaphors; the data center introduces extra cabinets and unreliable labels. Small text, exact port identity and connectivity cannot be certified from generated pixels. The factual diagram and table are the source of truth. Treat these as creative network walkthroughs grounded in selected real evidence, not a precision visualization engine.

Fifty source refinement passes preceded actual production. They produced and tested source changes; they were **not fifty paid world generations** and did not themselves satisfy live acceptance. Actual production evidence, rather than loop counts, establishes what was recorded.

## NetClaw member in a Risk: distinguish design from qualification

The designed deployment is a scoped `genie-worlds` **member in the owner's existing Risk**. Its policy exposes the six controls and the workflow skill. The member gets a backend control capability, not the Google credential, CML/pyATS device credentials or unrestricted snapshots. Native member setup is intended to reuse supported NetClaw enrollment and policy mechanisms.

**The actual existing Risk member has not been installed or qualified in this work.** Actual stdio MCP → backend → Google → browser execution was exercised, but it does not establish an LLM-driven member turn, enrollment, or end-to-end Risk acceptance. The selected Risk runtime home and agent provider/model credential reference still need to be bound through the supported setup review. Do not advertise this as an already deployed member or generally released NetClaw feature. HUD, VS Code and Mobile integration remains outside this prototype.

## Lifecycle, cost and hosting boundaries

The owner authorized five full recordings plus initial synthetic qualification under a US$100 aggregate hard limit. The US$25 point is a review checkpoint, not permission to exceed that limit. Each admitted session reserves US$14.258688 conservatively, including the 120-second video bound and maximum documented input/text token bounds. Six reservations total US$85.552128. Reservations are **not billed usage**; no final billing receipt was available. The campaign ledger retains the full amounts until usage reconciliation.

The backend owns deadlines and termination. A closed browser or transport is not proof of remote completion. Initial workers timed out waiting for terminal receipts and preserved unknown states; original-provider-ID reconciliation recovered remote terminal receipts without creating replacement worlds. A temporary Google project spending-cap rate limit interrupted one such reconciliation, and local admission correctly refused the fifth world until the original session's terminal receipt was obtained. The refused attempt created no provider session. Consult the production verification record for the final status of every session.

No website visitor should call this lifecycle. The delivered MP4 is a recording, not a portable persistent world or scene graph. Website controls may play, pause, seek, replay and display authoritative facts; they cannot provide new navigation or new Google-generated state changes offline. Do not add an “explore live” option.

Official references checked during production: [Genie API guide](https://aistudio.google.com/docs/genie), [Genie 4 model reference](https://aistudio.google.com/docs/models/genie-4), [pricing](https://aistudio.google.com/docs/pricing#genie-4), [prompting guide](https://aistudio.google.com/docs/genie-prompting), [Interactions overview](https://aistudio.google.com/docs/interactions-overview), [rate limits](https://aistudio.google.com/docs/rate-limits), and [terms](https://aistudio.google.com/docs/terms). Recheck official documentation before any new paid production; do not infer future capabilities from this handoff.

## Website acceptance checklist

- All delivered videos play and seek, report 120 seconds and have correct posters; their hashes match the manifest.
- Page load and playback make no Google requests and require no API key, account login or backend generation service.
- The gallery, five detail pages and topology image work on desktop and mobile with keyboard-accessible controls.
- The measured topology, frozen date/provenance and important unavailable evidence remain discoverable beside every recording.
- The topology reconstruction is not mislabeled as a native CML screenshot. Generated geometry is not labeled measured.
- Fictional amber animation is not called an actual link failure, reroute, traffic measurement or live network change.
- Marketing separates implemented MCP/skill source from unqualified Risk-member deployment. There is no 100% feature-acceptance claim.
- No raw configurations, addresses, credentials, private launch packets, SQLite ledgers or original provider IDs are published.
- Publish the reviewed static package through the website's normal deployment process. This handoff does not claim that a public website has already been deployed.
