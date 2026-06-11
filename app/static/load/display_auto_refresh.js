// C:\manifest_fallschirm\app\static\load\display_auto_refresh.js
(() => {
  "use strict";

  // ✅ konsistent: 30 Sekunden
  const REFRESH_MS = 30000;

  const WRAP_SELECTOR = ".display-list-wrap";
  const LIST_SELECTOR = ".load-list-container";
  const STATE_SELECTOR = "#displayState";

  function bust(url) {
    const u = new URL(url, window.location.href);
    u.searchParams.set("_ts", String(Date.now()));
    return u.toString();
  }

  // schneller, deterministischer Hash (kein Crypto; reicht für Change-Detection)
  function hashString(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0).toString(16);
  }

  function stateSignatureFromEl(el) {
    if (!el) return "no-state";
    const c = el.dataset.current || "";
    const n = el.dataset.next || "";
    const ns = el.dataset.nextStart || "";
    return `${c}\n${n}\n${ns}`;
  }

  function isDisplayQuerPage() {
    try {
      // robust: funktioniert lokal & hinter Proxy
      const p = (window.location.pathname || "").toLowerCase();
      return p.includes("display-quer");
    } catch (_) {
      return false;
    }
  }

  let lastSig = ""; // merkt letzte Kombination aus State + Liste

  async function refreshDisplayOnce() {
    const wrap = document.querySelector(WRAP_SELECTOR);
    if (!wrap) return;

    const list = wrap.querySelector(LIST_SELECTOR);
    const oldScroll = list ? list.scrollTop : 0;

    // Soll: wenn Countdown==0, weiterhin refreshen (auch wenn nichts erkennbar geändert)
    const countdownZero =
      typeof window.displayIsCountdownZero === "function"
        ? window.displayIsCountdownZero()
        : false;

    const forceAlwaysPatch = isDisplayQuerPage();

    try {
      const res = await fetch(bust(window.location.href), {
        cache: "no-store",
        credentials: "same-origin"
      });
      if (!res.ok) return;

      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, "text/html");

      const newWrap = doc.querySelector(WRAP_SELECTOR);
      if (!newWrap) return;

      const newList = newWrap.querySelector(LIST_SELECTOR);
      if (!newList) return;

      // ✅ State aus neuer Seite ziehen
      const newStateEl = doc.querySelector(STATE_SELECTOR);
      const newStateSig = stateSignatureFromEl(newStateEl);

      // ✅ Liste hashen (echte Änderungen erkennen)
      const newListHtml = newList.innerHTML || "";
      const newListHash = hashString(newListHtml);
      const newSig = `${newStateSig}::${newListHash}`;

      // Nur patchen wenn:
      // - Display-Quer: IMMER (damit Änderungen sofort sichtbar sind)
      // - oder Countdown==0
      // - oder Signatur geändert
      if (!forceAlwaysPatch && !countdownZero && lastSig && newSig === lastSig) {
        return;
      }

      // ✅ State im aktuellen Dokument aktualisieren
      const oldStateEl = document.querySelector(STATE_SELECTOR);
      if (oldStateEl && newStateEl) {
        oldStateEl.dataset.current = newStateEl.dataset.current || "";
        oldStateEl.dataset.next = newStateEl.dataset.next || "";
        oldStateEl.dataset.nextStart = newStateEl.dataset.nextStart || "";
      }

      // ✅ Liste aktualisieren + Scrollposition erhalten
      if (list) {
        list.innerHTML = newListHtml;
        list.scrollTop = oldScroll;
      } else {
        wrap.innerHTML = newWrap.innerHTML;
      }

      // ✅ vorhandene Hooks weiter nutzen
      if (typeof window.refreshLoadBlockColors === "function") {
        window.refreshLoadBlockColors(wrap);
      }
      if (typeof window.displayApplyMarkers === "function") {
        window.displayApplyMarkers();
      }

      // ✅ Event feuern, damit Seiten-spezifische Hooks nach AutoRefresh laufen
      document.dispatchEvent(new Event("display:refreshed"));

      lastSig = newSig;
    } catch (e) {
      console.warn("Display auto-refresh failed:", e);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    // externe Trigger (z.B. Countdown==0 in display.html)
    window.forceDisplayRefresh = refreshDisplayOnce;

    // initialer kurzer Refresh
    setTimeout(refreshDisplayOnce, 400);

    // Polling
    setInterval(refreshDisplayOnce, REFRESH_MS);
  });
})();