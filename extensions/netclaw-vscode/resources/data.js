(() => {
  "use strict";
  const vscode = acquireVsCodeApi(),
    viewId = document.body.dataset.viewId,
    kind = document.body.dataset.kind || "overview";
  const content = document.getElementById("content"),
    status = document.getElementById("status"),
    filter = document.getElementById("filter"),
    refresh = document.getElementById("refresh");
  const post = window.netclawPost(vscode, viewId),
    pages = new Map();
  let model,
    observation,
    invalidated = false,
    revision = 0,
    availableActions,
    timer;
  const text = (tag, value, parent, cls) => {
    const e = document.createElement(tag);
    e.textContent = value;
    if (cls) e.className = cls;
    parent.append(e);
    return e;
  };
  function actions(items, parent) {
    if (!items?.length) return;
    const row = text("div", "", parent, "toolbar");
    for (const a of items) {
      if (availableActions && !availableActions.includes(a.id)) continue;
      const b = text("button", a.label, row);
      b.type = "button";
      b.addEventListener(
        "click",
        () =>
          !invalidated &&
          post("action", {
            action: a.id,
            ...(a.target ? { id: a.target } : {}),
          }),
      );
    }
  }
  function details(value, parent) {
    const d = text("details", "", parent, "source-details");
    text("summary", "Source details", d);
    d.addEventListener("toggle", () => {
      if (!d.open || d.dataset.loaded) return;
      d.dataset.loaded = "true";
      let encoded;
      try {
        encoded = JSON.stringify(value, null, 2);
      } catch {
        encoded = "Source details unavailable.";
      }
      text(
        "pre",
        encoded.length > 32000
          ? encoded.slice(0, 32000) + "\n[Display limited]"
          : encoded,
        d,
      );
    });
  }
  function draw() {
    if (!model) return;
    const query = filter.value.trim().toLocaleLowerCase(),
      f = document.createDocumentFragment();
    const intro = text("div", "", f, "section-intro");
    text("p", model.description, intro, "lede");
    actions(model.actions, intro);
    for (const notice of model.notices) text("p", notice, f, "notice");
    const source = text(
      "p",
      `${model.provenance.source}${model.provenance.observedAt ? " · " + model.provenance.observedAt : ""}`,
      f,
      "provenance",
    );
    source.id = "provenance";
    for (const [sectionIndex, group] of model.sections.entries()) {
      const section = text("section", "", f, "domain-section");
      section.setAttribute("aria-label", group.title);
      text("h2", group.title, section);
      const matching = group.cards.filter(
          (c) => !query || c.search.includes(query),
        ),
        page = Math.min(
          pages.get(sectionIndex) || 0,
          Math.max(0, Math.ceil(matching.length / 50) - 1),
        );
      if (!group.known) {
        text(
          "p",
          "This source has not reported this collection.",
          section,
          "empty-state",
        );
        continue;
      }
      if (!matching.length) {
        text(
          "p",
          group.cards.length
            ? "No loaded entries match your search."
            : "No entries in this observed result.",
          section,
          "empty-state",
        );
        continue;
      }
      if (group.cards.length > 1)
        text(
          "p",
          `${page * 50 + 1}–${Math.min(page * 50 + 50, matching.length)} of ${matching.length} matching entries (${group.cards.length} loaded)`,
          section,
          "hint",
        );
      const grid = text("div", "", section, "card-grid");
      for (const c of matching.slice(page * 50, page * 50 + 50)) {
        const article = text("article", "", grid, "info-card");
        article.dataset.entry = String(c.index);
        text(
          "p",
          kind === "integrations" ? "INTEGRATION" : group.title.toUpperCase(),
          article,
          "card-kicker",
        );
        text("h3", c.title, article);
        const dl = text("dl", "", article, "facts");
        for (const fact of c.facts) {
          text("dt", fact.label, dl);
          text("dd", fact.value, dl);
        }
        actions(c.actions, article);
        details(c.source, article);
      }
      if (matching.length > 50) {
        const nav = text("nav", "", section, "toolbar pagination");
        nav.setAttribute("aria-label", group.title + " pages");
        for (const [name, delta, disabled] of [
          ["Previous entries", -1, page === 0],
          ["Next entries", 1, (page + 1) * 50 >= matching.length],
        ]) {
          const b = text("button", name, nav, "secondary");
          b.disabled = disabled;
          b.dataset.pageControl = `${sectionIndex}:${delta}`;
          b.addEventListener("click", () => {
            pages.set(sectionIndex, page + delta);
            draw();
            const candidates = [
              ...content.querySelectorAll("button[data-page-control]"),
            ];
            (
              candidates.find(
                (x) =>
                  x.dataset.pageControl === `${sectionIndex}:${delta}` &&
                  !x.disabled,
              ) ||
              candidates.find(
                (x) =>
                  x.dataset.pageControl.startsWith(`${sectionIndex}:`) &&
                  !x.disabled,
              )
            )?.focus();
          });
        }
      }
    }
    const provenance = text("section", "", f);
    details(model.source, provenance);
    content.replaceChildren(f);
    content.dataset.rendered = String(++revision);
    status.textContent =
      "Observed result" + (query ? " · local filter active" : "");
    window.netclawObservation = { kind, observation };
    window.dispatchEvent(
      new CustomEvent("netclaw:observation", { detail: { kind, observation } }),
    );
  }
  filter.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      pages.clear();
      if (!invalidated) draw();
    }, 80);
  });
  refresh.addEventListener("click", () => {
    if (!invalidated) {
      status.textContent = "Refreshing…";
      post("refresh");
    }
  });
  window.addEventListener("message", (event) => {
    const m = event.data;
    if (!m || m.viewId !== viewId || invalidated) return;
    clearTimeout(timer);
    if (m.error) {
      model = undefined;
      observation = undefined;
      content.replaceChildren();
      status.textContent = String(m.error);
      status.className = "notice error";
      if (m.invalidated) {
        invalidated = true;
        filter.disabled = refresh.disabled = true;
        window.dispatchEvent(new Event("netclaw:invalidate"));
      }
      return;
    }
    let encoded;
    try {
      encoded = JSON.stringify(m.data);
    } catch {
      return;
    }
    if (
      typeof encoded !== "string" ||
      new TextEncoder().encode(encoded).length > 1024 * 1024
    ) {
      content.replaceChildren();
      status.textContent =
        "Observation exceeds the display limit. Narrow the source selection.";
      return;
    }
    availableActions = Array.isArray(m.availableActions) ? m.availableActions.filter(a => typeof a === "string") : undefined;
    observation = m.data;
    model = window.netclawPresenters.present(kind, observation);
    for (const group of model.sections)
      group.cards.forEach((c, i) => {
        c.index = i;
        c.search = JSON.stringify(c).toLocaleLowerCase();
      });
    pages.clear();
    status.className = "";
    draw();
  });
  post("ready");
})();
