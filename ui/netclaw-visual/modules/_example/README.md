# Example module

Not loaded — directories starting with `_` are skipped. Copy it to
`modules/<your-id>/` to start.

```bash
cp -r modules/_example modules/my-module
$EDITOR modules/my-module/module.json     # set id, name, requiresEnv
echo 'EXAMPLE_MODULE_URL=http://localhost:9999' >> .env
```

Then restart the HUD and check it was picked up:

```bash
curl -s localhost:3001/api/modules | jq '.modules[] | {id, configured, missing}'
```

With `requiresEnv` unsatisfied you should see `configured: false` and the missing
keys — and no routes and no UI. That is the intended behaviour, and the thing to
verify first when writing a module.

See ../README.md for the full contract.
