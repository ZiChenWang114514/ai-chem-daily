(() => {
  const KEY = "aix-daily.theme.v1";
  const LABELS = {
    system: "外观：跟随系统",
    light: "外观：浅色",
    dark: "外观：深色",
  };

  function pref() {
    try {
      const value = localStorage.getItem(KEY);
      return value === "light" || value === "dark" ? value : "system";
    } catch {
      return "system";
    }
  }

  function resolved(value = pref()) {
    if (value === "dark" || value === "light") return value;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function apply(value = pref()) {
    const mode = resolved(value);
    document.documentElement.dataset.theme = mode;
    document.documentElement.dataset.themePref = value;
    document.documentElement.style.colorScheme = mode;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = mode === "dark" ? "#0d141c" : "#122033";
    document.querySelectorAll("[data-theme-button]").forEach((button) => {
      button.setAttribute("aria-label", LABELS[value] || LABELS.system);
      button.dataset.themePref = value;
      button.textContent = "外观";
    });
    return value;
  }

  function cycle() {
    const order = ["system", "light", "dark"];
    const next = order[(order.indexOf(pref()) + 1) % order.length];
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* ignore quota */
    }
    return apply(next);
  }

  function bind() {
    document.querySelectorAll("[data-theme-button]").forEach((button) => {
      if (button.dataset.bound === "1") return;
      button.dataset.bound = "1";
      button.addEventListener("click", cycle);
    });
    apply(pref());
  }

  window.AixTheme = { KEY, LABELS, pref, resolved, apply, cycle, bind };
  apply(pref());
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (pref() === "system") apply("system");
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind, { once: true });
  } else {
    bind();
  }
})();
