# Voice Command Contracts

**Feature**: 043-full-voice-integration
**Date**: 2026-06-26

## Overview

This document defines the contract between voice input and MCP tool execution. The voice webhook receives transcribed speech, passes it to Claude for intent resolution, and Claude invokes the appropriate MCP tools.

## Voice Command Categories

### 1. Device Health Commands

**Intent**: Query device status, health metrics, reachability

**Example Utterances**:
- "Check the health of router R1"
- "Is the core switch up?"
- "Give me a network health summary"
- "What's the CPU on the firewall?"

**MCP Tools**: `pyats_get_device_health`, `pyats_show_command`

**Response Format**:
```
Device [name] is [status].
CPU usage: [X]%, Memory: [Y]% used.
[N] interfaces up, [M] interfaces down.
Uptime: [duration].
```

### 2. Configuration Query Commands

**Intent**: Retrieve specific configuration elements

**Example Utterances**:
- "Show me BGP neighbors on router R1"
- "Are all OSPF adjacencies up?"
- "What VLANs are on the access switch?"
- "What's the status of interface GigabitEthernet0/1?"

**MCP Tools**: `pyats_show_command`, `pyats_parse_output`

**Response Format**:
```
[Device] has [N] BGP neighbors.
Neighbor [IP] in AS [number] is [state].
[Continue for each or summarize if many]
```

### 3. Lab Management Commands

**Intent**: List, start, stop, or query CML/GNS3 labs

**Example Utterances**:
- "What labs do I have?"
- "Start the BGP training lab"
- "Stop all labs"
- "How many nodes are running in the OSPF lab?"

**MCP Tools**: `cml_list_labs`, `cml_start_lab`, `cml_stop_lab`, `gns3_list_projects`

**Response Format**:
```
You have [N] labs.
[Name]: [status], [X] nodes.
[Continue for each]

Starting lab [name]...
[Progress updates]
Lab is ready. All [N] nodes are running.
```

### 4. Incident Management Commands

**Intent**: Query, acknowledge, or get details on PagerDuty incidents

**Example Utterances**:
- "Are there any active incidents?"
- "Acknowledge the high priority incident"
- "Give me details on the database alert"

**MCP Tools**: `pagerduty_list_incidents`, `pagerduty_acknowledge`, `pagerduty_get_incident`

**Response Format**:
```
You have [N] active incidents.
[Priority] priority: [Title], open for [duration].
[Continue for each]

Incident acknowledged. [Title] is now in acknowledged state.
```

### 5. RFC Lookup Commands

**Intent**: Query RFC documentation

**Example Utterances**:
- "Look up RFC 2328"
- "What does RFC 4271 say about the decision process?"
- "Search RFCs for MPLS"

**MCP Tools**: `rfc_get_rfc`, `rfc_get_section`, `rfc_search`

**Response Format**:
```
RFC [number]: [title].
[Brief summary or requested section, formatted for speech]
```

### 6. Memory Commands

**Intent**: Store or recall facts and decisions

**Example Utterances**:
- "What do you remember about the data center migration?"
- "Remember that the maintenance window is Sundays 2-4 AM"
- "Why did we choose OSPF over EIGRP?"

**MCP Tools**: `memory_recall`, `memory_store`, `memory_search`

**Response Format**:
```
I found [N] relevant memories.
[Summary of each]

Got it. I'll remember that [fact summary].
```

### 7. Twitter Commands

**Intent**: Post tweets or check mentions

**Example Utterances**:
- "Post a tweet: Just completed the BGP migration"
- "Any Twitter mentions?"
- "Reply to the last mention"

**MCP Tools**: `twitter_post_tweet`, `twitter_get_mentions`, `twitter_reply`

**Response Format**:
```
Tweet posted: [content preview]

You have [N] recent mentions.
[Author] said: [content summary]
```

### 8. Context Commands

**Intent**: Manage conversation context

**Example Utterances**:
- "What device are we talking about?"
- "Summarize what we've found"
- "Forget the current context"

**MCP Tools**: None (handled by context manager)

**Response Format**:
```
We're currently focused on [device/lab].
Here's what we've found: [summary of findings]
```

## Error Response Contracts

### Device Unreachable
```
I couldn't reach [device].
It may be offline or there's a network issue.
Would you like me to check another device?
```

### Tool Timeout
```
The [operation] is taking longer than expected.
I'll keep trying. Would you like me to call you back when it's done?
```

### Ambiguous Request
```
I found [N] [items] matching that.
Which one did you mean: [option 1], [option 2], or [option 3]?
```

### MCP Server Unavailable
```
The [capability] service isn't available right now.
Would you like me to try something else?
```

### Sensitive Information
```
I found that information, but it contains sensitive data like credentials.
I can send it to you securely instead of reading it aloud.
Would you like me to do that?
```

## Speech Formatting Rules

1. **IP Addresses**: "10.0.0.1" → "10 dot 0 dot 0 dot 1"
2. **UUIDs**: Omit or "identifier ending in A-B-C"
3. **Percentages**: "85%" → "85 percent"
4. **Timestamps**: Convert to relative time "3 hours ago"
5. **Large Numbers**: "1000000" → "one million"
6. **Technical Acronyms**: Expand on first use "BGP, Border Gateway Protocol"
7. **Lists > 5 items**: "There are 10 items. Here are the first 5..."
8. **Error Codes**: Map to human descriptions
