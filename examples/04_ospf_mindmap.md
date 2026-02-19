# Example: OSPF Mind Map

## Prompt

```
Show me the OSPF topology as an interactive mind map
```

## What NetClaw Does

NetClaw uses **pyats-routing** for deep OSPF analysis, then **markmap-viz** to render it:

### Step 1: OSPF Process Overview

```
→ pyats_run_show_command: show ip ospf
```

Gets router ID, process ID, areas configured, SPF run count, reference bandwidth.

### Step 2: OSPF Neighbors

```
→ pyats_run_show_command: show ip ospf neighbor
```

Lists all adjacencies with state (FULL/DR, FULL/BDR, etc.), neighbor router ID, interface.

### Step 3: OSPF Interfaces

```
→ pyats_run_show_command: show ip ospf interface
```

Per-interface: area, network type (broadcast/P2P), cost, hello/dead timers, DR/BDR.

### Step 4: OSPF Database

```
→ pyats_run_show_command: show ip ospf database
```

Counts LSAs by type per area: Type 1 (Router), Type 2 (Network), Type 3 (Summary), Type 5 (External), Type 7 (NSSA External).

### Step 5: Generate Mind Map

```
→ markmap-viz create_markmap
```

NetClaw generates markdown and feeds it to Markmap:

```markdown
# OSPF Process 1 (RID: 1.1.1.1)

## Area 0 (Backbone)
### Neighbors
#### R2 (2.2.2.2) — FULL/DR via Gi1
#### R3 (3.3.3.3) — FULL/BDR via Gi2
### Interfaces
#### Gi1 — Cost 1, P2P, Hello 10s
#### Gi2 — Cost 1, Broadcast, Hello 10s
#### Lo0 — Cost 1, Loopback
### LSDB
#### 3 Router LSAs (Type 1)
#### 1 Network LSA (Type 2)
#### 0 Summary LSAs (Type 3)

## Area 1 (Stub)
### Neighbors
#### R4 (4.4.4.4) — FULL via Gi3
### Interfaces
#### Gi3 — Cost 10, P2P, Hello 10s
### LSDB
#### 2 Router LSAs (Type 1)
#### 2 Summary LSAs (Type 3)

## External Routes
### 5 Type 5 LSAs (from ASBR 2.2.2.2)
### Redistributed from: BGP
```

This opens as an interactive HTML mind map with zoom, collapse/expand, and pan controls.

## Example Mind Map Structure

```
OSPF Process 1
├── Area 0 (Backbone)
│   ├── Neighbors
│   │   ├── R2 — FULL/DR
│   │   └── R3 — FULL/BDR
│   ├── Interfaces
│   │   ├── Gi1 (cost 1, P2P)
│   │   ├── Gi2 (cost 1, broadcast)
│   │   └── Lo0 (loopback)
│   └── LSDB: 3 Router, 1 Network, 0 Summary
├── Area 1 (Stub)
│   ├── Neighbors
│   │   └── R4 — FULL
│   ├── Interfaces
│   │   └── Gi3 (cost 10, P2P)
│   └── LSDB: 2 Router, 2 Summary
└── External: 5 Type-5 LSAs from BGP
```

## Skills Used

- **pyats-routing** (OSPF analysis — process, neighbors, interfaces, database)
- **pyats-network** (underlying show commands with Genie parsing)
- **markmap-viz** (markdown-to-mind-map rendering)
