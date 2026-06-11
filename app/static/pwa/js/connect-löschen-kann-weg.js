/* ============================================================
   Connect – Mobile-First (Internet irrelevant)
   Ziele:
   - App darf NIE hängen/frieren
   - Checks kurz, begrenzt, abbrechbar
   - KEIN Internet-Check (WWW ist irrelevant)
   - Fokus: Server erreichbar? Mobile Zugriff möglich? QR veröffentlicht? Konflikt?
   - QR wird hier NICHT geändert (nur Status/Overlay)
============================================================ */
(function () {
  "use strict";

  // -------------------------------
  // Konfiguration (minimal, sicher)
  // -------------------------------
  const CFG = {
    backendHealthUrls: ["/pwa/health"],      // schnell, lokal
    publishStatusUrl: "/pwa/publish/status",
    timeoutBackendMs: 800,
    timeoutStatusMs: 900,
    debug: true,
  };

  // -------------------------------
  // States
  // init      = wird ermittelt
  // local     = mobiler Zugriff möglich / QR ok / bereit
  // required  = kein nutzbares mobiles Netzwerk (Hotspot/WLAN nötig)
  // offline   = Server nicht erreichbar
  // hidden    = Overlay versteckt
  // -------------------------------
  const VALID_STATES = new Set(["init", "hidden", "local", "required", "offline"]);

  const byId = (id) => document.getElementById(id);
  const safeText = (el, text) => { if (el) el.textContent = text; };

  function uiFor(state, meta) {
    const conflict = !!(meta && meta.conflict);
    const publishedUrl = (meta && meta.published_url) ? String(meta.published_url) : "";
    const checkDisabled = !!(meta && meta.network_check_disabled);

    if (state === "offline") {
      return {
        overlayVisible: true,
        icon: "🔴",
        title: "Serverfehler",
        text: "Der lokale Server ist nicht erreichbar. Mobiler Zugriff nicht möglich.",
        statusIcon: "🔴",
        statusTitle: "Mobiler Zugriff",
        statusText: "Serverfehler – mobiler Zugriff nicht möglich.",
      };
    }

    if (state === "required") {
      return {
        overlayVisible: true,
        icon: "🟠",
        title: "Kein Netzwerk für mobile Geräte",
        text: checkDisabled
          ? "Netzwerkprüfung ist deaktiviert (Admin). Veröffentlichung ist möglich, aber es wird eine gültige IP/URL benötigt."
          : "Mobiler Zugriff nicht möglich – bitte WLAN oder Hotspot aktivieren.",
        statusIcon: "🟠",
        statusTitle: "Mobiler Zugriff",
        statusText: checkDisabled
          ? "Netzwerkprüfung deaktiviert (Admin)."
          : "Mobiler Zugriff nicht möglich – bitte Hotspot/WLAN aktivieren.",
      };
    }

    // state === "local"
    if (conflict) {
      return {
        overlayVisible: true,
        icon: "⚠️",
        title: "Adresse hat sich geändert",
        text: "Der veröffentlichte QR-Code bleibt stabil. Für eine neue Adresse: Display schließen und in der PWA neu veröffentlichen.",
        statusIcon: "⚠️",
        statusTitle: "Mobiler Zugriff",
        statusText: "Konflikt: Adresse geändert – Display schließen & neu veröffentlichen.",
      };
    }

    if (publishedUrl) {
      return {
        overlayVisible: false,
        icon: "✅",
        title: "QR veröffentlicht",
        text: "Der QR-Code ist veröffentlicht und bleibt stabil.",
        statusIcon: "✅",
        statusTitle: "Mobiler Zugriff",
        statusText: "QR veröffentlicht (LOCK) – stabil.",
      };
    }

    return {
      overlayVisible: false,
      icon: "🟡",
      title: "Bereit",
      text: "Mobiler Zugriff ist möglich. QR kann in der PWA veröffentlicht werden.",
      statusIcon: "🟡",
      statusTitle: "Mobiler Zugriff",
      statusText: "Bereit – QR kann veröffentlicht werden.",
    };
  }

  function clearActions(actionsEl) {
    if (actionsEl) actionsEl.innerHTML = "";
  }

  function setOverlayVisible(visible) {
    const overlay = byId("connect-overlay");
    if (!overlay) return;
    overlay.setAttribute("data-connect-state", visible ? "visible" : "hidden");
  }

  function renderActionsFor(state, meta) {
    const overlay = byId("connect-overlay");
    if (!overlay) return;
    const actionsEl = overlay.querySelector(".connect-actions");
    if (!actionsEl) return;

    clearActions(actionsEl);

    function addBtn(label, onClick, klass = "btn btn-outline-secondary btn-sm") {
      const b = document.createElement("button");
      b.type = "button";
      b.className = klass;
      b.textContent = label;
      b.addEventListener("click", onClick);
      actionsEl.appendChild(b);
    }

    addBtn("Status neu prüfen", () => runHealthCheckOnce(), "btn btn-dark btn-sm");

    const conflict = !!(meta && meta.conflict);
    if (state === "required" || conflict) {
      addBtn("Mobiler Zugriff öffnen", () => {
        window.location.href = "/pwa/connectivity";
      }, "btn btn-outline-primary btn-sm");
    }

    addBtn("Schließen", () => setOverlayVisible(false), "btn btn-outline-secondary btn-sm");
  }

  function updateOverlay(state, meta) {
    const overlay = byId("connect-overlay");
    if (!overlay) return;

    const titleEl = overlay.querySelector(".connect-title");
    const iconEl = overlay.querySelector(".connect-icon");
    const textEl = overlay.querySelector(".connect-text");

    const ui = uiFor(state, meta);

    overlay.setAttribute("data-connect-state", ui.overlayVisible ? "visible" : "hidden");
    safeText(titleEl, ui.title || "Verbindung prüfen");
    safeText(iconEl, ui.icon || "");
    safeText(textEl, ui.text || "");

    renderActionsFor(state, meta);
  }

  function updateStatusBox(state, meta) {
    const box = byId("connect-status");
    if (!box) return;

    const ui = uiFor(state, meta);
    box.setAttribute("data-connect-state", state);

    const iconSpan = box.querySelector("span");
    const titleDiv = box.querySelector(".fw-semibold");
    const textDiv = box.querySelector(".small");

    safeText(iconSpan, ui.statusIcon || "⏳");
    safeText(titleDiv, ui.statusTitle || "Mobiler Zugriff");
    safeText(textDiv, ui.statusText || "Status wird ermittelt…");
  }

  function setState(state, meta) {
    const next = VALID_STATES.has(state) ? state : "init";
    try {
      updateOverlay(next, meta);
      updateStatusBox(next, meta);
      window.__connectState = next;
      window.__connectMeta = meta || null;
      if (CFG.debug) console.debug("[connect] state =", next, meta || "");
    } catch (e) {
      window.__connectState = "init";
      if (CFG.debug) console.debug("[connect] state error -> init", e);
    }
  }

  // -------------------------------
  // Abbruchsteuerung
  // -------------------------------
  let activeRunId = 0;
  let activeAbort = null;

  function cancelActive(reason = "cancelled") {
    activeRunId++;
    try { if (activeAbort) activeAbort.abort(reason); } catch (_) {}
    activeAbort = null;
    if (CFG.debug) console.debug("[connect] cancelled:", reason);
  }

  // -------------------------------
  // Fetch mit hartem Timeout
  // -------------------------------
  async function fetchWithHardTimeout(url, options, ms, label, signal) {
    const controller = new AbortController();
    const t = setTimeout(() => {
      try { controller.abort("timeout"); } catch (_) {}
    }, ms);

    if (signal) {
      if (signal.aborted) {
        clearTimeout(t);
        return { ok: false, aborted: true, label };
      }
      signal.addEventListener("abort", () => {
        try { controller.abort("cancelled"); } catch (_) {}
      }, { once: true });
    }

    try {
      const res = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(t);
      return { ok: true, res, label };
    } catch (e) {
      clearTimeout(t);
      const aborted = !!controller.signal.aborted;
      return { ok: false, aborted, label };
    }
  }

  // -------------------------------
  // Backend Health
  // -------------------------------
  async function checkBackend(signal) {
    for (const url of CFG.backendHealthUrls) {
      const out = await fetchWithHardTimeout(
        url,
        { method: "GET", cache: "no-store", credentials: "same-origin" },
        CFG.timeoutBackendMs,
        "backend",
        signal
      );
      if (out && out.ok && out.res && out.res.ok) {
        return { ok: true, status: out.res.status };
      }
    }
    return { ok: false };
  }

  // -------------------------------
  // Publish Status
  // -------------------------------
  async function checkPublishStatus(signal) {
    const out = await fetchWithHardTimeout(
      CFG.publishStatusUrl,
      { method: "GET", cache: "no-store", credentials: "same-origin" },
      CFG.timeoutStatusMs,
      "publish-status",
      signal
    );
    if (!out || !out.ok || !out.res || !out.res.ok) return { ok: false };
    const data = await out.res.json().catch(() => null);
    if (!data || !data.ok) return { ok: false };
    return { ok: true, data };
  }

  // -------------------------------
  // Run checks once
  // -------------------------------
  async function runHealthCheckOnce() {
    cancelActive("new-run");
    const runId = activeRunId;

    const controller = new AbortController();
    activeAbort = controller;

    setState("init", null);

    const backend = await checkBackend(controller.signal);
    if (runId !== activeRunId) return;

    if (!backend.ok) {
      setState("offline", null);
      return;
    }

    const st = await checkPublishStatus(controller.signal);
    if (runId !== activeRunId) return;

    if (!st.ok) {
      setState("required", { network_check_disabled: false });
      return;
    }

    const meta = st.data || {};
    const publishedUrl = (meta.published_url || "").trim();
    const recommendedReachable = !!meta.recommended_mobile_reachable;
    const checkDisabled = !!meta.network_check_disabled;
    const conflict = !!meta.conflict;

    if (conflict) { setState("local", meta); return; }
    if (publishedUrl) { setState("local", meta); return; }

    if (checkDisabled) {
      setState(recommendedReachable ? "local" : "required", meta);
      return;
    }

    setState(recommendedReachable ? "local" : "required", meta);
  }

  // -------------------------------
  // Public API
  // -------------------------------
  window.connectSetState = setState;
  window.connectRunHealthCheckOnce = runHealthCheckOnce;
  window.connectCancel = cancelActive;

  // -------------------------------
  // Lifecycle Trigger (minimal, ohne Polling)
  // -------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    runHealthCheckOnce();
  });

  window.addEventListener("online", () => {
    runHealthCheckOnce();
  });

  window.addEventListener("offline", () => {
    runHealthCheckOnce();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      runHealthCheckOnce();
    }
  });

})();