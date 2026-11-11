# Registration Contract

```json
"cisco-iq-mcp": {
  "url": "<REGION ENDPOINT>",
  "headers": {"Authorization": "Bearer ${CISCO_IQ_API_KEY}"},
  "env": {"CISCO_IQ_API_KEY": "${CISCO_IQ_API_KEY}"}
}
```
Transport: Streamable HTTP. No other headers. Endpoints: emea `https://eu-central-1.iq.cisco.com/mcp`, us `https://us-west-2.iq.cisco.com/mcp`, apjc `https://ap-southeast-2.iq.cisco.com/mcp`. Source: issue #346 (official guide unreachable, unverified).
