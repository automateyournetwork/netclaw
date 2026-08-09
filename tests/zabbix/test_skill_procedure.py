"""The skills must contain a FOLLOWABLE PROCEDURE, not a warning. Spec 083, FR-006a.

This is the most important static suite in the feature, and the reason is uncomfortable:
after the adopt-as-is decision the skills are the ONLY thing preventing two silent
wrong-answer failures. There is no chokepoint. A skill that merely says "beware of value
types" is not enforcement — it is a note the agent may or may not act on.

So these tests check for the ORDER and the MECHANICS of a procedure, not for the presence
of scary words.
"""
from __future__ import annotations
from _harness import FAILURES, check, read, run  # noqa: F401

METRICS = "zabbix-metrics-history"
SKILLS = [METRICS, "zabbix-problem-review", "zabbix-availability"]

def _s(name): return read("workspace", "skills", name, "SKILL.md")

def test_frontmatter_matches_the_schema():
    for name in SKILLS:
        t = _s(name)
        check(f"{name} has frontmatter", t.startswith("---\n"), "missing")
        head = t.split("---")[1]
        for field in ("name:", "description:", "version:", "license:", "tags:", "user-invocable:"):
            check(f"{name} declares {field}", field in head, "absent")
        check(f"{name}'s description ends with a 'Use when' clause",
              "Use when" in head, "the router cannot tell when to reach for it")

def test_the_value_type_procedure_is_ordered_and_concrete():
    t = _s(METRICS)
    i_item, i_hist = t.find("item.get"), t.find("history.get")
    check("item.get is mentioned before history.get", 0 <= i_item < i_hist,
          "the order IS the procedure — reversing it is the bug")
    check("the procedure is numbered, not prose",
          "Step 1" in t and "Step 2" in t and "Step 3" in t and "Step 4" in t,
          "an unnumbered caution is not a procedure")
    check("it names the actual default the API uses",
          "defaults" in t and "3" in t, "the trap is unstated")
    check("it gives the value_type table so the agent can look the value up",
          "float" in t and "unsigned" in t, "the agent cannot act without the mapping")
    check("it quantifies how common the trap is",
          "84" in t, "without the measurement this reads as a theoretical caveat")

def test_type_splitting_is_required():
    t = _s(METRICS)
    check("mixing value types is explicitly prohibited",
          "mix" in t.lower() and "one call" in t.lower(), "unstated")
    check("the remedy is given, not just the hazard",
          "group" in t.lower() and "merge" in t.lower(),
          "telling an agent something is wrong without telling it what to do instead is not guidance")

def test_the_retention_router_is_a_decision_table():
    t = _s(METRICS)
    check("trend.get is covered", "trend.get" in t, "half the retention story is missing")
    check("routing is presented as a decision table", "Requested window" in t or "| Use |" in t,
          "prose routing will not be followed reliably")
    check("aggregates must be declared as hourly",
          "hourly" in t and ("not instantaneous" in t or "instantaneous" in t),
          "a peak from an hourly average is a different claim and must be labelled")
    check("boundary-spanning is covered", "spans the boundary" in t or "both" in t.lower())

def test_all_five_absences_are_distinguished():
    t = _s(METRICS)
    for cause in ("Wrong value type", "Aged out", "Retention disabled",
                  "Never collected", "Genuinely idle"):
        check(f"absence cause '{cause}' is named", cause in t, "collapsed into a generic 'no data'")
    check("retention-disabled is called a configuration fact",
          "configuration fact" in t, "it would read as an absence of data")
    check("never-collected is called a finding",
          "real finding" in t, "a broken poll must not read as 'nothing happened'")
    check("history=0 and trends=0 are both covered",
          "history=0" in t and "trends=0" in t, "the third retention state is missing")

def test_availability_never_asserts_a_device_is_down():
    t = _s("zabbix-availability")
    lowered = t.lower()
    check("the wording rule is the headline", "not" in lowered and "the device is down" in lowered,
          "the central discipline of this skill is missing")
    check("it requires attributing to the NMS", "vantage point" in lowered,
          "one poller's view must be framed as such")
    check("it requires a timestamp on every observation",
          "last observed" in lowered or "when that state was last observed" in lowered
          or "timestamp the observation" in lowered)
    check("not-monitored is distinguished from unreachable",
          "not monitored" in lowered, "the most common cause of surprise is unhandled")
    check("flapping is distinguished from sustained down",
          "flap" in lowered or "transitions" in lowered)

def test_problem_review_separates_empty_from_unreachable():
    t = _s("zabbix-problem-review")
    check("empty vs unreachable is called out",
          "no active problems" in t.lower() and "unreachable" in t.lower(),
          "reporting an unreachable NMS as 'no problems' is the worst failure in this skill")
    check("acknowledgement is not resolution",
          "acknowledged" in t.lower() and ("never" in t.lower() or "still happening" in t.lower()))
    check("duration is required, not just onset", "duration" in t.lower() or "how long" in t.lower())

def test_every_skill_states_all_five_boundaries():
    """FR-045..FR-049. Principle VII rests on these and nothing else checks them."""
    needles = {
        "prometheus/grafana": ("prometheus", "grafana"),
        "snmptrap (push vs poll)": ("snmptrap-mcp",),
        "ipfix (flows vs counters)": ("ipfix-mcp",),
        "SaaS monitoring": ("auvik", "thousandeyes", "datadog"),
        "device-reading skills": ("pyats", "multivendor-cli"),
    }
    for name in SKILLS:
        t = _s(name).lower()
        for label, words in needles.items():
            check(f"{name} names the {label} boundary",
                  all(w in t for w in words), f"missing one of {words}")

def test_the_enforcement_limitation_is_stated():
    t = _s(METRICS)
    check("the metrics skill warns that nothing structurally prevents the traps",
          "passthrough" in t.lower() and "will not stop you" in t.lower(),
          "an agent must know the guardrail is guidance, not code")
    check("the absence of a per-call audit trail is stated",
          "audit" in t.lower(), "a user needing an auditable record must be told there is none")

TESTS = [test_frontmatter_matches_the_schema, test_the_value_type_procedure_is_ordered_and_concrete,
         test_type_splitting_is_required, test_the_retention_router_is_a_decision_table,
         test_all_five_absences_are_distinguished, test_availability_never_asserts_a_device_is_down,
         test_problem_review_separates_empty_from_unreachable,
         test_every_skill_states_all_five_boundaries, test_the_enforcement_limitation_is_stated]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "skill procedure"))
