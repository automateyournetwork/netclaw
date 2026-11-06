# R05 source and artifact provenance

NetClaw Spec176 adapts the selected model-admission, calculator, keyless-guard,
accounting and recovery patterns identified in
`specs/176-ollama-members/thermidor-reference.json` from Thermidor Spec004.
Thermidor's retained source notice identifies its adopted NetClaw ancestry under
Apache License 2.0. NetClaw's repository license continues to apply to these
adaptations; source comments identify changed/adapted behavior.

This adoption does not include Thermidor's product runtime, identifiers, private
state, transport, Tailscale components or later HA work.

The pinned official Ollama CPU files retain their original terms. `Ollama-LICENSE`
is retained here, and the image includes the public libstdc++/libgcc copyright
notices and exact CPU inventory from the verified extraction. The pinned Qwen3
model's Apache-2.0 license remains one of its five verified model blobs.
The separately prepared public guard/OpenClaw/PyYAML images and wheels retain
their own notices and artifact receipts. No third-party binary is committed here.
