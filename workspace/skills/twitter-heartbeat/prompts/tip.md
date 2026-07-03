# Prompt: CCIE Tip

Generate a CCIE-level network engineering tip.

## Guidelines

- Pick one specific topic: BGP, OSPF, EIGRP, MPLS, EVPN/VXLAN, STP, QoS, AAA, or security
- Be direct and technical - no fluff
- Include the specific command or behavior being discussed
- Draw from real troubleshooting scenarios
- Include #netclaw hashtag
- Max 280 characters

## Examples

- "BGP tip: weight is LOCAL to the router - it's not advertised. If you need to influence all routers, use local preference instead. #netclaw"
- "OSPF tip: DR/BDR elections only happen on broadcast and NBMA networks. Point-to-point links don't need them. Save yourself the troubleshooting. #netclaw"
- "STP tip: PortFast doesn't disable STP - it just skips the listening/learning states. The port still participates in topology changes. #netclaw"

## Topics to Draw From

- Route redistribution gotchas
- Protocol timer tuning
- Debugging methodologies
- Configuration best practices
- Common misconfigurations
- Security hardening
- Performance optimization
