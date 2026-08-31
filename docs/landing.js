(() => {
  "use strict";

  const carousel = document.querySelector("[data-use-case-carousel]");
  if (!carousel) return;

  const slides = [...carousel.querySelectorAll("[data-carousel-slide]")];
  const dots = [...carousel.querySelectorAll("[data-carousel-dot]")];
  const status = carousel.querySelector("[data-carousel-status]");
  const mode = carousel.querySelector("[data-carousel-mode]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let current = 0;
  let timer = null;
  let manuallyStopped = reducedMotion;

  const show = (index, announce = false) => {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, slideIndex) => {
      const active = slideIndex === current;
      slide.hidden = !active;
      slide.setAttribute("aria-hidden", String(!active));
    });
    dots.forEach((dot, dotIndex) => {
      if (dotIndex === current) dot.setAttribute("aria-current", "true");
      else dot.removeAttribute("aria-current");
    });
    if (announce) status.textContent = `Showing use case ${current + 1} of ${slides.length}.`;
  };

  const pause = () => {
    window.clearInterval(timer);
    timer = null;
  };

  const play = () => {
    if (manuallyStopped || timer || document.hidden) return;
    mode.textContent = "Auto";
    timer = window.setInterval(() => show(current + 1), 6000);
  };

  const stop = () => {
    manuallyStopped = true;
    pause();
    mode.textContent = "Manual";
  };

  carousel.querySelector("[data-carousel-previous]").addEventListener("click", () => {
    stop();
    show(current - 1, true);
  });
  carousel.querySelector("[data-carousel-next]").addEventListener("click", () => {
    stop();
    show(current + 1, true);
  });
  dots.forEach((dot, index) => dot.addEventListener("click", () => {
    stop();
    show(index, true);
  }));

  carousel.addEventListener("mouseenter", pause);
  carousel.addEventListener("mouseleave", play);
  carousel.addEventListener("focusin", pause);
  carousel.addEventListener("focusout", (event) => {
    if (!carousel.contains(event.relatedTarget)) play();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
    else play();
  });

  show(0);
  if (reducedMotion) mode.textContent = "Manual";
  else play();
})();
