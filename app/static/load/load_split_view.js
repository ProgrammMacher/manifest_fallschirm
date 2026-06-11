// C:\manifest_fallschirm\app\static\load\load_split_view.js
(() => {
  "use strict";

  const root = document.getElementById("load-view-root");
  if (!root) return;

  const listPane = document.getElementById("list-pane");
  const editorPane = document.getElementById("editor-pane");
  const divider = document.getElementById("split-divider");
  const toggleBtn = document.getElementById("toggle-split-view"); // optional

  if (!listPane || !editorPane || !divider) return;

  // ---------------------------------------------------------
  // ✅ Split-View URL-State normalisieren:
  // - Wenn edit=<id> gesetzt ist, darf new=1 nicht mehr aktiv sein
  // ---------------------------------------------------------
  (function normalizeSplitUrlState() {
    try {
      const u = new URL(window.location.href);
      const edit = (u.searchParams.get("edit") || "").trim();
      const isNew = u.searchParams.get("new") === "1";
      if (edit && isNew) {
        u.searchParams.delete("new");
        window.location.replace(u.toString());
      }
    } catch (_) {}
  })();

  // Storage-Key nur für Split-Breite
  const SPLIT_WIDTH_KEY = "manifest_split_view_width_v1";

  // Mindestbreiten (dein aktueller Stand)
  const MIN_LIST_PX = 280;
  const MIN_EDITOR_PX = 420;
  const EXTRA_GAP_PX = 0;
  const DEFAULT_SPLIT_RATIO = 0.60;

  function rootWidthPx() {
    const w = root.getBoundingClientRect().width;
    return Number.isFinite(w) ? w : 0;
  }

  function dividerWidthPx() {
    const w = divider.getBoundingClientRect().width;
    return Number.isFinite(w) ? w : 0;
  }

  function splitAllowed() {
    const w = rootWidthPx();
    return w >= (MIN_LIST_PX + MIN_EDITOR_PX + dividerWidthPx() + EXTRA_GAP_PX);
  }

  // --- Initialzustand merken (Template bestimmt Startzustand!) ---
  const initial = {
    listHidden: !!listPane.hidden,
    editorHidden: !!editorPane.hidden,
    dividerHidden: !!divider.hidden,
    rootView: root.dataset?.view || ""
  };

  function clampWidth(px) {
    const w = rootWidthPx();
    const minWidth = MIN_LIST_PX;
    const maxWidth = Math.max(
      minWidth,
      w - (MIN_EDITOR_PX + dividerWidthPx() + EXTRA_GAP_PX)
    );
    const n = Number(px);
    if (!Number.isFinite(n)) return minWidth;
    return Math.max(minWidth, Math.min(n, maxWidth));
  }

  function setListWidthPx(px) {
    const clamped = clampWidth(px);
    // ✅ robust: Breite explizit setzen
    listPane.style.width = `${Math.round(clamped)}px`;
    listPane.style.flex = "0 0 auto";
    listPane.style.minWidth = `${MIN_LIST_PX}px`;
  }

  function getSavedSplitWidthPx() {
    try {
      const raw = localStorage.getItem(SPLIT_WIDTH_KEY);
      const savedPx = raw ? parseInt(raw, 10) : 0;
      if (Number.isFinite(savedPx) && savedPx > 0) return savedPx;
      return 0;
    } catch (_) {
      return 0;
    }
  }

  function saveSplitWidthPx(px) {
    try {
      localStorage.setItem(SPLIT_WIDTH_KEY, String(Math.round(px)));
    } catch (_) {}
  }

  function ensureSplitLayoutApplied() {
    const wantsSplit = (root.dataset.view === "split");
    if (!wantsSplit) return;

    if (!splitAllowed()) {
      divider.hidden = true;
      return;
    }

    listPane.hidden = false;
    listPane.style.overflowX = listPane.style.overflowX || "auto";
    listPane.style.overflowY = listPane.style.overflowY || "auto";
    listPane.style.minWidth = `${MIN_LIST_PX}px`;
    listPane.style.minHeight = "0";

    editorPane.hidden = false;
    editorPane.style.minWidth = `${MIN_EDITOR_PX}px`;
    editorPane.style.overflowY = editorPane.style.overflowY || "auto";
    editorPane.style.overflowX = editorPane.style.overflowX || "hidden";
    editorPane.style.minHeight = "0";

    divider.hidden = false;

    const saved = getSavedSplitWidthPx();
    if (saved > 0) {
      setListWidthPx(saved);
    } else {
      const w = rootWidthPx();
      setListWidthPx(Math.round(w * DEFAULT_SPLIT_RATIO));
    }
  }

  function applyNormalFromInitial() {
    root.dataset.view = "normal";

    listPane.hidden = initial.listHidden;
    listPane.style.flex = "";
    listPane.style.width = "";
    listPane.style.minWidth = "";
    listPane.style.minHeight = "";

    editorPane.hidden = initial.editorHidden;
    editorPane.style.minWidth = "";
    editorPane.style.minHeight = "";

    divider.hidden = true;

    if (toggleBtn) {
      toggleBtn.textContent = ">>> Split‑View >>>";
      toggleBtn.disabled = false;
      toggleBtn.title = "Split-View ein- oder ausblenden";
    }
  }

  function applySplit() {
    if (!splitAllowed()) {
      if (toggleBtn) {
        toggleBtn.disabled = true;
        toggleBtn.title = "Split-View benötigt mehr Platz (Fenster breiter machen).";
      }
      return;
    }
    root.dataset.view = "split";
    ensureSplitLayoutApplied();
    if (toggleBtn) {
      toggleBtn.disabled = false;
      toggleBtn.title = "Split-View ein- oder ausblenden";
      toggleBtn.textContent = "<<< Split‑View <<<";
    }
  }

  function updateSplitStateOnResize() {
    if (root.dataset.view === "split") {
      if (!splitAllowed()) {
        divider.hidden = true;
        if (toggleBtn) {
          toggleBtn.disabled = true;
          toggleBtn.title = "Split-View benötigt mehr Platz (Fenster breiter machen).";
        }
        return;
      }

      if (toggleBtn) {
        toggleBtn.disabled = false;
        toggleBtn.title = "Split-View ein- oder ausblenden";
      }

      const currentPx = Math.round(listPane.getBoundingClientRect().width);
      if (!Number.isFinite(currentPx) || currentPx < MIN_LIST_PX) {
        const w = rootWidthPx();
        setListWidthPx(Math.round(w * DEFAULT_SPLIT_RATIO));
        return;
      }

      const clamped = clampWidth(currentPx);
      if (Math.abs(clamped - currentPx) >= 2) setListWidthPx(clamped);

      divider.hidden = false;
    } else {
      if (toggleBtn) {
        toggleBtn.disabled = false;
        toggleBtn.title = "Split-View ein- oder ausblenden";
      }
    }
  }

  /* ---------------------------------------------------------
     Divider per Maus verschiebbar + Persistenz
  --------------------------------------------------------- */
  let __splitDragging = false;
  let __splitStartX = 0;
  let __splitStartWidth = 0;

  divider.addEventListener("mousedown", (ev) => {
    if (root.dataset.view !== "split") return;

    __splitDragging = true;
    __splitStartX = ev.clientX;
    __splitStartWidth = listPane.getBoundingClientRect().width;

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    ev.preventDefault();
  });

  document.addEventListener("mousemove", (ev) => {
    if (!__splitDragging) return;
    const delta = ev.clientX - __splitStartX;
    const newWidth = __splitStartWidth + delta;
    setListWidthPx(newWidth);
  });

  document.addEventListener("mouseup", () => {
    if (!__splitDragging) return;
    __splitDragging = false;

    document.body.style.cursor = "";
    document.body.style.userSelect = "";

    const px = Math.round(listPane.getBoundingClientRect().width);
    saveSplitWidthPx(px);
  });

  // Optional: Toggle innerhalb einer Seite (falls vorhanden)
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (toggleBtn.disabled) return;
      const isSplit = root.dataset.view === "split";
      if (isSplit) applyNormalFromInitial();
      else applySplit();
    });
  }

  window.addEventListener("resize", updateSplitStateOnResize);

  // Initial
  if (root.dataset.view === "split") {
    ensureSplitLayoutApplied();
    if (toggleBtn) {
      toggleBtn.textContent = "<<< Split‑View <<<";
      toggleBtn.title = "Split-View ein- oder ausblenden";
    }
  } else {
    if (toggleBtn) applyNormalFromInitial();
  }
  updateSplitStateOnResize();

  // ---------------------------------------------------------
  // ✅ (aus der "gross" Datei) Split-View: Load in der Liste anklicken -> rechts Editor öffnen
  // Erwartet <tr data-load-id="..."> in der Liste.
  // ---------------------------------------------------------
  function getShowParam() {
    try {
      const u = new URL(window.location.href);
      return u.searchParams.get("show") || "active";
    } catch (_) {
      return "active";
    }
  }

  function bindRowClickToEdit() {
    if (!listPane) return;
    if (root.dataset.view !== "split") return;

    listPane.addEventListener(
      "click",
      (ev) => {
        const t = ev.target;
        if (!t) return;

        // Nicht auslösen bei Klick auf echte Buttons/Links/Inputs
        if (t.closest("a, button, input, select, textarea, label")) return;

        const tr = t.closest('tr[data-load-id]');
        if (!tr) return;

        const loadId = tr.getAttribute("data-load-id");
        if (!loadId) return;

        const show = getShowParam();
        const url = new URL(window.location.origin + "/loads/split");
        url.searchParams.set("show", show);
        url.searchParams.set("edit", loadId);
        window.location.href = url.toString();
      },
      { passive: true }
    );
  }

  bindRowClickToEdit();

  // ---------------------------------------------------------
  // ✅ (aus der "gross" Datei) UX: nach edit=<id> zur Zeile scrollen + kurz hervorheben
  // ---------------------------------------------------------
  (function highlightEditedLoad() {
    try {
      const params = new URLSearchParams(window.location.search);
      const editId = params.get("edit");
      if (!editId) return;

      const row = document.querySelector(`tr[data-load-id="${editId}"]`);
      if (!row) return;

      row.scrollIntoView({ behavior: "smooth", block: "center" });
      row.classList.add("table-success");
      setTimeout(() => row.classList.remove("table-success"), 2500);
    } catch (e) {
      console.warn("Highlight new load failed:", e);
    }
  })();

})();