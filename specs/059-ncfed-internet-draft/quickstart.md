# Quickstart: build, validate, and submit `draft-capobianco-ncfed-00`

How to compile the draft, check it, and submit it — the acceptance pipeline for
US1/SC-001/SC-002.

## 0. One-time tooling

```bash
gem install kramdown-rfc          # provides kdrfc (and pulls xml2rfc)
pip install idnits                # I-D nits checker (Python rewrite). If the package
                                  # name/version differs on this host, DON'T block:
                                  # the AUTHORITATIVE nits check is the Datatracker
                                  # submission tool (it runs idnits server-side).
kdrfc --version && idnits --version   # record whatever installs into SUBMISSION-CHECKLIST.md
```

## 1. Build (kramdown-rfc → RFCXML v3 + text + HTML)

```bash
cd docs/ietf
kdrfc draft-capobianco-ncfed-00.md          # -> .xml (v3), .txt, .html
# SC-001: this MUST complete with zero errors.
```

## 2. Nits check

```bash
idnits --verbose draft-capobianco-ncfed-00.txt
# SC-002: zero ERRORS. Triage WARNINGS into SUBMISSION-CHECKLIST.md:
#  - "no date" / "no RFC number" style warnings are expected pre-submission.
#  - a real author email must be present (front matter TODO@ -> real address).
```

## 3. Fidelity cross-check (SC-003 — the correctness gate)

For each of the 14 rows in `data-model.md` §3, confirm the draft's normative statement
matches the cited code fact. Any mismatch is a defect in the draft (never "fix the
code" — the wire is frozen, FR-024).

```bash
# quick sanity: the magics/sizes/timeouts in the draft vs the constants
grep -nE "NCFED|NCTUN|IN2N1|65536|30 s|10 s|90 s|-3200|-3202|-3203" docs/ietf/draft-capobianco-ncfed-00.md
```

## 4. Completeness review (SC-004..007)

- All 5 Security Considerations parts present (`data-model.md` §5)? (SC-004)
- All ~14 wire facts have an unambiguous statement + diagram where applicable? (SC-005)
- All mandatory I-D sections + Experimental boilerplate present? (SC-006)
- draft-yan / MCP / A2A differentiation restatable in one sentence? (SC-007)

## 5. Submit (Datatracker)

1. Fill the author email in the front matter; leave `date:`/`number:` blank (tool-filled).
2. Upload the **`.xml`** (RFCXML v3) at <https://datatracker.ietf.org/submit/>.
   - The tool re-runs xml2rfc + idnits and generates the renderings.
   - Verify the confirmation email (unless logged in as the listed author).
   - Submitting grants rights under **BCP 78/79** — acknowledge in the checklist.
3. Mind the **meeting submission window** (freezes ~2 weeks around each IETF meeting).

## 6. Socialize (AGENTPROTO-POSITIONING.md)

- Post to the `agentproto` list / attend the BoF/side-meeting at IETF 126.
- Lead with the one-line differentiation: *NCFED federates independently-operated agents
  (BGP identity + consent/TOFU, port-multiplexed with BGP) and carries A2A/MCP —
  complementary to, not competing with, `draft-yan-a2a-device-agent-applicability`
  (single-domain controller→device mTLS).*
- ISE (Experimental) is the fallback if the WG doesn't take it up.

## Definition of done

`kdrfc` clean + `idnits` clean + 14/14 fidelity rows verified + 5/5 security parts +
all mandatory sections + submission checklist complete = ready to upload.
