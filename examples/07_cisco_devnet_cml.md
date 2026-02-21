Hey, can you set up the following lab network for me?

*Topology:*
• R1 eth0/1 ↔ R2 eth0/1 (WAN)
• R1 eth0/0 ↔ SW1 eth0/2 (trunk)
• SW1: PC1 on eth0/0, PC2 on eth0/1
• R2 eth0/0 ↔ SW2 eth0/2 (trunk)
• SW2: Server1 on eth0/0, Server2 on eth0/1

*Requirements:*
• 10.10.20.170 is reserved for management — do not use
• VLANs: 10 (PC1), 30 (PC2), 40 (Server1), 50 (Server2)
• Router-on-a-Stick on R1 and R2
• OSPFv2 Area 0, /31 point-to-point links, passive interfaces on all LAN sub-interfaces
• Full RFC standards, best practices on all trunk and access ports

*When done please:*
1. Run a full set of pings and traceroutes across all VLANs and confirm 0% loss
2. Generate a draw.io topology diagram
3. Generate a Nana Banana topology file
4. Document the final IP plan and device configs
5. Add all assets R1, R2, SW1, SW2, to NetBox (all ips, interfaces, VLANs, etc.)
6. Add all assets R1, R2, SW1, SW2, to ServiceNow CMDB (all ips, interfaces, VLANs, etc.)
7. Provide links to all assets in NetBox and ServiceNow CMDB in the final documentation

Let me know if you need any clarification before starting! 🙏