#!/usr/bin/env python3
"""
tts-mcp — Text-to-Speech MCP Server using Microsoft Edge TTS.
Converts NetClaw's text responses into MP3 audio files for Slack delivery.

No API keys required. No GPU required. Produces natural-sounding speech.

All MCP protocol output → stdout
All logs/debug → stderr
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from fastmcp import FastMCP
except ImportError:
    print("ERROR: fastmcp not installed. Run: pip3 install fastmcp", file=sys.stderr)
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts not installed. Run: pip3 install edge-tts", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(os.environ.get("TTS_OUTPUT_DIR", Path(__file__).parent / "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VOICE = os.environ.get("TTS_DEFAULT_VOICE", "en-US-GuyNeural")

# ---------------------------------------------------------------------------
# Logging (→ stderr only)
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="tts-mcp: %(message)s",
)
log = logging.getLogger("tts-mcp")

# ---------------------------------------------------------------------------
# MCP Server & Tools
# ---------------------------------------------------------------------------

mcp = FastMCP("tts-mcp")


@mcp.tool()
async def text_to_speech(text: str, voice: str = "", output_format: str = "mp3") -> str:
    """
    Convert text to speech audio using Microsoft Edge TTS.
    Returns the path to the generated MP3 file.
    Upload this file to Slack using files:write to deliver voice responses.

    text: The text to convert to speech.
    voice: Voice name (e.g. en-US-GuyNeural, en-US-JennyNeural).
           Default: en-US-GuyNeural. Use list_voices to see all options.
    output_format: Output format, always mp3.
    """
    voice = voice or DEFAULT_VOICE
    request_id = str(uuid.uuid4())[:8]
    output_path = str(OUTPUT_DIR / f"tts_{request_id}.mp3")

    if not text.strip():
        return json.dumps({"error": "Text cannot be empty"}, indent=2)

    log.info(f"[{request_id}] synthesizing {len(text)} chars with {voice}")
    start = datetime.now(timezone.utc)

    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        file_size = Path(output_path).stat().st_size

        log.info(f"[{request_id}] done in {elapsed:.1f}s — {file_size} bytes")

        return json.dumps(
            {
                "output_path": output_path,
                "voice": voice,
                "format": "mp3",
                "size_bytes": file_size,
                "text_length": len(text),
                "synthesis_seconds": round(elapsed, 1),
            },
            indent=2,
        )
    except Exception as e:
        log.error(f"[{request_id}] synthesis failed: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def list_voices(language: str = "en") -> str:
    """
    List available TTS voices, optionally filtered by language.
    Returns voice names that can be used with the text_to_speech tool.

    language: Language filter (e.g. 'en', 'es', 'fr'). Default: 'en'.
    """
    try:
        voices = await edge_tts.list_voices()
        filtered = [
            {
                "name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"],
                "is_default": v["ShortName"] == DEFAULT_VOICE,
            }
            for v in voices
            if v["Locale"].startswith(language)
        ]

        return json.dumps(
            {
                "voices": filtered,
                "total": len(filtered),
                "default_voice": DEFAULT_VOICE,
                "tip": "Use the 'name' field as the 'voice' parameter in text_to_speech.",
            },
            indent=2,
        )
    except Exception as e:
        log.error(f"list_voices failed: {e}")
        return json.dumps({"error": str(e)}, indent=2)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("starting — edge-tts voice synthesis MCP server")
    log.info(f"  output_dir: {OUTPUT_DIR}")
    log.info(f"  default_voice: {DEFAULT_VOICE}")
    mcp.run()
