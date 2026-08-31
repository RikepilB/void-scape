(() => {
  "use strict";

  const root = document.documentElement;
  const preference = window.matchMedia("(prefers-color-scheme: light)");
  root.dataset.theme = preference.matches ? "light" : "dark";

  const updateControls = () => {
    const current = root.dataset.theme;
    document.querySelectorAll("[data-site-theme-toggle]").forEach((button) => {
      const next = current === "light" ? "dark" : "light";
      button.setAttribute("aria-label", `Switch to ${next} mode`);
      button.setAttribute("title", `Switch to ${next} mode`);
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    updateControls();
    document.querySelectorAll("[data-site-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
        updateControls();
      });
    });

    const backToTop = document.createElement("button");
    backToTop.className = "back-to-top";
    backToTop.type = "button";
    backToTop.textContent = "↑";
    backToTop.setAttribute("aria-label", "Back to top");
    document.body.appendChild(backToTop);

    const updateBackToTop = () => backToTop.classList.toggle("visible", window.scrollY > 700);
    window.addEventListener("scroll", updateBackToTop, { passive: true });
    backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    updateBackToTop();
  });
})();
