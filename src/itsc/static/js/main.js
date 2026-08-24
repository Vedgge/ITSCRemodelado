/*
 * ITSC — site behaviour.
 *
 * Everything here is progressive enhancement: each feature layers on top of
 * markup that already works without JavaScript. The pages render server-side,
 * the accordion is a native <details>, and the nav is a plain list of links.
 *
 * Replaces jQuery (loaded on 21 pages, never once called), the Bootstrap
 * bundle (loaded on 21 pages for a single carousel), and seven inline
 * <script> blocks. No inline script means the CSP needs no 'unsafe-inline'.
 */
(function () {
  "use strict";

  /* --- Mobile navigation ------------------------------------------------ */
  function initNav() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.getElementById("nav-principal");
    if (!toggle || !nav) return;

    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute(
        "aria-label",
        open ? "Cerrar menú de navegación" : "Abrir menú de navegación"
      );
    });

    /* On touch/narrow layouts a parent link both navigates and opens a
       submenu. Hover cannot express that, so the first tap expands. */
    nav.querySelectorAll(".nav__item.has-children > a, .nav__item.has-children > .nav__group").forEach(function (link) {
      link.addEventListener("click", function (event) {
        var isButton = link.tagName === "BUTTON";
        /* A group heading has no destination, so it toggles at every width. */
        if (!isButton && !window.matchMedia("(max-width: 900px)").matches) return;
        if (isButton) {
          event.preventDefault();
          var open = link.parentElement.classList.toggle("is-open");
          link.setAttribute("aria-expanded", String(open));
          return;
        }
        var item = link.parentElement;
        if (!item.classList.contains("is-open")) {
          event.preventDefault();
          item.classList.add("is-open");
          link.setAttribute("aria-expanded", "true");
        }
      });
    });

    /* Escape closes any open menu and returns focus to the toggle. */
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      if (nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
      nav.querySelectorAll(".nav__item.is-open").forEach(function (item) {
        item.classList.remove("is-open");
      });
    });

    document.addEventListener("click", function (event) {
      if (!nav.contains(event.target) && !toggle.contains(event.target)) {
        nav.querySelectorAll(".nav__item.is-open").forEach(function (item) {
          item.classList.remove("is-open");
        });
      }
    });
  }

  /* --- Destructive-action confirmation ---------------------------------- */
  function initConfirms() {
    /* The form still POSTs with a CSRF token if this never runs; the dialog is
       a courtesy, not the security control. The old code relied on
       window.confirm() around an unauthenticated fetch(method:'DELETE'). */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });
  }

  /* --- Reveal-on-scroll -------------------------------------------------- */
  function initReveal() {
    /* The original had this check commented out, so the animation ran even for
       users who had explicitly asked for reduced motion. */
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!("IntersectionObserver" in window)) return;

    var targets = document.querySelectorAll(".card, .carrera-tile, .gallery-item");
    if (!targets.length) return;

    targets.forEach(function (el) {
      el.style.opacity = "0";
      el.style.transform = "translateY(12px)";
      el.style.transition = "opacity .4s ease, transform .4s ease";
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.style.opacity = "1";
          entry.target.style.transform = "none";
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -40px 0px", threshold: 0.05 }
    );
    targets.forEach(function (el) { observer.observe(el); });
  }

  /* --- Search box: trim before submitting -------------------------------- */
  function initSearch() {
    document.querySelectorAll('form[role="search"]').forEach(function (form) {
      form.addEventListener("submit", function (event) {
        var input = form.querySelector('input[type="search"]');
        if (!input) return;
        input.value = input.value.trim();
        if (!input.value) {
          event.preventDefault();
          input.focus();
        }
      });
    });
  }

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    initNav();
    initConfirms();
    initReveal();
    initSearch();
  });
})();
