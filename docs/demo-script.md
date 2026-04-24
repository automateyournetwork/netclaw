# NetClaw Demo — Presentation Script

## Timing
The demo runs ~15-20 minutes. You talk while the coworker works.

---

## Opening — kick off the demo, then talk (2 min)

> "I want to introduce you to my coworker. Its name is NetClaw, and it's a network engineer — a really good one. I'm going to ask it to do something that would normally take a team a full day: build a complete network lab with 20 routers and switches, set up the source of truth, generate all the configurations, push them to every device, and set up compliance monitoring. One request, and it handles the rest.

> Let me ask it now, and while it works, I'll tell you how we trained it."

**[Type the prompt and start the demo]**

---

## Training a Coworker (while repo clones and Nautobot builds) — 3 min

> "When you hire a new network engineer, you don't just hand them the keys to production on day one. You onboard them. You teach them how your team works, what tools you use, where things are, what the rules are. That's exactly what we did with NetClaw.

> We wrote down everything a senior engineer would need to know to work on our network. Not in a wiki that nobody reads — in a format the AI actually follows.

> There are three parts to this training:

> First, **who it is**. We gave it an identity — a CCIE-level network engineer. It knows OSPF, BGP, MPLS, EVPN. It knows what a flapping interface looks like and what questions to ask when a BGP peer goes down. This isn't a chatbot that searches the internet — this knowledge is part of who it is.

> Second, **how it works here**. Every team has rules. Ours say: never guess what a device is doing — go look. Never change a config without capturing the before state. Never skip the change request. Always log what you did and why. These aren't suggestions — they're non-negotiable, just like they would be for any engineer on the team.

> Third, **what it knows about us**. Our device IPs, our platforms, our Slack channels, our timezone. The stuff that makes it useful for OUR network, not just any network."

---

## Skills — Teaching Someone How to Do the Job (while Nautobot builds) — 3 min

> "Now here's the part that really clicked for me. My wife asked me to explain what a 'skill' is, and I told her: imagine you're teaching someone to cook a recipe. If you're teaching a professional chef, you can say 'deglaze the pan and reduce.' If you're teaching someone who's never cooked, you need to say 'pour a splash of wine in the hot pan, scrape the brown bits with a wooden spoon, and let it simmer until it's half the volume.'

> Same dish. Different instructions. Depends on who you're teaching.

> Skills work the same way. They're step-by-step procedures written for the AI. Some models are like experienced engineers — you give them the goal and they figure out the steps. Others need every single command spelled out with warnings about what NOT to do.

> The skill driving this demo is about 150 lines. It says: clone this repo, run these exact commands, use these specific tools to talk to Nautobot, wait for the user between phases, and whatever you do, don't try to build a local git server — use the ones that already exist on GitHub.

> That last one? We learned it the hard way. The first time we ran this demo, the AI decided to install nginx and set up its own git server from scratch. Spent 30 minutes and $10 in API costs doing something completely unnecessary. So we wrote it into the skill: 'don't do that.' Just like you'd tell a new hire 'we don't do it that way here.'"

---

## Tools — Giving Your Coworker the Right Equipment (while Nautobot starts) — 2 min

> "A skilled engineer without tools can't do much. You need to give them access — to the devices, to the source of truth, to the ticketing system, to the monitoring platform.

> NetClaw connects to over 50 different platforms through something called MCP — Model Context Protocol. Think of it as giving your coworker login credentials and a desk with all the right applications open. Nautobot, Cisco devices, GitHub, Grafana, AWS, Meraki, Palo Alto — each one is a tool the coworker can pick up and use.

> The important thing is that these tools handle the messy details. The coworker doesn't need to know the API endpoint or the authentication header for Nautobot — it just says 'show me all devices' and the tool handles the rest. Just like a human engineer doesn't need to know the HTTP spec to use a web UI."

---

## Source of Truth (when Design Builder runs) — 2 min

> "Watch this — the coworker just asked Nautobot to run a job that populates the entire data model. In about 10 seconds, it created 20 devices, hundreds of interfaces, IP addresses, BGP sessions, OSPF configs, VLANs — everything.

> And then it verified its own work. It asked Nautobot 'show me all devices' and confirmed all 20 are there with the right IPs and roles. That's something a good engineer does naturally — you don't just run a command and assume it worked. You check.

> This source of truth is the foundation. It's the single answer to 'what should the network look like?' Everything that follows — the configs, the compliance checks, the drift detection — all compares reality against this."

---

## The Network (when ContainerLab deploys) — 2 min

> "Now it's building the actual network. Twenty devices — Cisco routers running a service provider core with OSPF and MPLS and BGP, plus Arista switches running data center fabrics with EVPN and VXLAN. Two data centers, east and west.

> These are real network operating systems. You can SSH in, run show commands, break things and fix them. The coworker is going to test connectivity before moving on — because we taught it that lesson too. If you skip the connectivity check and jump straight to pushing configs, half the devices fail and you waste time figuring out why."

---

## Configuration (when Ansible runs) — 2 min

> "Now it's generating configurations from templates using data from the source of truth, and pushing them to every device. Notice it's using specific flags — 'build' to generate, 'deploy' to push. The skill says 'never run without those flags' because the default behavior would redo work that's already done.

> This is the kind of tribal knowledge that lives in a senior engineer's head. 'Oh yeah, don't run that playbook without tags, it'll blow away your lab.' Now it's written down in a skill where every coworker — human or AI — can benefit from it."

---

## Compliance (when Golden Config runs) — 2 min

> "The last piece is compliance. The coworker is registering template repositories that define what each device's config SHOULD look like, then running a job that compares intended versus actual.

> After this, if someone changes a router config — adds an ACL, modifies a BGP peer — the system flags it. The coworker can investigate, determine if it was authorized, and either fix it or create a ticket. That's not a one-time setup — that's ongoing operational value."

---

## Closing — 1 min

> "Everything you just saw — the source of truth, the network, the configs, the compliance — was set up by a coworker from a single request. Not a script. Not a pipeline. A conversation.

> The point isn't to replace network engineers. It's to give them a coworker that handles the repetitive, procedural work — so they can focus on design, architecture, and the problems that actually need a human.

> The skills are open. The tools are open. The framework is open. You can train this coworker for your network, your procedures, your rules. And every time it makes a mistake, you update the training — just like you would with any team member."

---

## Q&A

**"What if it makes a mistake?"**
> Every action is logged — there's always an answer to 'what did it do and why.' For production, all config changes require an approved change request. It can't touch a device without one. And destructive operations always require a human to say yes.

**"How much does it cost?"**
> With prompt caching on Anthropic, about $2 for a full demo run. On Ollama Cloud with open-source models, it's free. The cost comes from how many times the AI has to think — batching work and taking breaks between phases keeps it low.

**"Which AI model works best?"**
> It depends on how detailed your skills are. Claude follows procedures very reliably — you can give it the goal and it figures out the steps. Open-source models need more hand-holding — every command spelled out. The better the training material, the more models can succeed.

**"Can I use this on my network?"**
> Yes. You edit two files — one with your device IPs, one with your platform details. The skills and tools work with Cisco, Arista, Juniper, Palo Alto, F5, and many others.

**"How is this different from Ansible or Terraform?"**
> Those are tools — they do exactly what you tell them. If an Ansible playbook fails, it stops. NetClaw is a coworker — if something fails, it reads the error, thinks about what went wrong, and tries a different approach. The skills give it the judgment to make good decisions.
