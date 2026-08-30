(() => {
  "use strict";

  const body = document.body;
  const root = body.dataset.docsRoot || "";
  const menuToggle = document.querySelector("[data-menu-toggle]");
  const menuClose = document.querySelector("[data-menu-close]");
  const menuScrim = document.querySelector("[data-menu-scrim]");
  const sidebar = document.querySelector(".docs-sidebar");
  const mobileNavigation = window.matchMedia("(max-width: 760px)");
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const searchLayer = document.querySelector("[data-search-layer]");
  const searchInput = document.querySelector("#docs-search");
  const searchResults = document.querySelector("[data-search-results]");
  let searchIndex = [];
  let selectedResult = 0;
  let previousFocus = null;

  const syncSidebarAccessibility = (open = body.classList.contains("menu-open")) => {
    const hidden = mobileNavigation.matches && !open;
    if (sidebar) sidebar.inert = hidden;
    sidebar?.setAttribute("aria-hidden", String(hidden));
  };

  const setMenu = (open) => {
    body.classList.toggle("menu-open", open);
    menuToggle?.setAttribute("aria-expanded", String(open));
    if (menuScrim) menuScrim.hidden = !open;
    syncSidebarAccessibility(open);
  };

  menuToggle?.addEventListener("click", () => setMenu(!body.classList.contains("menu-open")));
  menuClose?.addEventListener("click", () => setMenu(false));
  menuScrim?.addEventListener("click", () => setMenu(false));
  document.querySelectorAll(".docs-sidebar a").forEach((link) => link.addEventListener("click", () => setMenu(false)));
  mobileNavigation.addEventListener("change", () => setMenu(false));
  syncSidebarAccessibility();

  themeToggle?.addEventListener("click", () => {
    const light = document.documentElement.dataset.theme !== "light";
    document.documentElement.dataset.theme = light ? "light" : "dark";
    themeToggle.setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
  });

  const fallbackCopy = (text) => {
    const input = document.createElement("textarea");
    input.value = text;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    input.remove();
  };

  document.querySelectorAll(".copy-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.closest(".code-block")?.querySelector("pre code")?.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
      } catch (_error) {
        fallbackCopy(text);
      }
      button.textContent = "Copied";
      button.classList.add("copied");
      window.setTimeout(() => {
        button.textContent = "Copy";
        button.classList.remove("copied");
      }, 1400);
    });
  });

  const resultNodes = () => [...searchResults.querySelectorAll(".search-result")];

  const selectResult = (index) => {
    const nodes = resultNodes();
    if (!nodes.length) return;
    selectedResult = Math.max(0, Math.min(index, nodes.length - 1));
    nodes.forEach((node, itemIndex) => node.classList.toggle("selected", itemIndex === selectedResult));
    nodes[selectedResult].scrollIntoView({ block: "nearest" });
  };

  const scoreEntry = (entry, tokens) => {
    const title = entry.title.toLocaleLowerCase();
    const description = entry.description.toLocaleLowerCase();
    const text = entry.text.toLocaleLowerCase();
    if (!tokens.every((token) => title.includes(token) || description.includes(token) || text.includes(token))) return -1;
    return tokens.reduce((score, token) => score + (title.includes(token) ? 8 : 0) + (description.includes(token) ? 3 : 0) + (text.includes(token) ? 1 : 0), 0);
  };

  const renderResults = () => {
    const query = searchInput.value.trim().toLocaleLowerCase();
    const tokens = query.split(/\s+/).filter(Boolean);
    const entries = tokens.length
      ? searchIndex.map((entry) => ({ entry, score: scoreEntry(entry, tokens) })).filter((item) => item.score >= 0).sort((a, b) => b.score - a.score).slice(0, 10).map((item) => item.entry)
      : searchIndex.filter((entry) => ["Overview", "Quick start", "Workflow and protocol", "Troubleshooting"].includes(entry.title));

    searchResults.replaceChildren();
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "search-empty";
      empty.textContent = `No agent docs match “${searchInput.value.trim()}”.`;
      searchResults.appendChild(empty);
      return;
    }

    entries.forEach((entry, index) => {
      const link = document.createElement("a");
      link.className = "search-result";
      link.href = `${root}${entry.url}`;
      link.setAttribute("role", "option");
      const category = document.createElement("span");
      category.textContent = entry.category;
      const title = document.createElement("strong");
      title.textContent = entry.title;
      const description = document.createElement("p");
      description.textContent = entry.description;
      link.append(category, title, description);
      link.addEventListener("mouseenter", () => selectResult(index));
      searchResults.appendChild(link);
    });
    selectedResult = 0;
    selectResult(0);
  };

  const loadSearch = async () => {
    if (searchIndex.length) return;
    searchResults.innerHTML = '<p class="search-empty">Loading local index…</p>';
    try {
      const response = await fetch(`${root}_assets/search-index.json`);
      if (!response.ok) throw new Error(`Search index returned ${response.status}`);
      searchIndex = await response.json();
      renderResults();
    } catch (_error) {
      searchResults.innerHTML = '<p class="search-empty">Search index unavailable. Use the navigation menu.</p>';
    }
  };

  const openSearch = async () => {
    previousFocus = document.activeElement;
    searchLayer.hidden = false;
    body.classList.add("search-open");
    await loadSearch();
    searchInput.focus();
    searchInput.select();
  };

  const closeSearch = () => {
    searchLayer.hidden = true;
    body.classList.remove("search-open");
    searchInput.value = "";
    previousFocus?.focus();
  };

  document.querySelectorAll("[data-search-open]").forEach((button) => button.addEventListener("click", openSearch));
  document.querySelectorAll("[data-search-close]").forEach((button) => button.addEventListener("click", closeSearch));
  searchInput?.addEventListener("input", renderResults);
  searchInput?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      selectResult(selectedResult + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      selectResult(selectedResult - 1);
    } else if (event.key === "Enter") {
      const selected = resultNodes()[selectedResult];
      if (selected) {
        event.preventDefault();
        window.location.href = selected.href;
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
      event.preventDefault();
      if (searchLayer.hidden) openSearch();
      else closeSearch();
    }
    if (event.key === "Escape") {
      if (!searchLayer.hidden) closeSearch();
      else setMenu(false);
    }
  });

  const tocLinks = [...document.querySelectorAll(".page-toc a")];
  const headings = [...document.querySelectorAll(".docs-article h2[id], .docs-article h3[id]")];
  if ("IntersectionObserver" in window && headings.length) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      tocLinks.forEach((link) => link.classList.toggle("active", link.hash === `#${visible.target.id}`));
    }, { rootMargin: "-80px 0px -70% 0px", threshold: [0, 1] });
    headings.forEach((heading) => observer.observe(heading));
  }
})();
