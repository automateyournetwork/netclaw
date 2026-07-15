---
name: webex-voice-interface
description: "Respond to WebEx voice clips with both text and an MP3 voice reply using edge-tts. Voice IN is already handled by OpenClaw transcription. Use when a user sends a voice message in WebEx, you need to reply with audio, or you want to generate a spoken MP3 response."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["TTS_MCP_SCRIPT", "MCP_CALL"] } } }
---

# WebEx Voice Interface

## How It Works

```
User sends voice clip in WebEx space
    |
    v
OpenClaw transcribes automatically (built-in)
    |
    v
NetClaw processes with full skill set
(pyATS, NetBox, ServiceNow, all 43 MCP servers)
    |
    v
python3 $MCP_CALL "python3 -u $TTS_MCP_SCRIPT" text_to_speech -> MP3 file
    |
    v
Upload MP3 to WebEx thread + post text response
```

## Voice Response Workflow

### Step 1: Process the question

Treat the transcribed voice message identically to a typed text message.
Use the full NetClaw skill set -- pyATS, NetBox, ServiceNow, etc.

### Step 2: Generate voice response

After composing your text response, call `text_to_speech`:

```bash
python3 $MCP_CALL "python3 -u $TTS_MCP_SCRIPT" text_to_speech '{"text":"R1 has 3 OSPF neighbors, all in FULL state on Area 0...","voice":"en-US-GuyNeural"}'
```

This returns JSON with an `output_path` to the generated MP3 file.

To list available voices:

```bash
python3 $MCP_CALL "python3 -u $TTS_MCP_SCRIPT" list_voices '{"language":"en"}'
```

### Step 3: Deliver both text and voice

Post the text response in the WebEx space/thread AND upload the MP3 file as an attachment via the Messages API (multipart/form-data with `files` parameter):

> **Voice Response**
> [MP3 audio file attached]
>
> R1 has 3 OSPF neighbors, all in FULL state on Area 0:
> - 2.2.2.2 (R2) via Gi1 -- FULL/DR
> - 3.3.3.3 (R3) via Gi2 -- FULL/BDR

**Always deliver text AND voice.** Text is primary (searchable, accessible).
Voice is supplementary.

## Voice Selection

| Voice | Description |
|-------|-------------|
| en-US-GuyNeural | Professional male -- **default** |
| en-US-JennyNeural | Professional female |
| en-US-AriaNeural | Conversational female |
| en-GB-RyanNeural | British male |

Users can request a voice change:
- "Switch to a female voice" -> use en-US-JennyNeural
- "Use a British accent" -> use en-GB-RyanNeural

Call `list_voices` to see all 300+ available voices.

## Performance

| Phase | Latency |
|-------|---------|
| edge-tts synthesis | 1-2 seconds |
| WebEx MP3 upload | < 1 second |

Voice synthesis adds minimal overhead to the response time.

## Fallback

If TTS fails, deliver the text response immediately. Do not block on voice.

## Tips for Voice Responses

- **Keep it concise** -- under 100 words works best for spoken delivery
- **Avoid tables** -- describe data conversationally for voice
- **Spell out abbreviations** -- say "OSPF" not "O-S-P-F" (edge-tts handles this)
- **Use natural phrasing** -- the text will be read aloud, so write for the ear

## WebEx File Upload for Voice

WebEx Messages API supports file attachments via multipart upload:

```
POST https://webexapis.com/v1/messages
Content-Type: multipart/form-data

- roomId: <space-id>
- parentId: <thread-parent-message-id> (if threading)
- text: "Voice Response: R1 has 3 OSPF neighbors..."
- files: @/tmp/netclaw-tts/response.mp3
```

Files up to 100 MB are supported. MP3 voice responses are typically under 1 MB.

## GAIT Integration

Record voice interactions in the GAIT audit trail:

```
Input: Voice clip from @user (transcript: "What are your interfaces?")
Action: Queried R1 interfaces via pyATS
Output: 4 interfaces found -- text + voice response delivered to WebEx
```
