"""The skills must carry a followable procedure. Spec 084, SC-002/005/006/009..013/020.

Same reasoning as spec 083's equivalent: adoption means no NetClaw code in the call path,
so the skills are the enforcement. Unlike 083 they are the SECOND layer here — the
mandated cluster-wide-read credential is the first — but a second layer that says nothing
useful is not a layer.
"""
from __future__ import annotations
from _harness import FAILURES, check, read, run  # noqa: F401

NP, SP_, WI = "k8s-network-policy", "k8s-service-path", "k8s-workload-inventory"
SKILLS = [NP, SP_, WI]

def _s(n): return read("workspace", "skills", n, "SKILL.md")

def test_frontmatter():
    for n in SKILLS:
        head = _s(n).split("---")[1]
        for f in ("name:", "description:", "version:", "license:", "tags:", "user-invocable:"):
            check(f"{n} declares {f}", f in head, "absent")
        check(f"{n}'s description has a 'Use when' clause", "Use when" in head, "router cannot dispatch")

def test_no_policy_means_permitted():
    t = _s(NP)
    check("the default-allow consequence is stated", "all traffic is permitted" in t.lower(),
          "reporting 'no policies' without the consequence invites the opposite conclusion")
    check("it is framed as a finding, not an observation", "finding" in t.lower())
    check("default-allow is named explicitly", "default-allow" in t.lower())

def test_preflight_procedure_exists():
    t = _s(NP)
    check("a numbered procedure exists", "Step 1" in t and "Step 2" in t, "prose is not a procedure")
    check("the preflight uses can-i", "can-i" in t, "no way to establish scope")
    check("can-i comes before the listing step", t.find("can-i") < t.find("resources_list"),
          "the order IS the procedure")
    check("a 'no' answer changes behaviour, not just the wording",
          "stop treating empty results as absence" in t.lower(), "the preflight has no consequence")

def test_narrowing_is_shown_not_just_warned():
    t = _s(NP)
    check("the skill shows the reproduced evidence", "raw kubectl" in t and "this server" in t,
          "an abstract warning is easier to skip than a demonstrated one")
    check("the audit-lie framing is present", "audit lie" in t.lower())

def test_six_absences():
    t = _s(NP)
    for cause in ("Permission insufficient", "Namespace does not exist", "Namespace exists but is empty",
                  "Selector matched nothing", "CRD not installed", "Cluster unreachable"):
        check(f"absence cause '{cause}' is covered", cause in t, "collapsed into a generic empty result")
    check("the selector must be shown so a typo is visible", "show the selector" in t.lower())

def test_scope_and_cluster_must_be_stated():
    for n in SKILLS:
        t = _s(n).lower()
        check(f"{n} requires stating the scope", "scope" in t, "an ambiguous scope is how a namespace becomes a cluster")
    check(f"{NP} requires naming which cluster answered", "which cluster" in _s(NP).lower())
    check(f"{WI} requires naming which cluster answered", "which cluster" in _s(WI).lower())

def test_service_path_diagnoses():
    t = _s(SP_)
    check("links must be marked checked or not checked", "not checked" in t.lower(),
          "a partial trace presented as complete is this skill's failure mode")
    check("'no endpoints' is called a symptom not a diagnosis", "symptom" in t.lower())
    check("selector-matches-no-pods is a named diagnosis", "matches no pods" in t.lower())
    check("ready vs not-ready is distinguished", "not-ready" in t.lower() or "not Ready" in t)
    check("a non-existent ingress backend is called out", "does not exist" in t.lower())

def test_inventory_rules():
    t = _s(WI)
    check("Running is distinguished from Ready", "running" in t.lower() and "ready" in t.lower()
          and "not serving" in t.lower())
    check("non-running pods must not be omitted", "never omit" in t.lower() or "never omitted" in t.lower())
    check("event retention is treated as an empty-result trap", "aged out" in t.lower())

def test_traffic_is_not_permission():
    t = _s(NP).lower()
    check("observed traffic vs declared policy is distinguished",
          "traffic observed is not traffic permitted" in t or "not prove" in t,
          "the kubeshark confusion is the most common misreading here")

def test_boundaries_in_every_skill():
    for n in SKILLS:
        t = _s(n).lower()
        for word in ("kubeshark", "prometheus", "read-only"):
            check(f"{n} names the {word} boundary/posture", word in t, "missing")

TESTS = [test_frontmatter, test_no_policy_means_permitted, test_preflight_procedure_exists,
         test_narrowing_is_shown_not_just_warned, test_six_absences, test_scope_and_cluster_must_be_stated,
         test_service_path_diagnoses, test_inventory_rules, test_traffic_is_not_permission,
         test_boundaries_in_every_skill]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "skill procedure"))
