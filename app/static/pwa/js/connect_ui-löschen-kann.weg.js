// C:\manifest_fallschirm\app\static\pwa\js\connect_ui.js
(() => {
  "use strict";

  const el = (id) => document.getElementById(id);

  const state = {
    publishedUrl: "",
    recommendedUrl: "",
    conflict: false,
    networkCheckDisabled: false,
    isAdmin: false,
  };

  function setText(id, txt) {
    const e = el(id);
    if (e) e.textContent = txt;
  }

  function setHtml(id, html) {
    const e = el(id);
    if (e) e.innerHTML = html;
  }

  function show(id, on) {
    const e = el(id);
    if (!e) return;
    e.classList.toggle("d-none", !on);
  }

  async function apiGet(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    return r.ok ? r.json() : null;
  }

  async function apiPost(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body || {}),
    });
    const data = await r.json().catch(() => null);
    return { ok: r.ok, data };
  }

  function updatePreview() {
    const img = el("qrPreview");
    if (!img) return;

    // ✅ Bewährtes Verhalten: immer den serverseitigen QR anzeigen
    img.src = "/loads/qr.png?size=220&ts=" + Date.now();
  }

    const encoded = encodeURIComponent(state.publishedUrl);
    img.src = `/loads/qr.png?data=${encoded}&size=220`;
  }

  function updateUI() {
    setText("publishedUrl", state.publishedUrl || "–");

    if (state.publishedUrl) {
      setHtml("publishedMeta", `Veröffentlicht (LOCK). QR bleibt stabil.`);
    } else {
      setText("publishedMeta", "Nicht veröffentlicht.");
    }

    setText("recommendedUrl", state.recommendedUrl || "–");

    setText(
      "recommendedHint",
      state.recommendedUrl
        ? "Diese URL wird für eine neue Veröffentlichung verwendet."
        : "Keine empfohlene URL erkannt (kein nutzbares Netz oder keine IP)."
    );

    show("conflictBox", state.conflict);

    const toggle = el("toggleNetworkCheck");
    if (toggle) {
      toggle.disabled = !state.isAdmin;
      toggle.checked = !!state.networkCheckDisabled;
    }

    setText(
      "adminNote",
      state.isAdmin
        ? (state.networkCheckDisabled
            ? "Netzwerkprüfung ist deaktiviert (Admin). Veröffentlichung kann erzwungen werden."
            : "Netzwerkprüfung ist aktiv.")
        : "Admin-Schalter nur im Admin-Modus verfügbar."
    );

    updatePreview();

    if (!state.publishedUrl) {
      setText(
        "cxStatusText",
        state.recommendedUrl
          ? "Mobiler Zugriff möglich. Du kannst jetzt veröffentlichen."
          : (state.networkCheckDisabled
              ? "Netzprüfung deaktiviert. Veröffentlichung nur mit manueller URL möglich."
              : "Mobiler Zugriff aktuell nicht möglich – bitte Hotspot/WLAN aktivieren.")
      );
    } else if (state.conflict) {
      setText(
        "cxStatusText",
        "⚠️ Konflikt: Empfohlene Adresse weicht von veröffentlichter ab. Display schließen und neu veröffentlichen."
      );
    } else {
      setText("cxStatusText", "QR ist veröffentlicht und stabil.");
    }
  }

  async function refreshStatus() {
    const st = await apiGet("/pwa/publish/status");

    if (!st || !st.ok) {
      setText("cxStatusText", "Status konnte nicht geladen werden.");
      return;
    }

    state.publishedUrl = (st.published_url || "").trim();
    state.recommendedUrl = (st.recommended_url || "").trim();
    state.conflict = !!st.conflict;
    state.networkCheckDisabled = !!st.network_check_disabled;
    state.isAdmin = !!st.is_admin;

    updateUI();
  }

  async function onPublish() {
    const manual = ((el("manualUrl")?.value || "").trim());
    const body = manual ? { url: manual } : {};

    const res = await apiPost("/pwa/publish", body);

    if (!res.ok) {
      const err = res.data && res.data.error ? res.data.error : "unknown";

      if (err === "no_mobile_network") {
        alert("Mobiler Zugriff nicht möglich – bitte Hotspot/WLAN aktivieren (oder Admin: Netzprüfung deaktivieren).");
      } else if (err === "no_url_admin_override_required") {
        alert("Keine IP erkannt. Bitte manuelle URL eintragen (Admin/Override).");
      } else if (err === "loopback_not_allowed") {
        alert("127.0.0.1 ist für mobile Geräte nicht erlaubt. Bitte eine echte IP verwenden.");
      } else {
        alert("Veröffentlichung fehlgeschlagen.");
      }
      return;
    }

    await refreshStatus();
    alert("QR veröffentlicht (LOCK). Display kann jetzt geöffnet werden.");
  }

  async function onClearPublish() {
    const res = await apiPost("/pwa/publish/clear", {});
    if (!res.ok) {
      alert("Konnte Veröffentlichung nicht zurückziehen.");
      return;
    }
    await refreshStatus();
  }

  function onOpenDisplay() {
    if (!state.publishedUrl) {
      alert("Kein QR veröffentlicht. Bitte zuerst veröffentlichen.");
      return;
    }
    window.open("/loads/display", "_blank", "noopener,noreferrer");
  }

  async function onToggleNetworkCheck() {
    const toggle = el("toggleNetworkCheck");
    if (!toggle) return;

    const desiredDisabled = !!toggle.checked;
    const res = await apiPost("/pwa/admin/network-check", { disabled: desiredDisabled });

    if (!res.ok) {
      alert("Admin-Aktion fehlgeschlagen (nur im Admin-Modus erlaubt).");
      toggle.checked = !desiredDisabled;
      return;
    }

    await refreshStatus();
  }

  function onHotspotHint() {
    alert("Hotspot/WLAN prüfen:\n\nWindows: Win+I → Netzwerk & Internet → Mobiler Hotspot.\n\nDanach erneut 'Status' prüfen und veröffentlichen.");
  }

  document.addEventListener("DOMContentLoaded", () => {
    el("btnPublish")?.addEventListener("click", onPublish);
    el("btnClearPublish")?.addEventListener("click", onClearPublish);
    el("btnOpenDisplay")?.addEventListener("click", onOpenDisplay);
    el("toggleNetworkCheck")?.addEventListener("change", onToggleNetworkCheck);
    el("btnHotspotHint")?.addEventListener("click", onHotspotHint);

    refreshStatus();
  });
})();