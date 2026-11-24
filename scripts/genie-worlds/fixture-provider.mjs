import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
// Deterministic transport frames, NEVER a generated world or model acceptance.
export class FixtureProvider {
  constructor({
    interval = 100,
    noTerminal = false,
    noUsage = false,
    noFrames = false,
  } = {}) {
    this.id = "fixture-" + randomUUID();
    this.interval = interval;
    this.noTerminal = noTerminal;
    this.noUsage = noUsage;
    this.noFrames = noFrames;
    this.closed = false;
    this.ended = false;
    this.changed = false;
    this.moved = false;
    this.sent = [];
  }
  async send(event) {
    this.sent.push(event);
    if (typeof event === "string") this.changed = true;
    else if (event.event_type === "user_action" && event.action === "key_down")
      this.moved = true;
  }
  async complete() {
    if (!this.noTerminal) this.ended = true;
  }
  async cancel() {
    this.closed = true;
  }
  async *receive() {
    let count = 0;
    while (!this.closed) {
      await new Promise((r) => setTimeout(r, this.interval));
      if (this.ended) {
        yield {
          event_type: "interaction.completed",
          status: "completed",
          ...(this.noUsage ? {} : { usage: { video_output_tokens: 0 } }),
        };
        return;
      }
      if (!this.noFrames) {
        const name = this.changed
          ? "event"
          : this.moved
            ? "movement"
            : "baseline";
        yield {
          event_type: "step.delta",
          delta: {
            type: "video",
            data: readFileSync(
              new URL(`./fixtures/${name}.jpg`, import.meta.url),
            ).toString("base64"),
          },
          fixture: true,
          sequence: ++count,
        };
      }
    }
  }
}
