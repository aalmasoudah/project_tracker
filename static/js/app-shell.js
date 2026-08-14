(function () {
  "use strict";

  const storageKey = "insight-sidebar-collapsed";
  const toggle = document.getElementById("sidebar-toggle");
  if (!toggle) {
    return;
  }

  function setCollapsed(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    toggle.setAttribute(
      "aria-label",
      collapsed ? toggle.dataset.labelExpand : toggle.dataset.labelCollapse
    );
    toggle.querySelector("span").textContent = collapsed ? "⇥" : "⇤";
  }

  try {
    setCollapsed(window.localStorage.getItem(storageKey) === "true");
  } catch (_error) {
    setCollapsed(false);
  }

  toggle.addEventListener("click", function () {
    const collapsed = !document.body.classList.contains("sidebar-collapsed");
    setCollapsed(collapsed);
    try {
      window.localStorage.setItem(storageKey, String(collapsed));
    } catch (_error) {
      // The layout still works when storage is unavailable.
    }
  });
})();
