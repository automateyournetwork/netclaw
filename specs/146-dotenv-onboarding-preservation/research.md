# Research

The template directs users to `cp .env.example .env`. Neither `install.sh` nor `setup.sh` imports that file. Onboarding precedes deployment, while generated runtime paths and platform credentials are written to `~/.openclaw/.env` (or Hermes' environment). Deployment creates a checkout template only at the end. Onboarding errors are swallowed and followed by a completion message.

Installed OpenClaw 2026.7.1-2 filters provider credentials from working-directory dotenv files. Its global state dotenv loads those keys and remains available when the working directory changes. Official references: [environment](https://docs.openclaw.ai/help/environment), [secrets and storage](https://docs.openclaw.ai/gateway/security/secrets-and-storage), [onboarding](https://docs.openclaw.ai/start/wizard).

An isolated Node subprocess invoked the installed `loadDotEnv` with a temporary HOME/state directory and dummy `ANTHROPIC_API_KEY`/`NETBOX_TOKEN`. It made no provider/service calls:

| Files and working directory | Provider present | Network key present |
| --- | --- | --- |
| Checkout dotenv, checkout cwd | false | true |
| Checkout dotenv, unrelated cwd | false | false |
| Same values in state dotenv, unrelated cwd | true | true |

Decision: explicit installer import into the trusted runtime location, constrained to the repository template's declared names. Do not source the file, export it wholesale, disable upstream workspace filtering, or overwrite existing runtime choices. Provide a previewable repair command. Original dotenv assignments are copied literally to avoid introducing shell parsing or interpolation.

OpenClaw upstream uses `OPENCLAW_STATE_DIR`; NetClaw historically treated `OPENCLAW_HOME` as its state directory. Preserve that installer fallback for compatibility, prefer the upstream state variable, and pass the resolved state directory to onboarding. Broader path migration is deferred.
