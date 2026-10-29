(() => {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const wrappers = document.querySelectorAll("[data-search-suggest]");
  wrappers.forEach((wrapper) => {
    const input = wrapper.querySelector("input[name='q']");
    const panel = wrapper.querySelector(".search-suggest");
    if (!input || !panel || !panel.id) return;

    let activeIndex = -1;
    let request = null;
    let timer = null;
    let lastQuery = "";

    const options = () => panel.querySelectorAll("[role='option']");

    const close = () => {
      panel.hidden = true;
      panel.replaceChildren();
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    };

    const setActive = (index) => {
      const rows = options();
      if (!rows.length) return;
      activeIndex = (index + rows.length) % rows.length;
      rows.forEach((row, position) => {
        const isActive = position === activeIndex;
        row.classList.toggle("is-active", isActive);
        row.setAttribute("aria-selected", String(isActive));
      });
      const active = rows[activeIndex];
      input.setAttribute("aria-activedescendant", active.id);
      active.scrollIntoView({
        block: "nearest",
        behavior: reducedMotion.matches ? "auto" : "smooth",
      });
    };

    const buildRow = (suggestion, index) => {
      const row = document.createElement("a");
      row.className = "search-suggest__item";
      row.id = `${panel.id}-option-${index}`;
      row.href = suggestion.url;
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", "false");

      if (suggestion.image) {
        const image = document.createElement("img");
        image.src = suggestion.image;
        image.alt = "";
        image.loading = "lazy";
        image.decoding = "async";
        row.append(image);
      }

      const body = document.createElement("span");
      body.className = "search-suggest__body";
      const name = document.createElement("strong");
      name.textContent = suggestion.name;
      body.append(name);
      if (suggestion.store || suggestion.category) {
        const meta = document.createElement("small");
        meta.textContent = [suggestion.store, suggestion.category].filter(Boolean).join(" · ");
        body.append(meta);
      }
      row.append(body);

      const price = document.createElement("span");
      price.className = "search-suggest__price";
      price.textContent = `৳${suggestion.price}`;
      if (suggestion.was_price) {
        const was = document.createElement("del");
        was.textContent = `৳${suggestion.was_price}`;
        price.append(" ", was);
      }
      row.append(price);

      row.addEventListener("pointerdown", (event) => event.preventDefault());
      return row;
    };

    const render = (suggestions) => {
      if (!suggestions.length) {
        close();
        return;
      }
      const fragment = document.createDocumentFragment();
      suggestions.forEach((suggestion, index) => fragment.append(buildRow(suggestion, index)));
      panel.replaceChildren(fragment);
      panel.hidden = false;
      input.setAttribute("aria-expanded", "true");
      activeIndex = -1;
      input.removeAttribute("aria-activedescendant");
    };

    const load = async (query) => {
      if (request) request.abort();
      request = new AbortController();
      try {
        const response = await fetch(
          `/api/search-suggestions?q=${encodeURIComponent(query)}`,
          { signal: request.signal, headers: { Accept: "application/json" } }
        );
        if (!response.ok) {
          close();
          return;
        }
        const body = await response.json();
        if (query !== lastQuery) return;
        render(Array.isArray(body) ? body : []);
      } catch (error) {
        if (error.name !== "AbortError") close();
      }
    };

    input.addEventListener("input", () => {
      const query = input.value.trim();
      lastQuery = query;
      window.clearTimeout(timer);
      if (query.length < 2) {
        close();
        return;
      }
      timer = window.setTimeout(() => load(query), 220);
    });

    input.addEventListener("keydown", (event) => {
      if (panel.hidden) return;
      if (event.key === "ArrowDown") { event.preventDefault(); setActive(activeIndex + 1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); setActive(activeIndex - 1); }
      else if (event.key === "Escape") { close(); }
      else if (event.key === "Enter" && activeIndex >= 0) {
        const active = options()[activeIndex];
        if (active) { event.preventDefault(); window.location.assign(active.href); }
      }
    });

    input.addEventListener("blur", () => window.setTimeout(close, 120));
    document.addEventListener("click", (event) => {
      if (!wrapper.contains(event.target)) close();
    });
  });
})();
