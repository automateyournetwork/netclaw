# Quickstart: Stand up a risk and route work to a Member

End-to-end walkthrough of iN2N — forming a risk, enrolling a Member (one co-located, one in another cloud), and having the Border route a real task. Maps to US1–US5.

## 0. Concepts in one breath

You run several focused NetClaws — a **risk**. You only ever talk to the **Border Claw**. The Border routes each request to the **Member** that owns the skill and hands you the result. Members dial *out* to the Border, so they need no public address. Trust inside the risk is one-time enrollment + a pinned key — no CA, no mutual consent.

## 1. Install the Border

```
./scripts/install.sh
# N2N component prompt:
#   Standalone NetClaw or part of a risk?          → part of a risk
#   Risk name / description?                        → johns-risk / "John's lab fleet"
#   Role?                                           → Border
#   Enable eN2N / iN2N / both?                      → both
```
The Border comes up with the gateway (the only operator-facing interface) and an iN2N listener on its reachable endpoint.

```
n2n_risk_status()
→ role=border · risk=johns-risk · stacks=both · members=0
```

## 2. Provision a Member from a profile (co-located CML claw)

Profiles are derived from your installed skill catalog, so they match what you actually have:

```
n2n_member_add(profile="cml", name="cml")
→ member johns-risk/cml provisioned (scope: cml-lab-lifecycle + cml_* tools)
  enrollment token: in2n_xxxxxxxx   (single-use; hand to the member)
  join: set N2N_ROLE=member, N2N_BORDER_ENDPOINT=<border>, run enroll with this token
```

On the member host (same machine here) install as a **Member** of `johns-risk`, point `N2N_BORDER_ENDPOINT` at the Border, and start it with the token. The member generates its own self-signed key, dials out, presents `(token, public_key)`, and the Border pins it:

```
n2n_member_list()
→ johns-risk/cml   profile=cml   state=active   transport=loopback   in_flight=0
```

## 3. Provision a Member in another cloud (pyATS claw)

Same flow — the only difference is where it runs and how it reaches the Border:

```
n2n_member_add(profile="pyats", name="pyats")   → token in2n_yyyyyyyy
```
On a VM in another cloud/datacenter: install as a Member, set `N2N_BORDER_ENDPOINT` to the Border's address reachable over your private transport (VPC peering / WireGuard / tunnel), enroll with the token. No inbound ports opened on the member.

```
n2n_member_list()
→ johns-risk/cml     state=active  transport=loopback
  johns-risk/pyats   state=active  transport=distributed   (dialed in from cloud B)
```

## 4. Ask the Border — it routes to the specialist

You talk only to the Border. It picks the member and delegates:

```
"Recreate my NetClaw-Full-Topo lab in CML."

Border → n2n_route(request_text="recreate NetClaw-Full-Topo (10 nodes/12 links)")
→ matched member johns-risk/cml (CML specialist); task_id=t-abc  state=submitted   # returns in ~2s

n2n_task_status("t-abc")  → working · "nodes 6/10"
n2n_task_result("t-abc")  → completed · "lab up, OSPF adjacency formed"
```
```
"Run the pyATS testbed against those devices."

Border → n2n_route(...) → matched johns-risk/pyats (in cloud B); task_id=t-def
n2n_task_result("t-def") → completed · "42/42 tests passed"
```
Long builds run as background tasks (reused 053 async delegation) — they survive a member restart or a network blip.

## 5. What the Border refuses / handles

```
"Configure BGP on the CML member directly."         # cml member has no config skill
Border → ERR_OUT_OF_SCOPE (member declined; it only does CML lab lifecycle)

"Do something no member covers."
Border → ERR_NO_CAPABLE_MEMBER: no member in risk johns-risk can perform that
         (the Border does NOT attempt it itself)
```

## 6. Security lifecycle

```
n2n_member_remove("johns-risk/pyats")    # decommission cloud B member (confirm first)
→ key unpinned, dropped from routing; it cannot reconnect on the old key.
  To return it must re-enroll with a NEW token.
```
If a member repeatedly fails auth/health, the Border **auto-quarantines** it (unpins, stops routing, alerts you) — visible in `n2n_member_health` and on the HUD.

## 7. The outside world sees ONE identity

With eN2N also enabled, a peer *risk* federating with your Border sees only `johns-risk` (the Border) — never `johns-risk/cml` or the cloud-B pyATS member. If the Border satisfies a peer's request by delegating internally, your audit log shows both the external request and the internal delegation, linked — the peer just gets a result attributed to your risk.

## 8. Standalone is unchanged

Choosing **Standalone NetClaw** at install → behaves exactly as today (a risk of one, its own Border). `n2n_risk_status()` reports `standalone`; nothing about members or routing is imposed.

---

**Verification checklist** (acceptance):
- [ ] Border + 1 member up and routing in < 15 min from fresh install (SC-001)
- [ ] Member carries only its profile's skills (SC-002)
- [ ] Members opened zero inbound ports; both reached the Border by dialing out (SC-003/SC-011)
- [ ] Every routed request produced a logged internal delegation at the Border (SC-004)
- [ ] Out-of-scope refused; no-capable-member reported plainly (SC-007)
- [ ] Removed member refused on reconnect; spent token rejected (SC-010)
- [ ] eN2N mesh behavior unchanged; standalone unchanged (SC-008/SC-009)
