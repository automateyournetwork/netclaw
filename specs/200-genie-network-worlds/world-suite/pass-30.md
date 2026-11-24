# World-suite pass30 — world3: post-baseline navigation capture

2026-11-23. Assignment from environment: pass30/world3; source_refinement.
One bounded partial T018/T028 unit. No checkbox closes;15/30 unchanged.

The viewer previously enabled navigation capture as soon as the baseline POST
returned. A click before newer decoded media consumed its single-flight attempt
with a backend refusal. Added a post-baseline-acknowledgement media gate at both
the button and direct handler/checkpoint boundaries. Eligibility is sampled at
frame receipt, before asynchronous JPEG decoding; pre-ack in-flight decoding and
old frame sequences cannot satisfy it. Capture status now says “Navigation:
Waiting for subsequent media.” Existing pending/saved/unconfirmed and no-replay
behavior is preserved. No new module or source-closure member was added; viewer
bytes changed, so prior reviewed paid packets remain stale.

## Verification and visual review

- Spec Kit prerequisites pass; requirements15/15 and quality43/43. Optional Git
  hooks omitted per owner. Existing audit root/branch reused.
- Red actual Chrome reproduction fails at “baseline ACK alone must not enable
  capture”; retained in `.spec200-local/tests/world-pass-30/browser-red.log`.
- Final actual Chrome6/6, zero skips, including three new synthetic scenarios:
  delayed baseline acknowledgement, pre-ack in-flight decode, and terminal state
  before post-ack decode finishes. All check old sequences, early direct handler
  calls and decode completion. Existing ten single-flight/response-loss scenarios
  still pass. Private `browser-green.log` and `navigation-order.json` retain results.
- Exact source closure/staleness checks5/5, zero skips: `source-review.log`.
- Reviewed `navigation-waiting.png`: disabled capture with readable waiting text,
  enabled Stop, explicit OFFLINE TRANSPORT FIXTURE / No Google generation banner.
  The preexisting transport JPEG is synthetic, never generated-world evidence.
- Native GAIT start/finish and full gait_log retained in the same private directory.

No source unit proves ten seconds of deliberate navigation, pixel authenticity,
Google camera/landmark quality, a visible event or accepted world3. No provider,
device, SSH/CML/pyATS call, dotenv read, private export, owner runtime change,
authority/allowance/acceptance/PROGRESS modification, branch change, Git commit,
agent/loop or publication. Sealed snapshot untouched.198at856bbc88/199AWS retained.

Next bounded defect: the automatic baseline checkpoint still awaits HTTP without
a timeout (unlike navigation/event captures). Reproduce lost/hanging baseline
response, then bound waiting without retrying an ambiguous save and preserve stop
and original-session evidence. Secondary known gap: recording.test.mjs registers
cleanup after Chrome launch/launchServer; pass25 corrected only browser helper.
Event JPEG/DB crash gap remains unconfirmed. Live/member/T029 gates stay open.
