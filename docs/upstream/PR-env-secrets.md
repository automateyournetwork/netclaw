## Problem

`GET /api/env/:integrationId` returns each key's cleartext value alongside the masked form:

```js
const fields = mapping.env.map((key) => ({
  key,
  value: envVars[key] || '',                              // <-- plaintext
  masked: envVars[key] ? maskValue(envVars[key]) : '',
  isSet: key in envVars && envVars[key] !== '',
}));
```

The HUD never reads `value`. `renderEnvFields()` uses `field.key`, `field.isSet` and `field.masked`, and sets the input's value to `""` explicitly:

```js
<input class="env-input" data-key="${field.key}" type="text"
       placeholder="${field.isSet ? field.masked : 'not set'}"
       value="" />
```

So the plaintext has no consumer in the UI — it is returned but never displayed.

That matters because this endpoint enumerates credentials for **every configured integration** (SoT tokens, cloud keys, device passwords), the HUD has no authentication, and `server.listen(PORT)` with no host argument binds all interfaces. Any host that can reach the port can read them:

```
curl -s http://<hud-host>:3001/api/env/nautobot
```

## Fix

Remove the field. One line.

## Why this is safe

Editing a key is unaffected — the operator types a new value, and `PUT /api/env` has never needed the old one echoed back. `masked` still drives the placeholder, `isSet` still drives the status chip.

## Verification

Ran the config panel against this change on the endpoint's only consumer: renders identically (placeholder from `masked`, status from `isSet`), and saving a key still works.

## Notes

Found while running a downstream fork of the HUD on a LAN-reachable host. Happy to adjust the comment wording or drop it entirely if you'd prefer the diff be purely the deletion.

Worth mentioning separately, since it is out of scope here: the endpoint is unauthenticated on an all-interfaces listener, which is what makes this reachable in the first place. If you'd welcome an opt-in gate for the credential/config-write surface (`/api/env`, `PUT /api/testbed/raw`), I'm glad to open a separate issue rather than bundle it into this fix.
