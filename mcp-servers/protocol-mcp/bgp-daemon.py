#!/usr/bin/env python3
"""
BGP Daemon — Persistent speaker for NetClaw eBGP session
AS 65001 (NetClaw) <-> AS 65000 (Edge1 @ 172.16.0.1)
"""
import asyncio
import logging
import os
import sys
import json

# Add the protocol-mcp directory to path
sys.path.insert(0, os.path.dirname(__file__))

from bgp.speaker import BGPSpeaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('/tmp/bgp-daemon.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("bgp-daemon")

ROUTER_ID   = os.environ.get("NETCLAW_ROUTER_ID", "4.4.4.4")
LOCAL_AS    = int(os.environ.get("NETCLAW_LOCAL_AS", "65001"))
BGP_PEERS   = json.loads(os.environ.get("NETCLAW_BGP_PEERS", "[]"))

async def main():
    logger.info("Starting NetClaw BGP speaker — AS%s router-id %s", LOCAL_AS, ROUTER_ID)

    speaker = BGPSpeaker(
        local_as=LOCAL_AS,
        router_id=ROUTER_ID,
        listen_ip="0.0.0.0",
    )

    for peer in BGP_PEERS:
        speaker.add_peer(peer_ip=peer["ip"], peer_as=peer["as"])
        logger.info("Added peer %s AS%s", peer["ip"], peer["as"])

    logger.info("Starting speaker event loop...")
    await speaker.start()

    # Keep running and log state every 10s
    while True:
        try:
            for peer_ip, session in speaker.agent.sessions.items():
                state = session.fsm.state.name if hasattr(session, 'fsm') else "unknown"
                logger.info("Peer %s state: %s", peer_ip, state)
        except Exception as e:
            logger.debug("State poll error: %s", e)
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
