// === MANIFEST FILE START: app/static/load/load_editor.js ===
// C:\manifest_fallschirm\app\static\load\load_editor.js
(() => {
  "use strict";

  // ---------------------------------------------------------------------------
  // 1) Konstanten
  // ---------------------------------------------------------------------------
  const STUDENT_STATUSES = ["Schüler", "Schüler Ek 1", "Schüler Ek 2", "Schüler GK 6"];
  const TD_STATUSES = ["TD", "TD-Vereins-Schirm"];
  const VIDEO_STATUS_CODES = ["Video", "Videomann"]; // historisch
  const TANDEM_ROLE_STATUSES = ["G-TD", "G-TD-Video", "TD", "TD-Vereins-Schirm", "Video", "Videomann"];
  const TANDEM_GUEST_ALLOWED_STATUSES = ["G-TD", "G-TD-Video", "Mitflieger"]; // Tandemgäste (alle Arten)
  const TANDEMMASTER_STATUSES = ["TD", "TD-Vereins-Schirm"];
  const AFF_TEACHER_STATUS = "AFF-LEHRER";
  const AFF_STUDENT_STATUSES = ["SCHUELER-AFF-1", "SCHUELER-AFF-2"];
  const MEMBER_ONLY_STATUSES = ["Verein", "Auffüller Verein"];
  const PARTNER_ONLY_STATUSES = ["Partner-Verein", "Auffüller Partner-Verein"];
  const GUEST_ONLY_STATUSES = ["Gast", "Auffüller Gast"];
  const TANDEM_PALETTE_SIZE = 10;
  const INSTRUCTION_PALETTE_SIZE = 5;
  const CLIPBOARD_KEY = "manifest_load_clipboard_v1";

  // Draft / Restore
  const DRAFT_PREFIX = "manifest_load_editor_draft_v1:";
  const LAST_SUBMIT_PREFIX = "manifest_load_editor_last_submit_v1:";
  const AUTO_RESTORE_WINDOW_MS = 5 * 60 * 1000; // 5 Minuten
  const DRAFT_SAVE_DEBOUNCE_MS = 250;

  // UX Hint (einmal pro Page Load)
  const FILL_HINT_DURATION_MS = 4000;
  const MAX_EXTRA_SEATS_PER_LOAD = 4;

  // Nur diese Höhen sind im UI/Backend sinnvoll
  const VALID_HEIGHTS = new Set([1500, 3000, 4000]);

  // Schirmmiete (gear_rental)
  const GEAR_RENTAL_FIELD_ALIASES = ["gear_rental", "schirmmiete", "rental"];

  // ---------------------------------------------------------------------------
  // 2) State
  // ---------------------------------------------------------------------------
  let currentLoadHeight = null;
  let statusList = [];
  const seatStatusListCache = Object.create(null);
  const personCache = Object.create(null);
  let instructionWarnTwoTeachers = false;
  let lastPayloadTotal = 0;
  let lastMaxPayload = 0;
  let __autoLoadHeightInProgress = false;

  // Draft state
  let __draftSaveTimer = null;
  let __pageLoadedAt = Date.now();

  // Guard: doppelte Bindings vermeiden
  let __submitGuardBound = false;
  let __maxPayloadBound = false;
  let __aircraftVisibilityBound = false;

  // ---------------------------------------------------------------------------
  // 3) Kleine Utils
  // ---------------------------------------------------------------------------
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const safeInt = (v, def = 0) => {
    const n = parseInt(String(v ?? "").trim(), 10);
    return Number.isFinite(n) ? n : def;
  };
  const safeStr = (v) => String(v ?? "").trim();

  // ✅ wird von computeWarnings() benutzt
  function count(entries, statuses) {
    const list = Array.isArray(entries) ? entries : [];
    const wanted = new Set(
      (Array.isArray(statuses) ? statuses : [])
        .map(safeStr)
        .filter(Boolean)
    );
    let n = 0;
    for (const e of list) {
      if (!e) continue;
      if (wanted.has(safeStr(e.status))) n++;
    }
    return n;
  }

  function nowMs() {
    return Date.now();
  }

  function getSaveForm() {
    return (
      qs("#load-save-form") ||
      qs('form[action*="/loads/"][action*="/save"]') ||
      qs("form")
    );
  }

  function getLoadIdFromFormAction() {
    const form = getSaveForm();
    const action = safeStr(form?.getAttribute("action"));
    const m = action.match(/\/loads\/(\d+)\/save/);
    return m ? m[1] : null;
  }

  function draftKey(loadId) {
    return `${DRAFT_PREFIX}${loadId}`;
  }

  function submitKey(loadId) {
    return `${LAST_SUBMIT_PREFIX}${loadId}`;
  }

  function setLastSubmitNow(loadId) {
    try {
      localStorage.setItem(submitKey(loadId), String(nowMs()));
    } catch (_) {}
  }

  function getLastSubmitMs(loadId) {
    try {
      const raw = localStorage.getItem(submitKey(loadId));
      const n = raw ? parseInt(raw, 10) : 0;
      return Number.isFinite(n) ? n : 0;
    } catch (_) {
      return 0;
    }
  }

  function clearLastSubmit(loadId) {
    try {
      localStorage.removeItem(submitKey(loadId));
    } catch (_) {}
  }

  // Base seat count aus aktuellem Aircraft-Select (Optionstext: "(n Sitze)")
  function getBaseSeatCount() {
    const aircraftSelect = qs('select[name="aircraft_id"]');
    if (!aircraftSelect) {
      const seats = qsa("tr.seat-row[data-seat]")
        .map((r) => safeInt(r.dataset.seat, 0))
        .filter((n) => n > 0);
      return seats.length ? Math.max(...seats) : 0;
    }
    const opt = aircraftSelect.options[aircraftSelect.selectedIndex];
    const txt = opt ? opt.textContent : "";
    const m = String(txt).match(/\((\d+)\s*Sitze\)/i);
    if (m) return safeInt(m[1], 0);

    const maxSeat = Math.max(...qsa("tr.seat-row[data-seat]").map((r) => safeInt(r.dataset.seat, 0)), 0);
    return maxSeat > 2 ? (maxSeat - 2) : maxSeat;
  }

  function areAllBaseSeatsFilled() {
    const base = getBaseSeatCount();
    if (!base) return false;
    for (let s = 1; s <= base; s++) {
      const hid = qs(`#seat_${s}_person`);
      if (!hid || !safeStr(hid.value)) return false;
    }
    return true;
  }

  // Extrasitz-UI: hidden input (editor_inner.html)
  function getExtraSeatsUiCount() {
    const hidden = qs("#extra_seats_ui");
    if (!hidden) return 0;
    const v = safeInt(hidden.value, 0);
    return Math.max(0, Math.min(MAX_EXTRA_SEATS_PER_LOAD, v));
  }

  function setExtraSeatsUiCount(n) {
    const hidden = qs("#extra_seats_ui");
    if (!hidden) return;
    const v = Math.max(0, Math.min(MAX_EXTRA_SEATS_PER_LOAD, safeInt(n, 0)));
    hidden.value = String(v);
  }

  function getOccupiedExtraSeatCount(baseSeatCount = getBaseSeatCount()) {
    if (!baseSeatCount) return 0;
    let occupied = 0;
    for (let seat = baseSeatCount + 1; seat <= baseSeatCount + MAX_EXTRA_SEATS_PER_LOAD; seat++) {
      if (isSeatRowOccupied(seat)) occupied += 1;
    }
    return Math.max(0, Math.min(MAX_EXTRA_SEATS_PER_LOAD, occupied));
  }

  function syncExtraSeatsUiCount(baseSeatCount = getBaseSeatCount()) {
    const synced = Math.max(getExtraSeatsUiCount(), getOccupiedExtraSeatCount(baseSeatCount));
    setExtraSeatsUiCount(synced);
    return synced;
  }

  function updateExtraSeatButtonState(baseSeatCount = getBaseSeatCount()) {
    const button = qs("#add_extra_seat");
    if (!button) return;
    const current = syncExtraSeatsUiCount(baseSeatCount);
    const locked = button.dataset.locked === "1";
    button.disabled = locked || current >= MAX_EXTRA_SEATS_PER_LOAD;
    if (current >= MAX_EXTRA_SEATS_PER_LOAD) {
      button.setAttribute("aria-disabled", "true");
      button.title = `Maximal ${MAX_EXTRA_SEATS_PER_LOAD} Extrasitze pro Load.`;
    } else {
      button.removeAttribute("aria-disabled");
      button.removeAttribute("title");
    }
  }

  function bindExtraSeatButton() {
    const button = qs("#add_extra_seat");
    if (!button || button.dataset.bound === "1") return;
    button.dataset.bound = "1";
    button.dataset.locked = button.disabled ? "1" : "0";

    updateExtraSeatButtonState();

    button.addEventListener("click", () => {
      const baseSeatCount = getBaseSeatCount();
      const current = syncExtraSeatsUiCount(baseSeatCount);
      if (current >= MAX_EXTRA_SEATS_PER_LOAD) {
        updateExtraSeatButtonState(baseSeatCount);
        return;
      }
      setExtraSeatsUiCount(current + 1);
      const aircraftSelect = qs('select[name="aircraft_id"]');
      if (aircraftSelect) {
        aircraftSelect.dispatchEvent(new Event("change"));
      } else {
        updateExtraSeatButtonState(baseSeatCount);
        updateLiveLogic();
        scheduleDraftSave();
      }
    });
  }

  function isSeatRowOccupied(seatNo) {
    const hid = qs(`#seat_${seatNo}_person`);
    return !!(hid && safeStr(hid.value));
  }

  function normalizeHeightValue(h) {
    const n = safeInt(h, 0);
    return VALID_HEIGHTS.has(n) ? n : 0;
  }

  function seatFromId(id, suffix) {
    const m = String(id ?? "").match(new RegExp(`^seat_(\\d+)_${suffix}$`));
    return m ? safeInt(m[1], 0) : 0;
  }

// ---------------------------------------------------------------------------
// 4) DOM Helper pro Seat
// ---------------------------------------------------------------------------
function elPersonInput(seat) { return qs(`input.person-input[data-seat="${seat}"]`); }
function elPersonId(seat) { return qs(`#seat_${seat}_person`); }
function elStatus(seat) { return qs(`#seat_${seat}_status_code`); }
function elHeight(seat) { return qs(`#seat_${seat}_height_m`); }
function elLoadHeight() { return qs("#load_height_m"); }

// ✅ Schritt 4 (UI/UX): Placeholder für Ampel/Hint unter dem Personfeld
// (wird in editor_inner.html als <div id="seat_{{seat}}_validity_hints"> gerendert)
function elValidityHints(seat) { return qs(`#seat_${seat}_validity_hints`); }

  // ---------------------------------------------------------------------------
  // 5) Invalid-Person: rot hinterlegen
  // ---------------------------------------------------------------------------
  function setInvalidPersonVisual(inputEl, isInvalid) {
    if (!inputEl) return;
    inputEl.classList.toggle("invalid-person", !!isInvalid);
    inputEl.classList.toggle("is-invalid", !!isInvalid);
    inputEl.setAttribute("aria-invalid", isInvalid ? "true" : "false");
  }

  function evalInvalidPersonForSeat(seat) {
    const input = elPersonInput(seat);
    const hid = elPersonId(seat);
    if (!input) return false;
    const name = safeStr(input.value);
    const pid = safeStr(hid?.value);
    const invalid = !!(name && !pid);
    setInvalidPersonVisual(input, invalid);
    return invalid;
  }

  function clearInvalidPersonForSeat(seat) {
    const input = elPersonInput(seat);
    if (!input) return;
    setInvalidPersonVisual(input, false);
  }

  // ---------------------------------------------------------------------------
  // 6) Schirmmiete (gear_rental) UI
  // ---------------------------------------------------------------------------
  function isStatusForbiddenForGearRental(statusCode) {
    const st = safeStr(statusCode);
    if (!st) return true;
    if (isStudentStatusAny(st)) return true;
    if (TANDEM_GUEST_ALLOWED_STATUSES.includes(st)) return true;
    return false;
  }

  function ensureGearRentalSlot(seat) {
    const statusSel = elStatus(seat);
    if (!statusSel) return null;
    const wrap = statusSel.parentElement;
    if (!wrap) return null;
    let slot = wrap.querySelector(`.gear-rental-slot[data-seat="${seat}"]`);
    if (slot) return slot;
    slot = document.createElement("div");
    slot.className = "gear-rental-slot mt-1";
    slot.dataset.seat = String(seat);
    wrap.appendChild(slot);
    return slot;
  }

  function removeGearRentalUi(seat) {
    const slot = ensureGearRentalSlot(seat);
    if (!slot) return;
    slot.innerHTML = "";
  }

  function getGearRentalInputName(seat) {
    return `seat_${seat}_gear_rental`;
  }

  function findInitialGearRentalFromDataset(seat) {
    const sel = elStatus(seat);
    if (!sel || !sel.dataset) return null;
    const raw = safeStr(sel.dataset.gearRentalInitial);
    if (!raw) return null;
    return ["1", "true", "on", "yes", "ja"].includes(raw.toLowerCase());
  }

  function findExistingGearRentalValue(seat) {
    const name = getGearRentalInputName(seat);
    const slot = ensureGearRentalSlot(seat);
    if (slot) {
      const cbInSlot = slot.querySelector(`input[type="checkbox"][name="${CSS.escape(name)}"]`);
      if (cbInSlot) return !!cbInSlot.checked;
      const hiddenInSlot = slot.querySelector(`input[type="hidden"][name="${CSS.escape(name)}"]`);
      if (hiddenInSlot) {
        const v = safeStr(hiddenInSlot.value);
        if (!v) return false;
        return ["1", "true", "on", "yes", "ja"].includes(v.toLowerCase());
      }
    }
    const el = qs(`[name="${CSS.escape(name)}"]`);
    if (!el) return null;
    if (el.type === "checkbox") return !!el.checked;
    const v = safeStr(el.value);
    if (!v) return false;
    return ["1", "true", "on", "yes", "ja"].includes(v.toLowerCase());
  }

  function renderGearRentalUi(seat, { checked = null } = {}) {
    const slot = ensureGearRentalSlot(seat);
    if (!slot) return;
    const status = safeStr(elStatus(seat)?.value);
    if (isStatusForbiddenForGearRental(status)) {
      slot.innerHTML = "";
      return;
    }

    let isChecked = false;
    if (checked !== null) {
      isChecked = !!checked;
    } else {
      const existing = findExistingGearRentalValue(seat);
      if (existing !== null) {
        isChecked = !!existing;
      } else {
        const init = findInitialGearRentalFromDataset(seat);
        if (init !== null) isChecked = !!init;
      }
    }

    slot.innerHTML = "";
    const id = `seat_${seat}_gear_rental_cb`;
    const name = getGearRentalInputName(seat);

    const div = document.createElement("div");
    div.className = "form-check";
    div.innerHTML = `
      <input class="form-check-input" type="checkbox" id="${id}" name="${name}" value="1">
      <input type="hidden" name="${name}" value="0">
      <label class="form-check-label" for="${id}">Schirmmiete</label>
    `;
    slot.appendChild(div);

    const cb = qs(`#${CSS.escape(id)}`, slot);
    if (cb) {
      cb.checked = !!isChecked;
      cb.addEventListener("change", () => {
        scheduleDraftSave();
      });
    }
  }

  function parseGearRentalFromPayload(entry) {
    if (!entry) return null;
    const raw =
      (entry.gearRental !== undefined) ? entry.gearRental :
      (entry.gear_rental !== undefined) ? entry.gear_rental :
      (entry.gearRentalChecked !== undefined) ? entry.gearRentalChecked :
      null;
    if (raw === null) return null;
    if (raw === true) return true;
    if (raw === false) return false;
    const s = String(raw).trim().toLowerCase();
    return (s === "1" || s === "true" || s === "on" || s === "yes" || s === "ja");
  }

  function getGearRentalForSeatSerialize(seat) {
    const existing = findExistingGearRentalValue(seat);
    if (existing !== null) return !!existing;
    const init = findInitialGearRentalFromDataset(seat);
    if (init !== null) return !!init;
    return false;
  }

  // ---------------------------------------------------------------------------
  // 7) UX: Ausfüllhinweis (einmal pro Seite)
  // ---------------------------------------------------------------------------
  function ensureFillHintStyles() {
    if (qs("#fill-hint-styles")) return;
    const style = document.createElement("style");
    style.id = "fill-hint-styles";
    style.textContent = `
      .fill-hint-pop{
        position:fixed; z-index:9999; max-width:340px;
        background:rgba(31,41,55,0.98); color:#fff;
        padding:10px 12px; border-radius:12px;
        box-shadow:0 12px 28px rgba(0,0,0,0.25);
        font-size:0.9rem; line-height:1.25;
        pointer-events:none;
        opacity:0; transform:translateY(-2px);
        transition:opacity 140ms ease, transform 140ms ease;
      }
      .fill-hint-pop.show{ opacity:1; transform:translateY(0); }
      .fill-hint-pop .title{ font-weight:800; margin:0 0 4px 0; letter-spacing:0.2px; }
      .fill-hint-pop .body{ margin:0; opacity:0.95; }
    `;
    document.head.appendChild(style);
  }

  function positionFillHint(anchorEl, hintEl) {
    if (!anchorEl || !hintEl) return;
    const rect = anchorEl.getBoundingClientRect();
    const vw = window.innerWidth || document.documentElement.clientWidth;
    const hintW = hintEl.offsetWidth || 340;
    const hintH = hintEl.offsetHeight || 90;
    const gap = 10;

    let top = rect.top - hintH - gap;
    if (top < 8) top = rect.bottom + gap;
    let left = rect.left;
    left = Math.max(8, Math.min(left, vw - hintW - 8));

    hintEl.style.left = `${Math.round(left)}px`;
    hintEl.style.top = `${Math.round(top)}px`;
  }

  function showFillHintOnce(anchorEl, message) {
    if (window.__loadEditorFillHintShown) return;
    window.__loadEditorFillHintShown = true;
    ensureFillHintStyles();
    const hintEl = document.createElement("div");
    hintEl.className = "fill-hint-pop";
    hintEl.innerHTML = `<div class="title">Ausfüllhinweis</div><p class="body"></p>`;
    hintEl.querySelector(".body").textContent = message;
    document.body.appendChild(hintEl);

    const reflow = () => positionFillHint(anchorEl, hintEl);
    reflow();
    hintEl.classList.add("show");

    const onScroll = () => reflow();
    const onResize = () => reflow();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize, true);

    window.setTimeout(() => {
      hintEl.classList.remove("show");
      window.setTimeout(() => {
        window.removeEventListener("scroll", onScroll, true);
        window.removeEventListener("resize", onResize, true);
        hintEl.remove();
      }, 180);
    }, FILL_HINT_DURATION_MS);
  }

  function maybeTriggerFillHintFromPerson(inputEl, seat) {
    if (!inputEl) return;
    const pid = safeStr(elPersonId(seat)?.value);
    if (!pid) return;
    showFillHintOnce(
      inputEl,
      "Person und Status kannst du in beliebiger Reihenfolge setzen. Tipp: Wählst du zuerst den Status, wird die Personenliste automatisch gefiltert (z.B. Verein/Gast/Lehrer)."
    );
  }

  function maybeTriggerFillHintFromStatus(selectEl) {
    if (!selectEl) return;
    if (!safeStr(selectEl.value)) return;
    showFillHintOnce(
      selectEl,
      "Tipp: Wenn du zuerst den Status wählst, wird die Personenliste automatisch gefiltert. Danach Person auswählen oder umgekehrt – beides ist möglich."
    );
  }

  // ---------------------------------------------------------------------------
  // 8) Statusliste (Backend)
  // ---------------------------------------------------------------------------
  async function loadStatusList() {
    try {
      const res = await fetch("/loads/api/status/list");
      if (!res.ok) throw new Error("status list http " + res.status);
      const data = await res.json();
      statusList = Array.isArray(data) ? data : [];
      Object.keys(seatStatusListCache).forEach((k) => { delete seatStatusListCache[k]; });
    } catch (err) {
      console.error("Konnte Statusliste nicht laden:", err);
      statusList = [];
      Object.keys(seatStatusListCache).forEach((k) => { delete seatStatusListCache[k]; });
    }
  }

  function statusLabelFor(s) {
    const code = safeStr(s?.code);
    const label = safeStr(s?.label);
    if (label === "Videomann" || code === "Videomann") return "Video";
    return label || code;
  }

  function getStatusLabelByCode(code, sourceStatuses = null) {
    const list = Array.isArray(sourceStatuses) ? sourceStatuses : statusList;
    const c = safeStr(code);
    const found = list.find((s) => safeStr(s?.code) === c);
    return safeStr(found?.label) || c;
  }

  function isAffTeacherStatus(code) {
    return safeStr(code).toUpperCase() === AFF_TEACHER_STATUS;
  }

  function isAffStudentStatus(code) {
    return AFF_STUDENT_STATUSES.includes(safeStr(code).toUpperCase());
  }

  function isStudentStatusAny(code) {
    const st = safeStr(code);
    return STUDENT_STATUSES.includes(st) || isAffStudentStatus(st);
  }

  function isTeacherStatusAny(code, sourceStatuses = null) {
    const st = safeStr(code);
    if (isAffStudentStatus(st)) return false;
    if (st === "Lehrer" || isAffTeacherStatus(st)) return true;

    const cu = st.toUpperCase();
    const lu = getStatusLabelByCode(st, sourceStatuses).toUpperCase();
    return cu.includes("LEHRER") || lu.includes("LEHRER");
  }

  function ensureStatusOption(selectEl, code, label = null) {
    if (!selectEl) return;
    const c = safeStr(code);
    if (!c) return;

    const exists = Array.from(selectEl.options).some((o) => safeStr(o.value) === c);
    if (exists) return;

    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = safeStr(label) || c;
    selectEl.appendChild(opt);
  }

  function populateStatusSelect(selectEl, allowedCodes = null, sourceStatuses = null) {
    if (!selectEl) return;
    const list = Array.isArray(sourceStatuses) ? sourceStatuses : statusList;
    const previous = safeStr(selectEl.value);
    const initial = safeStr(selectEl.dataset.initial);

    selectEl.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "– auswählen –";
    selectEl.appendChild(placeholder);

    for (const s of list) {
      const code = safeStr(s.code);

      // Tandem (Vereins-Schirm) nicht mehr anbieten
      if (code === "TD-Vereins-Schirm") continue;
      if (allowedCodes && !allowedCodes.includes(code)) continue;

      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = statusLabelFor(s);
      selectEl.appendChild(opt);
    }

    // Legacy-/Kopierstatus erhalten, auch wenn er aktuell nicht in statusList enthalten ist.
    if (previous) ensureStatusOption(selectEl, previous, previous);
    if (initial) ensureStatusOption(selectEl, initial, initial);

    if (selectEl.dataset.initial && selectEl.dataset.initialApplied !== "1") {
      selectEl.value = selectEl.dataset.initial;
      selectEl.dataset.initialApplied = "1";
    } else {
      selectEl.value = previous;
    }
  }

  // ---------------------------------------------------------------------------
  // 9) Person Cache (Backend)
  // ---------------------------------------------------------------------------
  async function getPerson(personId) {
    const pid = safeStr(personId);
    if (!pid) return null;
    if (personCache[pid]) return personCache[pid];

    try {
      const res = await fetch(`/loads/api/person/${encodeURIComponent(pid)}`);
      if (res.ok) {
        const p = await res.json();
        personCache[pid] = p;
        return p;
      }
    } catch (_) {}

    try {
      const res = await fetch(`/loads/api/person/search?q=${encodeURIComponent(pid)}`);
      if (!res.ok) return null;
      const persons = await res.json();
      if (!Array.isArray(persons)) return null;
      const p = persons.find((x) => safeStr(x.id) === pid);
      if (p) {
        personCache[safeStr(p.id)] = p;
        return p;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  async function preloadPersons(personIds) {
    const ids = Array.from(new Set(personIds.map(safeStr).filter(Boolean)));
    const missing = ids.filter((id) => !personCache[id]);
    if (!missing.length) return;
    await Promise.all(missing.map((id) => getPerson(id).catch(() => null)));
  }

  async function loadSeatStatusList(seat, personId = "", personObj = null) {
    const pid = safeStr(personId);
    const p = personObj || (pid ? await getPerson(pid) : null);

    let slot = "";
    if (p) {
      const hasTeacher = !!(p.is_teacher || p.is_aff_teacher);
      const hasStudent = !!(p.is_student || p.is_aff_student);
      if (hasTeacher && !hasStudent) slot = "teacher";
      else if (hasStudent && !hasTeacher) slot = "student";
    }

    const cacheKey = `${slot || "any"}|${pid || "none"}`;
    if (seatStatusListCache[cacheKey]) {
      return seatStatusListCache[cacheKey].slice();
    }

    const params = new URLSearchParams();
    if (slot) params.set("slot", slot);
    if (pid) params.set("person_id", pid);
    const url = params.toString() ? `/loads/api/status/list?${params.toString()}` : "/loads/api/status/list";

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("status list seat http " + res.status);
      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      seatStatusListCache[cacheKey] = list.slice();
      return list;
    } catch (_) {
      return [];
    }
  }

  // ---------------------------------------------------------------------------
  // 10) Regeln: erlaubte Status / erlaubte Personen
  // ---------------------------------------------------------------------------

  /**
   * ✅ Schritt 3 Änderung:
   * - Wenn eine Person Lehrer ist, aber teacher_license_valid == false,
   *   soll der Status "Lehrer" NICHT auswählbar sein (Frontend-UX).
   * - Dafür muss die API teacher_license_valid liefern (Schritt 2).
   */
  function allowedStatusesForPerson(p, sourceStatuses = null) {
    const list = Array.isArray(sourceStatuses) ? sourceStatuses : statusList;
    let allowed = list.map((s) => safeStr(s.code)).filter(Boolean);
    if (p && p.deleted_at) return [];

    if (p && p.is_tandem_guest) {
      allowed = allowed.filter((c) => TANDEM_GUEST_ALLOWED_STATUSES.includes(c));
    } else {
      allowed = allowed.filter((c) => !TANDEM_GUEST_ALLOWED_STATUSES.includes(c));
    }

    if (p && !p.is_tandemmaster) {
      allowed = allowed.filter((c) => !TANDEMMASTER_STATUSES.includes(c));
    }

    if (p && !p.is_video) {
      allowed = allowed.filter((c) => !VIDEO_STATUS_CODES.includes(c));
    }

    const hasStudent = !!(p && (p.is_student || p.is_aff_student));
    const hasTeacher = !!(p && (p.is_teacher || p.is_aff_teacher));

    if (p && hasStudent && !hasTeacher) {
      allowed = allowed.filter((c) => isStudentStatusAny(c));
    }
    if (p && hasTeacher && !hasStudent) {
      allowed = allowed.filter((c) => !isStudentStatusAny(c));
    }

    if (p && !hasTeacher) {
      allowed = allowed.filter((c) => c !== "Lehrer" && !isAffTeacherStatus(c));
    }
    if (p && hasTeacher) {
      if (!p.is_teacher) {
        allowed = allowed.filter((c) => c !== "Lehrer");
      }
      if (!p.is_aff_teacher) {
        allowed = allowed.filter((c) => !isAffTeacherStatus(c));
      }

      // Lehrer ohne gültige Lizenz dürfen nicht als "Lehrer" eingetragen werden
      if (p.teacher_license_valid === false) {
        allowed = allowed.filter((c) => c !== "Lehrer");
      }
    }

    if (p && !hasStudent) {
      allowed = allowed.filter((c) => !isStudentStatusAny(c));
    }
    if (p && hasStudent) {
      if (!p.is_student) {
        allowed = allowed.filter((c) => !STUDENT_STATUSES.includes(c));
      }
      if (!p.is_aff_student) {
        allowed = allowed.filter((c) => !isAffStudentStatus(c));
      }
    }

    if (p && p.is_partner_verein) {
      allowed = allowed.filter((c) => !MEMBER_ONLY_STATUSES.includes(c));
      allowed = allowed.filter((c) => !GUEST_ONLY_STATUSES.includes(c));
    } else if (p && p.is_member) {
      allowed = allowed.filter((c) => !GUEST_ONLY_STATUSES.includes(c));
      allowed = allowed.filter((c) => !PARTNER_ONLY_STATUSES.includes(c));
    } else {
      allowed = allowed.filter((c) => !MEMBER_ONLY_STATUSES.includes(c));
      allowed = allowed.filter((c) => !PARTNER_ONLY_STATUSES.includes(c));
    }

    return allowed;
  }

  /**
   * ✅ Schritt 3 Änderung:
   * - Prüft jetzt zusätzlich teacher_license_valid beim Status "Lehrer"
   * - Enthaftung (liability_waiver_valid) bleibt verpflichtend für Nicht-Tandemgäste
   *   (Tandemgäste werden über TANDEM_GUEST_ALLOWED_STATUSES geregelt)
   */
  function personAllowedForStatus(p, statusCode) {
    if (!p) return false;
    if (p.deleted_at) return false;

    const st = safeStr(statusCode);
    if (!st) return true;

    // Tandemgäste: nur in diesen Statusen
    if (p.is_tandem_guest) {
      return TANDEM_GUEST_ALLOWED_STATUSES.includes(st);
    }
    if (TANDEM_GUEST_ALLOWED_STATUSES.includes(st)) return false;

    if (TANDEMMASTER_STATUSES.includes(st) && !p.is_tandemmaster) return false;
    if (VIDEO_STATUS_CODES.includes(st) && !p.is_video) return false;

    const hasStudent = !!(p.is_student || p.is_aff_student);
    const hasTeacher = !!(p.is_teacher || p.is_aff_teacher);

    if (isAffTeacherStatus(st) && !p.is_aff_teacher) return false;
    if (isAffStudentStatus(st) && !p.is_aff_student) return false;

    if (STUDENT_STATUSES.includes(st) && !p.is_student) return false;
    if (st === "Lehrer" && !p.is_teacher) return false;

    if (!hasStudent && isStudentStatusAny(st)) return false;
    if (!hasTeacher && isTeacherStatusAny(st)) return false;

    if (hasStudent && !hasTeacher && isTeacherStatusAny(st)) return false;
    if (hasTeacher && !hasStudent && isStudentStatusAny(st)) return false;

    // Mitglied/Gast Mapping
    if (MEMBER_ONLY_STATUSES.includes(st)) {
      if (!p.is_member) return false;
    }
    if (PARTNER_ONLY_STATUSES.includes(st)) {
      if (!p.is_partner_verein) return false;
    }
    if (GUEST_ONLY_STATUSES.includes(st)) {
      if (p.is_member || p.is_partner_verein) return false;
    }

    // ✅ Enthaftung: für Nicht-Tandemgäste verpflichtend
    if (!p.liability_waiver_valid) return false;

    // ✅ NEU: Lehrerlizenz prüfen (nur wenn Status Lehrer)
    if (st === "Lehrer") {
      // wenn Feld fehlt -> konservativ sperren
      if (p.teacher_license_valid !== true) return false;
    }

    return true;
  }

  // -------------------------------
  // ✅ Auffüller-Regel (global + sitz-/block-basiert)
  // (unverändert)
  // -------------------------------
  function isAuffuellerStatus(code) {
    const c = safeStr(code);
    return c === "Auffüller Verein" || c === "Auffüller Gast" || c === "Auffüller Partner-Verein";
  }

  function isBlockStatusForAuffuellerRule(code) {
    const c = safeStr(code);
    if (!c) return false;

    if (
      c === "G-TD" ||
      c === "G-TD-Video" ||
      c === "TD" ||
      c === "TD-Vereins-Schirm" ||
      c === "Video" ||
      c === "Videomann" ||
      c === "Lehrer" ||
      STUDENT_STATUSES.includes(c) ||
      isAffTeacherStatus(c) ||
      isAffStudentStatus(c)
    ) {
      return true;
    }

    return false;
  }

  function isStatusAllowedInAuffuellerContext(seat, code) {
    const s = safeInt(seat, 0);
    const c = safeStr(code);
    if (!c) return false;

    // WICHTIG: Für die Auswahl dieses Sitzes den aktuellen Sitz aus dem Kontext ausklammern,
    // damit ein bereits gesetzter Nicht-Block-Status am selben Sitz auf Auffueller wechselbar bleibt.
    const entries = collectEntriesFromDom().filter((e) => e.seat !== s);
    const hasAuffuellerInLoad = entries.some((e) => isAuffuellerStatus(e.status));
    const hasNonBlockStatus = entries.some(
      (e) => !isAuffuellerStatus(e.status) && !isBlockStatusForAuffuellerRule(e.status)
    );

    // Sobald ein Nicht-Block-Status im Load vorhanden ist, darf kein Auffueller gesetzt werden.
    if (isAuffuellerStatus(c) && hasNonBlockStatus) {
      return false;
    }

    // Wenn bereits ein Auffueller im Load steht, sind nur Block-Status zulaessig.
    // (Auffueller selbst wird in applyStatusFilterForSeat separat ueber isAuffuellerAllowedForSeat geregelt.)
    if (hasAuffuellerInLoad && !isAuffuellerStatus(c) && !isBlockStatusForAuffuellerRule(c)) {
      return false;
    }

    return true;
  }

  /**
    * Auto-Bestimmung des Default-Status.
    *
    * Regel:
    * - Nur wenn nach Status-Filter genau ein Status verfügbar ist,
    *   wird dieser automatisch vorausgewählt.
    * - Sonst keine automatische Vorauswahl.
   */




  function computeDefaultStatusForPerson(person, availableStatusCodes = null) {
    if (!person) return null;
    if (person.deleted_at) return null;

    // Wenn nach Filterung nur ein Status übrig bleibt, diesen automatisch setzen
    if (Array.isArray(availableStatusCodes)) {
      const filtered = availableStatusCodes.map(safeStr).filter(Boolean);
      if (filtered.length === 1) {
        return filtered[0];
      }
    }

    // ...Fallback-Logik für Spezialfälle (optional, falls weitere Regeln nötig sind)...
    return null;
  }

  function getInvalidInputAlertMessage(videoRuleBlocked) {
    if (videoRuleBlocked) {
      return "Bitte korrigiere: Ungültige Eingaben. Status Video ist nur zusammen mit G-TD-Video und TD/TD-Vereins-Schirm erlaubt.";
    }
    return "Bitte korrigiere: Ungültige Eingaben.";
  }

  // Dev-Selbsttest fuer die zwei kritischen Faelle im Load-Editor.
  // Aufruf in der Browser-Konsole: window.runLoadEditorStatusSmokeTest()
  if (typeof window.runLoadEditorStatusSmokeTest !== "function") {
    window.runLoadEditorStatusSmokeTest = function runLoadEditorStatusSmokeTest() {
      const results = [];

      const t1 = computeDefaultStatusForPerson({ id: 1, deleted_at: null }, ["Gast"]);
      results.push({
        name: "Auto-Status bei genau einer Option (Gast)",
        ok: t1 === "Gast",
        got: t1,
        expected: "Gast",
      });

      const t2 = computeDefaultStatusForPerson(
        { id: 2, deleted_at: null },
        ["Verein", "Video", "Lehrer"]
      );
      results.push({
        name: "Keine Auto-Auswahl bei mehreren Optionen",
        ok: t2 === null,
        got: t2,
        expected: null,
      });

      const t3 = getInvalidInputAlertMessage(false);
      results.push({
        name: "Generische Fehlermeldung ohne Video-Regelverstoß",
        ok: t3 === "Bitte korrigiere: Ungültige Eingaben.",
        got: t3,
        expected: "Bitte korrigiere: Ungültige Eingaben.",
      });

      const t4 = getInvalidInputAlertMessage(true);
      results.push({
        name: "Spezifische Fehlermeldung bei Video-Regelverstoß",
        ok: t4.indexOf("Status Video ist nur zusammen") >= 0,
        got: t4,
        expected: "...Status Video ist nur zusammen...",
      });

      const failed = results.filter((r) => !r.ok);
      const summary = {
        ok: failed.length === 0,
        total: results.length,
        passed: results.length - failed.length,
        failed: failed.length,
        results,
      };

      try {
        console.table(results.map((r) => ({ Test: r.name, OK: r.ok, Got: r.got, Expected: r.expected })));
      } catch (_) {}

      return summary;
    };
  }

  // ============================================================
  // BLOCK 2A — Statusauswertung nur auf belegten Sitzen
  //
  // Warum:
  // - Auffüller-Regeln und weitere Logik sollen nur echte Einträge berücksichtigen.
  // - "Status zuerst" (ohne Person-ID) darf globale Regeln nicht verfälschen.
  // - collectEntriesFromDom() liefert nur valide Entries (personId + status) und
  //   ignoriert Freitext ohne ID bereits zuverlässig.
  // ============================================================
  function getAllSelectedStatusCodes() {
    const entries = collectEntriesFromDom();
    return entries.map(e => safeStr(e.status)).filter(Boolean);
  }

  function hasAnySelectedStatus(codes) {
    const want = new Set((codes || []).map(safeStr).filter(Boolean));
    return getAllSelectedStatusCodes().some(v => want.has(v));
  }

  function collectEntriesFromDom() {
    const rows = qsa(".seat-row");
    const entries = [];
    for (const row of rows) {
      const seat = safeInt(row.dataset.seat, 0);
      if (!seat) continue;
      const input = elPersonInput(seat);
      const personId = safeStr(elPersonId(seat)?.value);
      const status = safeStr(elStatus(seat)?.value);
      const height = safeInt(elHeight(seat)?.value, 0);

      // Freitext ignorieren
      if (input && safeStr(input.value) && !personId) continue;

      if (!personId || !status) continue;
      entries.push({ seat, personId, status, height, row });
    }
    return entries;
  }

  function computeTandemBlocks(entries) {
    const guestsVideo = entries.filter((e) => e.status === "G-TD-Video").sort((a, b) => a.seat - b.seat);
    const guests = entries.filter((e) => e.status === "G-TD").sort((a, b) => a.seat - b.seat);
    const tds = entries.filter((e) => TD_STATUSES.includes(e.status)).sort((a, b) => a.seat - b.seat);
    const vids = entries.filter((e) => VIDEO_STATUS_CODES.includes(e.status)).sort((a, b) => a.seat - b.seat);

    const usedSeats = new Set();
    const blocks = [];

    function nearestAvailable(target, pool, disallowPersonId = null) {
      let best = null;
      let bestD = null;
      for (const c of pool) {
        if (usedSeats.has(c.seat)) continue;
        if (disallowPersonId && String(c.personId) === String(disallowPersonId)) continue;
        const d = Math.abs(target.seat - c.seat);
        if (best === null || d < bestD || (d === bestD && c.seat < best.seat)) {
          best = c;
          bestD = d;
        }
      }
      return best;
    }

    for (const g of guestsVideo) {
      if (usedSeats.has(g.seat)) continue;
      const td = nearestAvailable(g, tds, g.personId);
      const vid = nearestAvailable(g, vids, g.personId);
      if (td && vid) {
        usedSeats.add(g.seat);
        usedSeats.add(td.seat);
        usedSeats.add(vid.seat);
        blocks.push([g.seat, td.seat, vid.seat]);
      }
    }
    for (const g of guests) {
      if (usedSeats.has(g.seat)) continue;
      const td = nearestAvailable(g, tds, g.personId);
      if (td) {
        usedSeats.add(g.seat);
        usedSeats.add(td.seat);
        blocks.push([g.seat, td.seat]);
      }
    }
    return blocks;
  }

  function computeInstructionBlocks(entries, tandemSeats) {
    const teachers = entries
      .filter((e) => (safeStr(e.status) === "Lehrer" || isAffTeacherStatus(e.status)) && !tandemSeats.has(e.seat))
      .sort((a, b) => a.seat - b.seat);
    const students = entries
      .filter((e) => (STUDENT_STATUSES.includes(safeStr(e.status)) || isAffStudentStatus(e.status)) && !tandemSeats.has(e.seat))
      .sort((a, b) => a.seat - b.seat);

    const blocks = [];
    if (!teachers.length || !students.length) {
      return { blocks, studentSeats: students.map((s) => s.seat) };
    }

    const studentPrimary = new Map();
    const studentToTeachers = new Map();
    const teacherToStudents = new Map();
    teachers.forEach((t) => teacherToStudents.set(t.seat, []));
    students.forEach((s) => studentToTeachers.set(s.seat, []));

    for (const s of students) {
      let bestT = null;
      let bestD = null;
      for (const t of teachers) {
        if (String(t.personId) === String(s.personId)) continue;
        const d = Math.abs(s.seat - t.seat);
        if (bestT === null || d < bestD || (d === bestD && t.seat < bestT.seat)) {
          bestT = t;
          bestD = d;
        }
      }
      if (bestT) {
        studentPrimary.set(s.seat, bestT.seat);
        studentToTeachers.set(s.seat, [bestT.seat]);
        teacherToStudents.get(bestT.seat).push(s.seat);
      }
    }

    for (const t of teachers) {
      const assigned = (teacherToStudents.get(t.seat) || []);
      if (assigned.length > 0) continue;

      // Versuch 1: Reassign eines Schülers von Lehrer mit >1 Schülern.
      let bestStudentSeat = null;
      let bestD = null;
      for (const s of students) {
        const oldT = studentPrimary.get(s.seat);
        if (oldT == null) continue;
        const oldList = teacherToStudents.get(oldT) || [];
        if (oldList.length <= 1) continue;
        const d = Math.abs(s.seat - t.seat);
        if (bestStudentSeat === null || d < bestD) {
          bestStudentSeat = s.seat;
          bestD = d;
        }
      }

      if (bestStudentSeat !== null) {
        const oldT = studentPrimary.get(bestStudentSeat);
        if (oldT != null) {
          teacherToStudents.set(oldT, (teacherToStudents.get(oldT) || []).filter((x) => x !== bestStudentSeat));
        }
        studentPrimary.set(bestStudentSeat, t.seat);
        studentToTeachers.set(bestStudentSeat, [t.seat]);
        teacherToStudents.get(t.seat).push(bestStudentSeat);
        continue;
      }

      // Versuch 2: Secondary-Zuordnung (max. 2 Lehrer pro Schüler).
      let secondarySeat = null;
      let secondaryD = null;
      for (const s of students) {
        if (String(t.personId) === String(s.personId)) continue;
        const assignedTeachers = studentToTeachers.get(s.seat) || [];
        if (assignedTeachers.includes(t.seat)) continue;
        if (assignedTeachers.length >= 2) continue;
        const d = Math.abs(s.seat - t.seat);
        if (secondarySeat === null || d < secondaryD) {
          secondarySeat = s.seat;
          secondaryD = d;
        }
      }
      if (secondarySeat !== null) {
        const assignedTeachers = studentToTeachers.get(secondarySeat) || [];
        studentToTeachers.set(secondarySeat, [...assignedTeachers, t.seat]);
        teacherToStudents.get(t.seat).push(secondarySeat);
      }
    }

    for (const t of teachers) {
      const sts = Array.from(new Set((teacherToStudents.get(t.seat) || []).slice().sort((a, b) => a - b)));
      if (!sts.length) continue;
      blocks.push([t.seat, ...sts]);
    }

    return { blocks, studentSeats: students.map((s) => s.seat) };
  }

  function clearSeatBlockClasses() {
    qsa(".seat-row").forEach((row) => {
      const remove = [];
      row.classList.forEach((c) => {
        if (
          c === "tandem-seat" ||
          c.startsWith("tandem-seat-") ||
          c === "instruction-seat" ||
          c.startsWith("instruction-seat-")
        ) {
          remove.push(c);
        }
      });
      remove.forEach((c) => row.classList.remove(c));
    });
  }

  function hasSeatBlockClass(row, base) {
    if (!row || !row.classList) return false;
    if (row.classList.contains(base)) return true;
    for (const c of row.classList) {
      if (c.startsWith(`${base}-`)) return true;
    }
    return false;
  }

  function addSeatBlockClass(row, base, idx, { skipIfAlready = false } = {}) {
    if (!row || !row.classList) return;
    if (skipIfAlready && hasSeatBlockClass(row, base)) return;
    row.classList.add(base);
    row.classList.add(`${base}-${idx}`);
  }

  function applySeatBlockHighlights(entries) {
    clearSeatBlockClasses();
    if (!Array.isArray(entries) || !entries.length) return;

    const entriesNoAuff = entries.filter((e) => !isAuffuellerStatus(e.status));
    const bySeat = new Map(entriesNoAuff.map((e) => [e.seat, e.row]));

    const tandemBlocks = computeTandemBlocks(entriesNoAuff);
    const tandemSeats = new Set();
    tandemBlocks.forEach((seats) => seats.forEach((seat) => tandemSeats.add(seat)));
    tandemBlocks.forEach((seats, i) => {
      const idx = (i % TANDEM_PALETTE_SIZE) + 1;
      seats.forEach((seat) => addSeatBlockClass(bySeat.get(seat), "tandem-seat", idx));
    });

    const instr = computeInstructionBlocks(entriesNoAuff, tandemSeats);
    let blockNo = 0;
    (instr.blocks || []).forEach((seats) => {
      blockNo += 1;
      const idx = ((blockNo - 1) % INSTRUCTION_PALETTE_SIZE) + 1;
      seats.forEach((seat) => addSeatBlockClass(bySeat.get(seat), "instruction-seat", idx, { skipIfAlready: true }));
    });

    // Schüler (inkl. AFF) generell gelb darstellen, auch ohne erkannten Lehrer-Block.
    (instr.studentSeats || []).forEach((seat) => {
      const row = bySeat.get(seat);
      if (!row) return;
      if (hasSeatBlockClass(row, "tandem-seat")) return;
      if (!hasSeatBlockClass(row, "instruction-seat")) {
        addSeatBlockClass(row, "instruction-seat", 1);
      }
    });
  }

  function getBlockedSeatsForAuffueller() {
    const entriesAll = collectEntriesFromDom();
    const entries = entriesAll.filter((e) => !isAuffuellerStatus(e.status));
    const tandemBlocks = computeTandemBlocks(entries);
    const tandemSeats = new Set();
    tandemBlocks.forEach((block) => block.forEach((seat) => tandemSeats.add(seat)));
    const instr = computeInstructionBlocks(entries, tandemSeats);
    const blocked = new Set(tandemSeats);
    (instr.blocks || []).forEach((block) => block.forEach((seat) => blocked.add(seat)));
    (instr.studentSeats || []).forEach((seat) => blocked.add(seat));
    return blocked;
  }

  function getAuffuellerCandidateSeat() {
    const base = getBaseSeatCount();
    if (!base) return 0;
    const blocked = getBlockedSeatsForAuffueller();
    for (let s = base; s >= 1; s--) {
      if (!blocked.has(s)) return s;
    }
    return 0;
  }

  function isAuffuellerAllowedForSeat(seat) {
    const base = getBaseSeatCount();
    const s = safeInt(seat, 0);
    if (!base || !s) return false;
    if (s > base) return false;

    const currentSeatPersonId = safeStr(elPersonId(s)?.value);
    if (!currentSeatPersonId) return false;

    const auffSeats = qsa(".status-select")
      .map((sel) => ({ seat: seatFromId(sel.id, "status_code"), st: safeStr(sel.value) }))
      .filter((x) => x.seat && isAuffuellerStatus(x.st))
      .map((x) => x.seat);

    if (auffSeats.length > 0 && !auffSeats.includes(s)) return false;
    if (auffSeats.length > 1) return false;

    // Auffueller ist der letzte freie Platz: alle regulaeren Sitze muessen bereits eine Person haben,
    // und ausser dem aktuellen Sitz muessen alle Sitze bereits einen Status haben.
    for (let seatNo = 1; seatNo <= base; seatNo++) {
      const pid = safeStr(elPersonId(seatNo)?.value);
      if (!pid) return false;
      if (seatNo === s) continue;
      const st = safeStr(elStatus(seatNo)?.value);
      if (!st) return false;
    }

    const otherStatuses = [];
    for (let seatNo = 1; seatNo <= base; seatNo++) {
      if (seatNo === s) continue;
      const st = safeStr(elStatus(seatNo)?.value);
      if (st) otherStatuses.push(st);
    }

    // Mit Auffueller sind nur Tandem- und/oder Schueler/Lehrer-Blockstatus erlaubt.
    if (otherStatuses.some((st) => !isBlockStatusForAuffuellerRule(st))) {
      return false;
    }

    const hasPrimary = otherStatuses.some((st) => {
      return (
        st === "G-TD" ||
        st === "G-TD-Video" ||
        st === "Lehrer" ||
        st === AFF_TEACHER_STATUS ||
        STUDENT_STATUSES.includes(st) ||
        AFF_STUDENT_STATUSES.includes(st) ||
        TD_STATUSES.includes(st) ||
        VIDEO_STATUS_CODES.includes(st)
      );
    });

    if (!hasPrimary) return false;
    return true;
  }

// ============================================================
// BLOCK 2B — applyStatusFilterForSeat (silent refresh support)
//
// Ziel:
// - Bei globalen Refreshes sollen keine Alerts erscheinen.
// - Bei direkter User-Aktion bleibt der Alert erhalten.
// Steuerung über: window.__manifestSilentStatusRefresh === true
// ============================================================
async function applyStatusFilterForSeat(seat) {
  const sel = elStatus(seat);
  if (!sel) return;

  const before = safeStr(sel.value);
  const silent = !!window.__manifestSilentStatusRefresh;
  const pid = safeStr(elPersonId(seat)?.value);
  const p = pid ? await getPerson(pid) : null;
  const seatStatusList = await loadSeatStatusList(seat, pid, p);
  const sourceStatuses = seatStatusList.length ? seatStatusList : statusList;
  const isKnownStatus = before
    ? sourceStatuses.some((s) => safeStr(s?.code) === before)
    : false;

  let allowed;

  if (!pid || !p) {
    allowed = sourceStatuses.map((s) => safeStr(s.code)).filter(Boolean);
  } else {
    allowed = allowedStatusesForPerson(p, sourceStatuses);
  }

  // Auffueller-Regel (inkl. Block-only-Kontext) zusaetzlich anwenden
  allowed = allowed.filter((code) => {
    if (!isStatusAllowedInAuffuellerContext(seat, code)) return false;
    if (isAuffuellerStatus(code)) return isAuffuellerAllowedForSeat(seat);
    return true;
  });

  // Legacy-/Altdatenstatus behalten (oder im stillen Global-Refresh nicht löschen).
  // ✅ Im stillen Modus: Auffüller-Status IMMER behalten (kein Alert auf passive Refresh)
  const beforeIsAuffueller = isAuffuellerStatus(before);
  const keepBefore = !!before && !allowed.includes(before) && (!isKnownStatus || silent);
  if (keepBefore) {
    allowed = [...allowed, before];
  }

  populateStatusSelect(sel, allowed, sourceStatuses);

  if (keepBefore) {
    ensureStatusOption(sel, before, before);
    sel.value = before;
    sel.dataset.prevValue = before;
  } else if (before && !allowed.includes(before)) {
    // Bekannter, aber in der aktuellen Konstellation unzulässiger Status.
    // ⚠️ Auffüller-Status im stillen Modus NICHT zurücksetzen/Alert zeigen
    if (silent && beforeIsAuffueller) {
      // Stille Beibehaltung des Auffüller-Status
      ensureStatusOption(sel, before, before);
      sel.value = before;
      sel.dataset.prevValue = before;
    } else {
      const wasUserSelected = sel.dataset.userSelected === "1";
      sel.value = "";
      sel.dataset.userSelected = "";
      if (!silent && wasUserSelected) {
        alert("Der gewählte Status ist in dieser Konstellation nicht zulässig. Bitte Status neu wählen.");
      }
      sel.dataset.prevValue = "";
    }
  }
}

// ============================================================
// BLOCK 2B-2a — Globaler Refresh aller Status-Selects (debounced)
//
// Zweck:
// - Nach Änderungen an einem Sitz (Person/Status/Clear/Paste/Drop) müssen
//   andere Sitze ihre erlaubten Status neu berechnen (z.B. Auffüller).
// - Der Refresh soll NICHT mit Alerts nerven -> "silent refresh".
// - Debounce verhindert unnötig viele Recalculations bei Batch-Aktionen.
//
// Voraussetzung:
// - applyStatusFilterForSeat(seat) unterstützt silent refresh via:
//   window.__manifestSilentStatusRefresh === true
// ============================================================

let __refreshAllStatusFiltersTimer = null;

/**
 * Debounced Trigger für globalen Refresh.
 * Aufrufen nach Person-/Statusänderungen, Clear, Paste/Drop usw.
 */
function refreshAllStatusFiltersDebounced() {
  if (__refreshAllStatusFiltersTimer) window.clearTimeout(__refreshAllStatusFiltersTimer);
  __refreshAllStatusFiltersTimer = window.setTimeout(() => {
    __refreshAllStatusFiltersTimer = null;
    refreshAllStatusFilters().catch(() => {});
  }, 80);
}

/**
 * Refiltert alle Status-Selects anhand der aktuellen globalen Konstellation.
 * Läuft "silent": keine Alerts, wenn ein Status ungültig wird.
 */
async function refreshAllStatusFilters() {
  const seats = qsa("tr.seat-row[data-seat]")
    .map(r => safeInt(r.dataset.seat, 0))
    .filter(n => n > 0);

  // globaler Refresh ohne Alerts
  window.__manifestSilentStatusRefresh = true;
  try {
    for (const s of seats) {
      await applyStatusFilterForSeat(s);
    }
  } finally {
    window.__manifestSilentStatusRefresh = false;
  }
}

// ============================================================
// BLOCK 2B-CLEANUP — Zentraler Recalc nach Sitz-Änderungen
//
// Zweck:
// - Alle typischen Folgeaktionen nach einer Sitzänderung bündeln
// - Verhindert Copy-Paste von 5–6 Zeilen an vielen Stellen
// - Macht klar: "Seat geändert" ist EIN semantischer Vorgang
// ============================================================
async function afterSeatChange({ refreshStatuses = true, immediateStatusRefresh = false } = {}) {
  await updatePayloadSum();
  updateLiveLogic();
  autoAdjustLoadHeightToOccupiedMax({ force: false });

  if (refreshStatuses && typeof refreshAllStatusFiltersDebounced === "function") {
    if (immediateStatusRefresh && typeof refreshAllStatusFilters === "function") {
      await refreshAllStatusFilters();
    } else {
      refreshAllStatusFiltersDebounced();
    }
  }

  scheduleDraftSave();
}

  // ---------------------------------------------------------------------------
  // 11) Hard Reset (Seat-Rebuild) für Person/Status Wechsel
  // ---------------------------------------------------------------------------
  function hardResetStatusSelect(selectEl) {
    if (!selectEl) return;
    selectEl.dataset.initialApplied = "1";
    try { delete selectEl.dataset.initial; } catch (_) {}
    selectEl.dataset.prevValue = "";
  }

  function hardResetSeatOnPersonChange(seat) {
    const sel = elStatus(seat);
    if (sel && !sel.disabled) {
      hardResetStatusSelect(sel);
      if (sel.dataset.userSelected !== "1") {
        sel.value = "";
        sel.dataset.prevValue = "";
      }
    }
    removeGearRentalUi(seat);
    scheduleDraftSave();
  }

  function hardResetSeatOnStatusChange(seat) {
    const sel = elStatus(seat);
    if (sel && !sel.disabled) {
      sel.dataset.initialApplied = "1";
      try { delete sel.dataset.initial; } catch (_) {}
    }
    removeGearRentalUi(seat);
  }

  // ---------------------------------------------------------------------------
  // 12) Height-Logik (Enforce + Auto-Adjust)
  // ---------------------------------------------------------------------------
  function getMaxOccupiedSeatHeight() {
    let maxH = 0;
    for (const row of qsa(".seat-row")) {
      const seat = safeInt(row.dataset.seat, 0);
      if (!seat) continue;
      const pid = safeStr(elPersonId(seat)?.value);
      if (!pid) continue;
      const h = normalizeHeightValue(elHeight(seat)?.value);
      if (h > maxH) maxH = h;
    }
    return maxH;
  }

  function applyLoadHeightToSeatDefaults(oldLoadHeight, newLoadHeight, { fromAuto = false } = {}) {
    let clampedAny = false;
    const newH = normalizeHeightValue(newLoadHeight);
    if (!newH) return;

    for (const sel of qsa("select.seat-height")) {
      if (sel.disabled) continue;
      const seat = seatFromId(sel.id, "height_m");
      if (!seat) continue;
      const pid = safeStr(elPersonId(seat)?.value);
      const cur = normalizeHeightValue(sel.value);
      const userTouched = sel.dataset.userModified === "1";

      if (cur && cur > newH) {
        sel.value = String(newH);
        clampedAny = true;
        continue;
      }

      if (!pid) {
        if (cur !== newH) sel.value = String(newH);
        continue;
      }

      if (!userTouched) {
        if (!cur || (oldLoadHeight && cur === oldLoadHeight)) {
          if (cur !== newH) sel.value = String(newH);
        }
      }
    }

    if (clampedAny && !fromAuto) {
      alert("Absprunghöhe höher als Load! Werte wurden automatisch angepasst.");
    }
    updateLiveLogic();
  }

  function setLoadHeightValue(newHeight, { fromAuto = false } = {}) {
    const loadSel = elLoadHeight();
    if (!loadSel) return false;
    const nh = normalizeHeightValue(newHeight);
    if (!nh) return false;

    const exists = Array.from(loadSel.options).some((o) => safeInt(o.value, 0) === nh);
    if (!exists) return false;

    const old = currentLoadHeight;
    if (old === nh) return false;

    loadSel.value = String(nh);
    currentLoadHeight = nh;
    applyLoadHeightToSeatDefaults(old, nh, { fromAuto });
    return true;
  }

  function autoAdjustLoadHeightToOccupiedMax({ force = false } = {}) {
    if (__autoLoadHeightInProgress) return;
    if (!force && !areAllBaseSeatsFilled()) return;

    const maxH = getMaxOccupiedSeatHeight();
    if (!maxH) return;

    __autoLoadHeightInProgress = true;
    try {
      setLoadHeightValue(maxH, { fromAuto: true });
    } finally {
      __autoLoadHeightInProgress = false;
    }
  }

  function enforceSeatHeightNotAboveLoad(sel) {
    const loadH = normalizeHeightValue(currentLoadHeight);
    if (!loadH) return;
    const cur = normalizeHeightValue(sel.value);
    if (cur && cur > loadH) {
      sel.value = String(loadH);
      alert("Absprunghöhe höher als Load! Dieser Eintrag wurde auf die Load-Höhe begrenzt.");
    }
  }

  // ---------------------------------------------------------------------------
  // 14) Warnungen (unverändert)
  // ---------------------------------------------------------------------------
  function computeWarnings(entries) {
    const warnings = [];
    if (currentLoadHeight && entries.some((e) => e.height > currentLoadHeight)) {
      warnings.push("Absprunghöhe höher als Load!");
    }

    const tandemRoleEntries = entries.filter((e) => TANDEM_ROLE_STATUSES.includes(e.status));
    const pidCounts = Object.create(null);
    for (const e of tandemRoleEntries) {
      pidCounts[e.personId] = (pidCounts[e.personId] || 0) + 1;
    }
    if (Object.values(pidCounts).some((v) => v > 1)) {
      warnings.push("Tandemrollen (Gast/TD/Video) müssen unterschiedliche Personen sein.");
    }

    const countTd = entries.filter((e) => TD_STATUSES.includes(safeStr(e.status))).length;
    const countGtdVideo = entries.filter((e) => safeStr(e.status) === "G-TD-Video").length;
    const countVideo = entries.filter((e) => VIDEO_STATUS_CODES.includes(safeStr(e.status))).length;
    if (countVideo > 0 && countGtdVideo === 0) {
      warnings.push("Status Video ist nur zusammen mit mindestens einem G-TD-Video erlaubt.");
    }
    if (countVideo > 0 && countTd === 0) {
      warnings.push("Status Video ist nur zusammen mit mindestens einem TD/TD-Vereins-Schirm erlaubt.");
    }

    const teachers = count(entries, ["Lehrer"]);
    const students = count(entries, STUDENT_STATUSES);
    if (teachers > 0 && students === 0) warnings.push("Ein Lehrer erfordert mindestens einen Schüler.");
    if (teachers > 0 && students > 0 && teachers > 2 * students) {
      warnings.push("Zu viele Lehrer: pro Schüler max. 2 Lehrer (Lehrer > 2×Schüler).");
    }

    const affTeachers = entries.filter((e) => safeStr(e.status).toUpperCase() === AFF_TEACHER_STATUS).length;
    const affStudent1 = entries.filter((e) => safeStr(e.status).toUpperCase() === "SCHUELER-AFF-1").length;
    const affStudent2 = entries.filter((e) => safeStr(e.status).toUpperCase() === "SCHUELER-AFF-2").length;
    const requiredAffTeachers = affStudent1 + (2 * affStudent2);
    if (affTeachers > 0 && requiredAffTeachers === 0) {
      warnings.push("AFF-Lehrer erfordert mindestens einen AFF-Schüler (Schüler-AFF-1/2).");
    }
    if (requiredAffTeachers > 0 && affTeachers < requiredAffTeachers) {
      warnings.push(`Zu wenige AFF-Lehrer: benötigt ${requiredAffTeachers}, vorhanden ${affTeachers}.`);
    }

    if (instructionWarnTwoTeachers) warnings.push("Achtung, zwei Lehrer für einen Schüler!");

    const duplicateGroups = findDuplicatePersonGroups();
    for (const group of duplicateGroups) {
      const personLabel = safeStr(group.displayName) || "Diese Person";
      warnings.push(`${personLabel} ist mehrfach eingetragen. Wirklich mehrfach oder Korrektur?`);
    }

    if (lastMaxPayload && lastPayloadTotal) {
      if (lastPayloadTotal > lastMaxPayload) warnings.push("Max. Nutzlast überschritten!");
      else if (lastPayloadTotal > lastMaxPayload * 0.9) warnings.push("Nutzlast nahe am Limit (über 90%).");
    }
    return warnings;
  }

  function applyGlobalWarnings(warnings) {
    const container = qs("#load_warnings");
    if (!container) return;
    if (!warnings.length) {
      container.classList.add("d-none");
      container.innerHTML = "";
      return;
    }
    container.classList.remove("d-none");
    container.innerHTML = "<strong>Hinweise:</strong><ul></ul>";
    const ul = container.querySelector("ul");
    for (const msg of warnings) {
      const li = document.createElement("li");
      li.textContent = msg;
      ul.appendChild(li);
    }
  }

  function applyHeightRowHighlight(entries) {
    qsa(".seat-row").forEach((r) => r.classList.remove("height-too-high"));
    if (!currentLoadHeight) return;
    for (const e of entries) {
      if (e.height > currentLoadHeight) e.row.classList.add("height-too-high");
    }
  }

  function ensureDuplicatePersonStyles() {
    if (qs("#load-editor-duplicate-person-styles")) return;
    const st = document.createElement("style");
    st.id = "load-editor-duplicate-person-styles";
    st.textContent = `
      .person-input.duplicate-person{
        border-color:#dc3545 !important;
        box-shadow:0 0 0 0.18rem rgba(220,53,69,0.2) !important;
        background-color:#fff5f5;
      }
    `;
    document.head.appendChild(st);
  }

  function normalizeNameForDuplicateCheck(name) {
    return safeStr(name).toLowerCase().replace(/\s+/g, " ").trim();
  }

  function findDuplicatePersonGroups() {
    const groupsByKey = new Map();

    for (const row of qsa("tr.seat-row[data-seat]")) {
      const seat = safeInt(row.dataset.seat, 0);
      if (!seat) continue;

      const pid = safeStr(elPersonId(seat)?.value);
      const displayName = safeStr(elPersonInput(seat)?.value).trim();
      if (!pid && !displayName) continue;

      const nameKey = normalizeNameForDuplicateCheck(displayName);
      const key = pid ? `pid:${pid}` : `name:${nameKey}`;
      if (!key || key === "name:") continue;

      if (!groupsByKey.has(key)) {
        groupsByKey.set(key, {
          seats: [],
          displayName: displayName || "Diese Person"
        });
      }

      const group = groupsByKey.get(key);
      group.seats.push(seat);
      if (!group.displayName && displayName) {
        group.displayName = displayName;
      }
    }

    return Array.from(groupsByKey.values()).filter((g) => g.seats.length > 1);
  }

  function getDuplicateSeatInfoMap() {
    const bySeat = new Map();
    const groups = findDuplicatePersonGroups();
    for (const group of groups) {
      const label = safeStr(group.displayName) || "Diese Person";
      for (const seat of group.seats) {
        bySeat.set(seat, label);
      }
    }
    return bySeat;
  }

  function applyDuplicatePersonHighlights() {
    ensureDuplicatePersonStyles();
    qsa("input.person-input[data-seat]").forEach((inputEl) => {
      if (!inputEl) return;
      inputEl.classList.remove("duplicate-person");
    });

    const duplicateSeatMap = getDuplicateSeatInfoMap();
    duplicateSeatMap.forEach((_label, seat) => {
      const inputEl = elPersonInput(seat);
      if (!inputEl) return;
      inputEl.classList.add("duplicate-person");
    });
  }

  // ---------------------------------------------------------------------------
  // 15) Payload Sum
  // ---------------------------------------------------------------------------
  async function updatePayloadSum() {
    const entries = collectEntriesFromDom();
    const ids = entries.map((e) => e.personId);
    await preloadPersons(ids);

    let total = 0;
    for (const e of entries) {
      const p = personCache[safeStr(e.personId)];
      if (!p) continue;
      total += (safeInt(p.weight_kg, 0) + 15);
    }

    const display = qs("#payload_sum_display");
    if (!display) return;

    lastPayloadTotal = total;
    display.textContent = `${Math.round(total)} kg`;

    const maxPayloadRaw = safeStr(display.dataset.maxPayload);
    const maxPayload = maxPayloadRaw ? Number(maxPayloadRaw) : 0;
    lastMaxPayload = Number.isFinite(maxPayload) ? maxPayload : 0;

    if (!lastMaxPayload) {
      display.className = "fw-bold payload-neutral";
      return;
    }

    const ratio = total / lastMaxPayload;
    if (ratio > 1.0) display.className = "fw-bold payload-red";
    else if (ratio > 0.9) display.className = "fw-bold payload-yellow";
    else display.className = "fw-bold payload-green";
  }

  function bindMaxPayloadInput() {
    if (__maxPayloadBound) return;
    __maxPayloadBound = true;

    const input = qs('input[name="max_payload_kg"]');
    const display = qs("#payload_sum_display");
    if (!input || !display) return;

    const sync = () => {
      const raw = safeStr(input.value);
      if (!raw) {
        display.dataset.maxPayload = "";
        lastMaxPayload = 0;
        return;
      }
      const n = Number(raw.replace(",", "."));
      if (Number.isFinite(n) && n > 0) {
        display.dataset.maxPayload = String(n);
        lastMaxPayload = n;
      } else {
        display.dataset.maxPayload = "";
        lastMaxPayload = 0;
      }
    };

    sync();

    const onChange = async () => {
      sync();
      await updatePayloadSum();
      updateLiveLogic();
      scheduleDraftSave();
    };

    input.addEventListener("input", () => { sync(); scheduleDraftSave(); });
    input.addEventListener("change", onChange);
    input.addEventListener("blur", onChange);
  }

  // ---------------------------------------------------------------------------
  // 16) Lehrer/Schüler Warnung
  // ---------------------------------------------------------------------------
  function computeInstructionTwoTeacherWarning(entries) {
    instructionWarnTwoTeachers = false;
    const teachers = entries.filter((e) => e.status === "Lehrer");
    const students = entries.filter((e) => STUDENT_STATUSES.includes(e.status));
    if (!teachers.length || !students.length) return;

    const tandemSeats = new Set();
    computeTandemBlocks(entries).forEach((b) => b.forEach((s) => tandemSeats.add(s)));

    const teachersAvail = teachers.filter((t) => !tandemSeats.has(t.seat));
    const studentsAvail = students.filter((s) => !tandemSeats.has(s.seat));
    if (!teachersAvail.length || !studentsAvail.length) return;

    const teacherDegree = new Map();
    teachersAvail.forEach((t) => teacherDegree.set(t.seat, 0));

    for (const s of studentsAvail) {
      let bestT = null;
      let bestD = null;
      for (const t of teachersAvail) {
        if (String(t.personId) === String(s.personId)) continue;
        const d = Math.abs(s.seat - t.seat);
        if (bestT === null || d < bestD || (d === bestD && t.seat < bestT.seat)) {
          bestT = t;
          bestD = d;
        }
      }
      if (bestT) teacherDegree.set(bestT.seat, (teacherDegree.get(bestT.seat) || 0) + 1);
    }

    for (const t of teachersAvail) {
      if ((teacherDegree.get(t.seat) || 0) > 0) continue;
      instructionWarnTwoTeachers = true;
      break;
    }
  }

// ---------------------------------------------------------------------------
// 18) Validierung (Feldfehler anzeigen)
// ---------------------------------------------------------------------------
function ensureValidationStyles() {
  if (qs("#load-editor-validation-styles")) return;
  const st = document.createElement("style");
  st.id = "load-editor-validation-styles";
  st.textContent = `
    .load-editor-error-note{
      color:#b91c1c; font-weight:700;
      font-size:0.85rem; margin-top:4px;
    }
    .load-editor-draftbar{
      position: sticky; top: 0; z-index: 4000;
      background: rgba(255,255,255,0.95);
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 8px 10px;
      display:flex; gap:10px; align-items:center; justify-content:space-between;
      box-shadow: 0 6px 18px rgba(0,0,0,0.08);
      margin-bottom: 10px;
    }
    .load-editor-draftbar .msg{ font-size:0.9rem; color:#111827; }
    .load-editor-draftbar .btns{ display:flex; gap:8px; }

    #load_warnings.alert{
      padding: 0.45rem 0.65rem;
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
      line-height: 1.25;
    }
    #load_warnings strong{
      font-size: 0.88rem;
      font-weight: 700;
    }
    #load_warnings ul{
      margin: 0.2rem 0 0 1rem;
      padding: 0;
    }
    #load_warnings li{
      margin: 0.05rem 0;
    }
  `;
  document.head.appendChild(st);
}

function clearFieldError(el) {
  if (!el) return;
  el.classList.remove("is-invalid");
  el.classList.remove("invalid-person");
  el.removeAttribute("aria-invalid");
  const wrap = el.parentElement;
  if (!wrap) return;
  const note = wrap.querySelector(".load-editor-error-note");
  if (note) note.remove();
}

function setFieldError(el, msg) {
  if (!el) return;
  ensureValidationStyles();
  el.classList.add("is-invalid");
  el.setAttribute("aria-invalid", "true");
  const wrap = el.parentElement;
  if (!wrap) return;
  let note = wrap.querySelector(".load-editor-error-note");
  if (!note) {
    note = document.createElement("div");
    note.className = "load-editor-error-note";
    wrap.appendChild(note);
  }
  note.textContent = msg || "Bitte Eingabe prüfen.";
}

// ---------------------------------------------------------------------------
// ✅ Schritt 4.2.1: Ampel/Hint unter dem Personfeld (Enthaftung + Lehrerlizenz)
// ---------------------------------------------------------------------------
function ensureSeatValidityHintStyles() {
  if (qs("#seat-validity-hint-styles")) return;
  const st = document.createElement("style");
  st.id = "seat-validity-hint-styles";
  st.textContent = `
    .seat-validity-hints{
      min-height: 18px;
      display:flex;
      gap:6px;
      flex-wrap:wrap;
      align-items:center;
    }
    .seat-validity-badge{
      display:inline-flex;
      align-items:center;
      gap:6px;
      padding:2px 8px;
      border-radius:999px;
      font-size:0.75rem;
      line-height:1.1;
      border:1px solid rgba(0,0,0,0.12);
      user-select:none;
      white-space:nowrap;
    }
    .sv-ok{ background:#e8f7ea; color:#0f5132; border-color:rgba(15,81,50,0.18); }
    .sv-bad{ background:#fdecea; color:#842029; border-color:rgba(132,32,41,0.18); }
    .sv-warn{ background:#fff7e0; color:#664d03; border-color:rgba(102,77,3,0.18); }
    .sv-note{ background:#eef2ff; color:#3730a3; border-color:rgba(55,48,163,0.18); }
  `;
  document.head.appendChild(st);
}

function seatValidityEl(seat) {
  // Container kommt aus editor_inner.html:
  // <div id="seat_{{ seat }}_validity_hints" class="seat-validity-hints ..."></div>
  return qs(`#seat_${seat}_validity_hints`);
}

function formatIsoToDE(iso) {
  // Erwartet YYYY-MM-DD
  const s = safeStr(iso);
  if (!s || s.length < 10) return "";
  const parts = s.slice(0, 10).split("-");
  if (parts.length !== 3) return "";
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

function buildBadge(text, cls, title = "") {
  const span = document.createElement("span");
  span.className = `seat-validity-badge ${cls}`;
  span.textContent = text;
  if (title) span.title = title;
  return span;
}

async function renderSeatValidityHints(seat) {
  ensureSeatValidityHintStyles();

  const box = seatValidityEl(seat);
  if (!box) return;

  const pid = safeStr(elPersonId(seat)?.value);
  const st = safeStr(elStatus(seat)?.value);

  if (!pid) {
    box.innerHTML = "";
    return;
  }

  // Persondaten sicher laden (Cache)
  const p = await getPerson(pid);
  if (!p) {
    box.innerHTML = "";
    return;
  }

  // Badges sammeln
  const badges = [];

  // Tandemgast-Hinweis (Enthaftung nicht erforderlich)
  if (p.is_tandem_guest) {
    badges.push(buildBadge("Tandemgast: Enthaftung frei", "sv-note"));
  }

  // Enthaftung nur sinnvoll, wenn kein Tandemgast
  if (!p.is_tandem_guest) {
    if (p.liability_waiver_valid) {
      badges.push(buildBadge("Enthaftung: OK", "sv-ok"));
    } else {
      const year = p.liability_waiver_year ? ` (Jahr ${p.liability_waiver_year})` : "";
      badges.push(
        buildBadge(
          "Enthaftung: FEHLT/UNGÜLTIG",
          "sv-bad",
          `Enthaftung ist nicht im laufenden Kalenderjahr gültig${year}.`
        )
      );
    }
  }

  // Lehrerlizenz nur anzeigen, wenn Status Lehrer gewählt ist ODER Person Lehrer ist
  const showTeacher = (st === "Lehrer") || !!p.is_teacher;
  if (showTeacher) {
    const expires = formatIsoToDE(p.teacher_license_expires);
    const status = safeStr(p.teacher_license_status);

    if (st === "Lehrer") {
      // Im Lehrer-Status ist die Lizenz zwingend
      if (p.teacher_license_valid) {
        const t = expires ? `Gültig bis ${expires}` : "Gültig";
        badges.push(buildBadge("Lizenz: OK", "sv-ok", t));
      } else {
        const t = expires ? `Ablaufdatum ${expires}` : "Kein Ablaufdatum hinterlegt";
        badges.push(buildBadge("Lizenz: NICHT OK", "sv-bad", t));
      }
    } else {
      // Nur Info (nicht zwingend), wenn Person Lehrer ist
      if (status === "warning") {
        const t = expires ? `Läuft bald ab: ${expires}` : "Läuft bald ab";
        badges.push(buildBadge("Lizenz: bald ablaufend", "sv-warn", t));
      } else if (status === "expired") {
        const t = expires ? `Abgelaufen: ${expires}` : "Abgelaufen";
        badges.push(buildBadge("Lizenz: abgelaufen", "sv-bad", t));
      } else if (status === "ok") {
        const t = expires ? `Gültig bis ${expires}` : "Gültig";
        badges.push(buildBadge("Lizenz: OK", "sv-ok", t));
      }
    }
  }

  const duplicateSeatMap = getDuplicateSeatInfoMap();
  const duplicateLabel = duplicateSeatMap.get(seat);
  if (duplicateLabel) {
    badges.push(
      buildBadge(
        "Mehrfach eingetragen",
        "sv-warn",
        `${duplicateLabel} ist mehrfach eingetragen. Wirklich mehrfach oder Korrektur?`
      )
    );
  }

  box.innerHTML = "";
  badges.forEach(b => box.appendChild(b));
}

async function renderAllSeatValidityHints() {
  const seats = qsa("tr.seat-row[data-seat]")
    .map(r => safeInt(r.dataset.seat, 0))
    .filter(n => n > 0);

  // parallel ist okay, getPerson cached
  await Promise.all(seats.map(s => renderSeatValidityHints(s).catch(() => null)));
}


// ---------------------------------------------------------------------------
// 19) Kompat-Stubs
// ---------------------------------------------------------------------------
if (typeof window.markInvalid !== "function") {
  window.markInvalid = function markInvalid(inputEl, isInvalid) {
    try { setInvalidPersonVisual(inputEl, !!isInvalid); } catch (_) {}
  };
} else {
  const prev = window.markInvalid;
  window.markInvalid = function markInvalidCompat(inputEl, isInvalid) {
    try { prev(inputEl, isInvalid); } catch (_) {}
    try { setInvalidPersonVisual(inputEl, !!isInvalid); } catch (_) {}
  };
}

if (typeof window.ensureAutocompleteScrollbarStyles !== "function") {
  window.ensureAutocompleteScrollbarStyles = function ensureAutocompleteScrollbarStyles() {
    if (qs("#autocomplete-scrollbar-styles")) return;
    const style = document.createElement("style");
    style.id = "autocomplete-scrollbar-styles";
    style.textContent = `
      .autocomplete-list{ max-height: 280px; overflow:auto; border:1px solid #94a3b8; background:#f8fafc; box-shadow:0 4px 12px rgba(0,0,0,0.15); }
      .autocomplete-list::-webkit-scrollbar{ width:12px; }
      .autocomplete-list::-webkit-scrollbar-thumb{ background:#94a3b8; border-radius:10px; }
      .autocomplete-list::-webkit-scrollbar-track{ background:#e2e8f0; }
    `;
    document.head.appendChild(style);
  };
}

if (typeof window.bindClearButton !== "function") {
  window.bindClearButton = function bindClearButton(btn, seat) {
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const input = elPersonInput(seat);
      const hid = elPersonId(seat);
      const sel = elStatus(seat);
      const hsel = elHeight(seat);

      if (input && input.disabled) return;

      // Person + ID leeren
      if (input) input.value = "";
      if (hid) hid.value = "";

      // Status zurücksetzen
      if (sel && !sel.disabled) {
        hardResetStatusSelect(sel);
        sel.value = "";
        sel.dataset.userSelected = "";
        sel.dataset.prevValue = "";
      }

      // Höhe zurücksetzen
      if (hsel && !hsel.disabled && currentLoadHeight) {
        hsel.value = String(currentLoadHeight);
        hsel.dataset.userModified = "";
      }

      // Gear rental UI entfernen
      removeGearRentalUi(seat);

      // Validierung / Fehler / Hint zurücksetzen
      try { window.markInvalid(input, false); } catch (_) {}
      clearFieldError(input);
      clearInvalidPersonForSeat(seat);

      const hintBox = qs(`#seat_${seat}_validity_hints`);
      if (hintBox) hintBox.innerHTML = "";

      // Recalc
      await updatePayloadSum();
      updateLiveLogic();
      autoAdjustLoadHeightToOccupiedMax({ force: false });

      // ✅ 2B: Globalen Status-Refresh triggern (Auffüller sofort sichtbar)
      if (typeof refreshAllStatusFiltersDebounced === "function") {
        refreshAllStatusFiltersDebounced();
      }

      scheduleDraftSave();
    });
  };
}

if (typeof window.bindSubmitGuard !== "function") {
  window.bindSubmitGuard = function bindSubmitGuard() {
    if (__submitGuardBound) return;
    __submitGuardBound = true;

    const form = getSaveForm();
    if (!form) return;

    form.addEventListener("submit", (ev) => {
      saveDraftNow();
      const loadId = getLoadIdFromFormAction();
      if (loadId) setLastSubmitNow(loadId);

      let blocked = false;
      let videoRuleBlocked = false;
      const loadH = normalizeHeightValue(currentLoadHeight);

      for (const row of qsa(".seat-row")) {
        const seat = safeInt(row.dataset.seat, 0);
        if (!seat) continue;

        const input = elPersonInput(seat);
        const hid = elPersonId(seat);
        const ssel = elStatus(seat);
        const hsel = elHeight(seat);

        const name = safeStr(input?.value);
        const pid = safeStr(hid?.value);

        // Freitext blockieren
        if (name && !pid) {
          blocked = true;
          try { window.markInvalid(input, true); } catch (_) {}
          setFieldError(input, "Bitte Person aus der Liste auswählen (kein Freitext).");
        } else {
          clearFieldError(input);
          clearInvalidPersonForSeat(seat);
        }

        // Status ist Pflicht, sobald eine Person gesetzt ist.
        const status = safeStr(ssel?.value);
        if (pid && !status) {
          blocked = true;
          setFieldError(ssel, "Status erforderlich.");
        } else if (ssel) {
          clearFieldError(ssel);
        }

        // Höhe > Load blockieren
        if (loadH && hsel && !hsel.disabled) {
          const sh = normalizeHeightValue(hsel.value);
          if (sh && sh > loadH) {
            blocked = true;
            hsel.value = String(loadH);
            setFieldError(hsel, "Absprunghöhe darf nicht höher als Load sein.");
          }
        }
      }

      // Harte Tandem-Video-Regel: Video niemals alleinstehend speichern.
      const entries = collectEntriesFromDom();
      const countTd = entries.filter((e) => TD_STATUSES.includes(safeStr(e.status))).length;
      const countGtdVideo = entries.filter((e) => safeStr(e.status) === "G-TD-Video").length;
      const countVideo = entries.filter((e) => VIDEO_STATUS_CODES.includes(safeStr(e.status))).length;
      if (countVideo > 0 && (countGtdVideo === 0 || countTd === 0)) {
        blocked = true;
        videoRuleBlocked = true;
      }

      if (blocked) {
        ev.preventDefault();
        alert(getInvalidInputAlertMessage(videoRuleBlocked));
      }
    }, { capture: true });
  };
}

// ---------------------------------------------------------------------------
// 20) Autocomplete (Statusfilter + open-up)
// ---------------------------------------------------------------------------
if (typeof window.bindAutocomplete !== "function") {
  window.bindAutocomplete = function bindAutocomplete(input, seat) {
    if (!input) return;
    const container = input.parentElement;
    if (!container) return;

    // Container-Position
    const cs = window.getComputedStyle(container);
    if (cs.position === "static") container.style.position = "relative";

    // Dropdown-Pfeil
    const arrow = container.querySelector(".autocomplete-arrow");
    if (arrow) {
      arrow.style.position = "absolute";
      arrow.style.right = "10px";
      arrow.style.top = "50%";
      arrow.style.transform = "translateY(-50%)";
      arrow.style.zIndex = "2100";
      arrow.style.cursor = "pointer";
      arrow.style.userSelect = "none";
      const pr = parseFloat(window.getComputedStyle(input).paddingRight || "0") || 0;
      if (pr < 28) input.style.paddingRight = "32px";
    }

    // Dropdown-Liste
    let list = container.querySelector(".autocomplete-list");
    if (!list) {
      list = document.createElement("div");
      list.className = "autocomplete-list list-group position-absolute";
      list.style.zIndex = "2000";
      list.style.display = "none";
      list.style.maxHeight = "280px";
      list.style.overflow = "auto";
      list.style.left = "0";
      list.style.top = "100%";
      list.style.marginTop = "6px";
      container.appendChild(list);
    }

    let timer = null;

    async function runSearch(q) {
      try {
        const res = await fetch(`/loads/api/person/search?q=${encodeURIComponent(q || "")}`);
        if (!res.ok) return [];
        const arr = await res.json();
        return Array.isArray(arr) ? arr : [];
      } catch {
        return [];
      }
    }

    function close() {
      list.style.display = "none";
      list.innerHTML = "";
      list.classList.remove("open-up");
      list.style.top = "100%";
      list.style.bottom = "auto";
      list.style.marginTop = "6px";
      list.style.marginBottom = "0";
    }

    function placeDropdown() {
      const w = input.offsetWidth || input.getBoundingClientRect().width || 0;
      if (w) list.style.width = `${Math.round(w)}px`;

      const rect = input.getBoundingClientRect();
      const approx = 280;
      const spaceBelow = (window.innerHeight || document.documentElement.clientHeight) - rect.bottom;
      const spaceAbove = rect.top;

      if (spaceBelow < approx && spaceAbove > spaceBelow) {
        list.classList.add("open-up");
        list.style.top = "auto";
        list.style.bottom = "100%";
        list.style.marginTop = "0";
        list.style.marginBottom = "6px";
      } else {
        list.classList.remove("open-up");
        list.style.bottom = "auto";
        list.style.top = "100%";
        list.style.marginBottom = "0";
        list.style.marginTop = "6px";
      }
    }

    function openIfHasItems() {
      if (!list.innerHTML.trim()) return;
      placeDropdown();
      list.style.display = "";
    }

    function getStatusCode() {
      const sel = elStatus(seat);
      return sel ? safeStr(sel.value) : "";
    }

    function render(items, statusFilterCode) {
      list.innerHTML = "";

      // --------------------------------------------------------
      // Freier Platz
      // --------------------------------------------------------
      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "list-group-item list-group-item-action fw-bold text-muted";
      clearBtn.textContent = "freier Platz";
      clearBtn.addEventListener("click", async () => {
        const inputEl = elPersonInput(seat);
        const hid = elPersonId(seat);
        const stSel = elStatus(seat);
        const hSel = elHeight(seat);

        if (inputEl && inputEl.disabled) return;

        if (inputEl) inputEl.value = "";
        if (hid) hid.value = "";

        if (stSel && !stSel.disabled) {
          hardResetStatusSelect(stSel);
          populateStatusSelect(stSel, null);
          stSel.value = "";
          stSel.dataset.prevValue = "";
          stSel.dataset.userSelected = "";
        }

        if (hSel && !hSel.disabled && currentLoadHeight) {
          hSel.value = String(currentLoadHeight);
          hSel.dataset.userModified = "";
        }

        removeGearRentalUi(seat);
        clearInvalidPersonForSeat(seat);
        clearFieldError(inputEl);

        const hintBox = qs(`#seat_${seat}_validity_hints`);
        if (hintBox) hintBox.innerHTML = "";

        close();
        await afterSeatChange();
      });
      list.appendChild(clearBtn);

      if (!Array.isArray(items) || items.length === 0) {
        openIfHasItems();
        return;
      }

      // --------------------------------------------------------
      // Personenliste
      // --------------------------------------------------------
      const filtered = items.filter((p) => personAllowedForStatus(p, statusFilterCode));
      const use = filtered.length ? filtered : items;

      use.slice(0, 50).forEach((p) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "list-group-item list-group-item-action";
        btn.textContent = safeStr(p.name);

        btn.addEventListener("click", async () => {
          input.value = safeStr(p.name);

          const hid = elPersonId(seat);
          const prevPid = safeStr(hid?.value);
          if (hid) hid.value = p.id;
          personCache[safeStr(p.id)] = p;

          if (safeStr(prevPid) !== safeStr(p.id)) {
            const sel = elStatus(seat);
            if (sel && !sel.disabled) hardResetStatusSelect(sel);
          }

          await applyStatusFilterForSeat(seat);

          // ✅ Auto-Bestimmung exklusiver Status basierend auf Person-Flags
          const sel = elStatus(seat);
          if (sel && !sel.disabled && !sel.value) {
            const allowedStatuses = Array.from(sel.options)
              .map((opt) => safeStr(opt.value))
              .filter(Boolean);
            const defaultStatus = computeDefaultStatusForPerson(p, allowedStatuses);
            if (defaultStatus) {
              sel.value = defaultStatus;
              sel.dataset.userSelected = "1";
            }
          }

          // Schirmmiete sofort nach Person/Status-Änderung neu aufbauen,
          // damit sie ohne vorheriges Speichern bedienbar ist.
          hardResetSeatOnStatusChange(seat);
          renderGearRentalUi(seat);

          await renderSeatValidityHints(seat);

          const hsel = elHeight(seat);
          if (hsel && !hsel.disabled) {
            if (hsel.dataset.userModified !== "1") {
              const lh = normalizeHeightValue(currentLoadHeight);
              if (lh) hsel.value = String(lh);
            }
            enforceSeatHeightNotAboveLoad(hsel);
          }

          maybeTriggerFillHintFromPerson(input, seat);
          try { window.markInvalid(input, false); } catch {}
          clearFieldError(input);
          clearInvalidPersonForSeat(seat);

          close();
          await afterSeatChange({ immediateStatusRefresh: true });
        });

        list.appendChild(btn);
      });

      openIfHasItems();
    }

    input.addEventListener("input", () => {
      evalInvalidPersonForSeat(seat);
      const q = safeStr(input.value);
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(async () => {
        const items = await runSearch(q);
        render(items, getStatusCode());
      }, 140);
    });

    input.addEventListener("blur", () => evalInvalidPersonForSeat(seat));

    input.addEventListener("focus", async () => {
      const q = safeStr(input.value);
      const items = await runSearch(q);
      render(items, getStatusCode());
    });

    if (arrow) {
      arrow.addEventListener("click", async (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const items = await runSearch("");
        render(items, getStatusCode());
      });
    }

    document.addEventListener("click", (ev) => {
      if (ev.target === input || ev.target === arrow) return;
      if (list.contains(ev.target)) return;
      if (!container.contains(ev.target)) close();
    }, true);
  };
}


// ---------------------------------------------------------------------------
// 21) Clipboard Helpers
// ---------------------------------------------------------------------------
function saveClipboard(payload) {
  try {
    localStorage.setItem(CLIPBOARD_KEY, JSON.stringify(payload));
    return true;
  } catch (e) {
    console.warn("Clipboard speichern fehlgeschlagen:", e);
    return false;
  }
}

function loadClipboard() {
  try {
    const raw = localStorage.getItem(CLIPBOARD_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn("Clipboard laden fehlgeschlagen:", e);
    return null;
  }
}

// ✅ Neu: Entry-Key-Varianten robust vereinheitlichen
function normalizeOneEntry(entry) {
  if (!entry || typeof entry !== "object") return null;

  // Person-ID (verschiedene Quellen)
  const personId =
    safeStr(entry.personId) ||
    safeStr(entry.person_id) ||
    safeStr(entry.personID) ||
    safeStr(entry.person);

  // Status (verschiedene Quellen)
  const status =
    safeStr(entry.status) ||
    safeStr(entry.status_code) ||
    safeStr(entry.statusCode);

  // Höhe (verschiedene Quellen)
  const heightRaw =
    entry.height !== undefined ? entry.height :
    entry.height_m !== undefined ? entry.height_m :
    entry.heightM !== undefined ? entry.heightM :
    entry.heightMeter !== undefined ? entry.heightMeter :
    null;

  const height = safeInt(heightRaw, 0);

  // Name optional (nur für UX)
  const personName =
    safeStr(entry.personName) ||
    safeStr(entry.name) ||
    safeStr(entry.full_name) ||
    safeStr(entry.fullName);

  // Schirmmiete optional
  const gear = parseGearRentalFromPayload(entry);
  const gearRental = (gear === null) ? false : !!gear;

  if (!personId || !status) return null;

  return {
    personId,
    status,
    height: height || 0,
    personName: personName || "",
    gearRental,
    gear_rental: gearRental
  };
}

function normalizeEntryArray(payload) {
  if (!payload) return [];

  const arr = (
    Array.isArray(payload) ? payload :
    Array.isArray(payload.entries) ? payload.entries :
    Array.isArray(payload.items) ? payload.items :
    (payload.personId || payload.person_id || payload.status || payload.status_code) ? [payload] :
    []
  );

  return arr.map(normalizeOneEntry).filter(Boolean);
}

// ---------------------------------------------------------------------------
// ✅ Clipboard: Copy aus dem Editor (inkl. Schirmmiete)
// - Export bleibt kompatibel
// ---------------------------------------------------------------------------
function collectEntriesForClipboardFromEditor() {
  const entries = [];

  for (const row of qsa('tr.seat-row[data-seat]')) {
    const seat = safeInt(row.dataset.seat, 0);
    if (!seat) continue;

    const personId = safeStr(elPersonId(seat)?.value);
    const status = safeStr(elStatus(seat)?.value);
    const height = safeInt(elHeight(seat)?.value, 0);
    const personName = safeStr(elPersonInput(seat)?.value);

    if (!personId || !status) continue;

    const gear = getGearRentalForSeatSerialize(seat);
    entries.push({
      personId,
      status,
      height,
      personName,
      gearRental: !!gear,
      gear_rental: !!gear
    });
  }

  return entries;
}

// Exporte für andere Skripte/Templates
window.getLoadEditorClipboardEntries = collectEntriesForClipboardFromEditor;

window.copyLoadEditorToClipboard = function copyLoadEditorToClipboard() {
  const entries = collectEntriesForClipboardFromEditor();
  if (!entries.length) {
    alert("Keine Einträge zum Kopieren vorhanden.");
    return false;
  }
  return saveClipboard({ v: 1, entries });
};

// ---------------------------------------------------------------------------
// 22) Paste / Drag Target: IMMER auf Standardsitze kürzen
// ---------------------------------------------------------------------------
function getStandardSeatRowsSorted() {
  const base = getBaseSeatCount();
  return qsa("tr.seat-row[data-seat]")
    .map((r) => safeInt(r.dataset.seat, 0))
    .filter((n) => Number.isFinite(n) && n > 0)
    .filter((n) => (base > 0 ? n <= base : true))
    .sort((a, b) => a - b);
}

function findFirstEditableFreeStandardSeat(seatRows) {
  for (const seat of seatRows) {
    const pid = safeStr(elPersonId(seat)?.value);
    const locked = !!elPersonInput(seat)?.disabled;
    if (!pid && !locked) return seat;
  }
  return seatRows[0] || 1;
}

async function setSeatFromEntry(seat, entry) {
  const input = elPersonInput(seat);
  if (input && input.disabled) return false;

  const pid = safeStr(entry?.personId);
  const status = safeStr(entry?.status);
  const height = entry?.height;

  if (!pid || !status) return false;

  // Person laden + Zulässigkeit prüfen (Enthaftung/Lehrerlizenz/Status)
  const p = await getPerson(pid);
  if (!p) return false;
  if (!personAllowedForStatus(p, status)) return false;

  // Person setzen
  if (input) input.value = safeStr(p.name);
  const hid = elPersonId(seat);
  if (hid) hid.value = p.id;

  // Personwechsel -> Statusfilter neu
  hardResetSeatOnPersonChange(seat);
  await applyStatusFilterForSeat(seat);

  // Status setzen (wenn Option verfügbar)
  const sel = elStatus(seat);
  if (sel && !sel.disabled) {
    const exists = Array.from(sel.options).some((o) => o.value === status);
    if (!exists && status) {
      ensureStatusOption(sel, status, status);
    }
    sel.value = status || "";

    // Statuswechsel -> Schirmmiete neu
    hardResetSeatOnStatusChange(seat);

    const wantGear = parseGearRentalFromPayload(entry);
    if (wantGear !== null) renderGearRentalUi(seat, { checked: wantGear });
    else renderGearRentalUi(seat);

    sel.dataset.prevValue = safeStr(sel.value);
  }

  // Höhe setzen + clamp
  const hsel = elHeight(seat);
  if (hsel && !hsel.disabled) {
    const h = normalizeHeightValue(height);
    const loadH = normalizeHeightValue(currentLoadHeight || elLoadHeight()?.value);
    if (!h) return false;
    if (loadH && h > loadH) return false;
    hsel.value = String(h);
    enforceSeatHeightNotAboveLoad(hsel);
    hsel.dataset.userModified = "1";
  }

  // UI-Validierung zurücksetzen
  try { window.markInvalid(input, false); } catch (_) {}
  clearFieldError(input);
  clearInvalidPersonForSeat(seat);

  // Ampel/Hint direkt aktualisieren
  await renderSeatValidityHints(seat);

  return true;
}

async function pasteEntriesSequentially(entries, startSeat = null) {
  const listRaw = (entries || []).filter(Boolean);
  if (!listRaw.length) return;

  const standardSeats = getStandardSeatRowsSorted();
  if (!standardSeats.length) return;

  // IMMER auf Standardsitze kürzen
  const list = listRaw.slice(0, standardSeats.length);

  let beginSeat = startSeat;
  if (beginSeat === null || beginSeat === undefined || !Number.isFinite(Number(beginSeat))) {
    beginSeat = findFirstEditableFreeStandardSeat(standardSeats);
  }

  let cursor = standardSeats.indexOf(Number(beginSeat));
  if (cursor < 0) cursor = 0;

  // Klare Kapazitaetspruefung: Keine Teil-Einfuegung, wenn Auswahl zu gross ist.
  const availableSeats = [];
  for (let i = cursor; i < standardSeats.length; i++) {
    const seat = standardSeats[i];
    const locked = !!elPersonInput(seat)?.disabled;
    const pid = safeStr(elPersonId(seat)?.value);
    if (!locked && !pid) availableSeats.push(seat);
  }

  if (listRaw.length > availableSeats.length) {
    const totalCapacity = getBaseSeatCount() || standardSeats.length;
    alert(
      `Zu viele Eintraege ausgewaehlt: ${listRaw.length}. ` +
      `Im Ziel-Load sind nur ${availableSeats.length} freie regulaere Sitze verfuegbar ` +
      `(Kapazitaet: ${totalCapacity}). Bitte Auswahl reduzieren oder Sitze freimachen.`
    );
    return;
  }

  let failedCount = 0;

  for (const entry of list) {
    // nächsten freien, nicht gesperrten Standardsitz suchen
    while (cursor < standardSeats.length) {
      const seat = standardSeats[cursor];
      const locked = !!elPersonInput(seat)?.disabled;
      const pid = safeStr(elPersonId(seat)?.value);
      if (!locked && !pid) break;
      cursor++;
    }
    if (cursor >= standardSeats.length) break;

    const seat = standardSeats[cursor];
    const ok = await setSeatFromEntry(seat, entry);
    if (!ok) {
      failedCount++;
      console.warn("Paste: konnte Eintrag nicht setzen:", entry);
    }
    cursor++;
  }

  if (failedCount > 0) {
    alert(`${failedCount} Eintrag/Einträge konnten nicht gesetzt werden (Status/Höhe nicht zulässig oder Sitz gesperrt). Bitte korrigieren.`);
  }

  // Nach Batch-Paste: Badges sauber nachziehen
  await renderAllSeatValidityHints();

  // ✅ zentraler Nachlauf: Payload/Warnungen/AutoHeight/Statusrefresh/Draft
          await afterSeatChange({ immediateStatusRefresh: true });
}

async function pasteClipboardIntoEditor() {
  const data = loadClipboard();
  const entries = normalizeEntryArray(data);

  if (!entries.length) {
    alert("Clipboard ist leer. Bitte zuerst in der Load-Liste/Detailansicht kopieren.");
    return;
  }

  await pasteEntriesSequentially(entries, null);
}

// ---------------------------------------------------------------------------
// 23) Drag&Drop: Drop-Ziele im Editor (+ Drag-Quelle + Ctrl+C/Ctrl+V)
// ---------------------------------------------------------------------------
function bindSeatDropTargets() {
  // Guard: doppelte Bindings vermeiden
  if (window.__manifestSeatDnDBound) return;
  window.__manifestSeatDnDBound = true;

  function seatFromEventTarget(target) {
    const el = target && target.closest ? target.closest("tr.seat-row[data-seat]") : null;
    return el ? safeInt(el.dataset.seat, 0) : 0;
  }

  function buildEntryFromSeat(seat) {
    const personId = safeStr(elPersonId(seat)?.value);
    const status = safeStr(elStatus(seat)?.value);
    const height = safeInt(elHeight(seat)?.value, 0);
    if (!personId || !status) return null;

    const gear = getGearRentalForSeatSerialize(seat);
    return { personId, status, height, gear_rental: gear, gearRental: gear };
  }

  function buildPayloadFromSeat(seat) {
    const entry = buildEntryFromSeat(seat);
    if (!entry) return null;
    return { v: 1, entries: [entry] };
  }

  function copySeatToClipboard(seat) {
    const payload = buildPayloadFromSeat(seat);
    if (!payload) return false;
    return saveClipboard(payload);
  }

  async function pasteClipboardToSeat(seat) {
    const data = loadClipboard();
    const entries = normalizeEntryArray(data);
    if (!entries.length) return;

    // pasteEntriesSequentially() enthält in deinem aufgeräumten BLOCK 22
    // bereits den zentralen Nachlauf (afterSeatChange). 
    await pasteEntriesSequentially(entries, seat);
  }

  // ---------------------------
  // A) Drag-Quelle im Editor
  // ---------------------------
  for (const row of qsa("tr.seat-row[data-seat]")) {
    const seat = safeInt(row.dataset.seat, 0);
    if (!seat) continue;

    if (row.dataset.dragSourceBound === "1") continue;
    row.dataset.dragSourceBound = "1";

    row.setAttribute("draggable", "true");

    row.addEventListener("dragstart", (ev) => {
      const s = safeInt(row.dataset.seat, 0);
      if (!s) return;

      const payload = buildPayloadFromSeat(s);
      if (!payload) {
        ev.preventDefault();
        return;
      }

      try {
        ev.dataTransfer.effectAllowed = "copy";
        const raw = JSON.stringify(payload);
        ev.dataTransfer.setData("application/json", raw);
        ev.dataTransfer.setData("text/plain", raw);
      } catch (_) {
        // ignore
      }
    });
  }

// ---------------------------
// B) Drop-Ziele im Editor (Mehrzeilen-Preview auf freie Sitze)
// ---------------------------
const rows = qsa(".seat-row");

// Preview-Helpers
function __clearDropPreview() {
  qsa(".seat-row.drag-over-ok, .seat-row.drag-over-warn, .seat-row.drag-over-limit")
    .forEach((r) => {
      r.classList.remove("drag-over-ok", "drag-over-warn", "drag-over-limit");
      try { r.removeAttribute("title"); } catch (_) {}
    });
}

function __getPreviewCountFromDataTransfer(dt) {
  // Default: 1 Zeile markieren
  let count = 1;
  if (!dt) return count;

  try {
    const raw = dt.getData("application/json") || dt.getData("text/plain") || "";
    if (!raw) return count;

    const payload = JSON.parse(raw);

    // Unterstützt:
    // - { entries:[...] } Paket
    // - { v:1, entries:[...] }
    // - Single (-> 1)
    if (Array.isArray(payload?.entries) && payload.entries.length) {
      count = payload.entries.length;
    }
  } catch (_) {
    // ignore -> count bleibt 1
  }

  // Sicherheitsgrenze (optional) – kann auch entfernt werden:
  count = Math.max(1, Math.min(12, count));
  return count;
}

function __isSeatFreeAndEditable(seatNo) {
  const input = elPersonInput(seatNo);
  const hid = elPersonId(seatNo);

  const locked = !!(input && input.disabled);
  const occupied = !!(hid && safeStr(hid.value));

  return !locked && !occupied;
}

/**
 * Markiert ab startSeat die nächsten freien/editierten Sitze.
 * Belegte / gesperrte Sitze werden übersprungen.
 */
function __applyDropPreviewFreeSeats(startSeat, count) {
  __clearDropPreview();

  const base = getBaseSeatCount();
  const maxSeat = Math.max(
    ...qsa("tr.seat-row[data-seat]").map(r => safeInt(r.dataset.seat, 0)),
    0
  );

  // Vorschau nur auf Standardsitze (bis base). Falls base==0, bis maxSeat.
  const upper = base > 0 ? Math.min(base, maxSeat) : maxSeat;

  let marked = 0;
  let available = 0;

  for (let s = startSeat; s <= upper; s++) {
    const r = qs(`tr.seat-row[data-seat="${s}"]`);
    if (!r) continue;
    if (r.hasAttribute("hidden") || r.style.display === "none") continue;
    if (__isSeatFreeAndEditable(s)) available++;
  }

  const enoughCapacity = available >= count;
  for (let s = startSeat; s <= upper && marked < count; s++) {
    const r = qs(`tr.seat-row[data-seat="${s}"]`);
    if (!r) continue;

    // Optional: versteckte Zeilen (Extrasitze) nicht markieren
    if (r.hasAttribute("hidden") || r.style.display === "none") continue;

    if (!__isSeatFreeAndEditable(s)) {
      // belegt/gesperrt -> überspringen
      continue;
    }

    r.classList.add(enoughCapacity ? "drag-over-ok" : "drag-over-warn");
    marked++;
  }

  return { marked, available, required: count, enoughCapacity };
}

rows.forEach((row) => {
  row.addEventListener("dragover", (ev) => {
    ev.preventDefault();
    try { ev.dataTransfer.dropEffect = "copy"; } catch (_) {}

    const seat = safeInt(row.dataset.seat, 0);
    if (!seat) return;

    const cnt = __getPreviewCountFromDataTransfer(ev.dataTransfer);
    const preview = __applyDropPreviewFreeSeats(seat, cnt);
    if (!preview) return;

    if (!preview.enoughCapacity) {
      row.classList.add("drag-over-limit");
      row.title = `Auswahl: ${preview.required}, freie Sitze ab hier: ${preview.available}`;
    }
  });

  // Kein sofortiges Clear bei dragleave (verhindert Flackern).
  // Preview wird beim nächsten dragover / drop / dragend entfernt.

  row.addEventListener("drop", async (ev) => {
    ev.preventDefault();
    __clearDropPreview();

    const seat = safeInt(row.dataset.seat, 0);
    if (!seat) return;

    const input = elPersonInput(seat);
    if (input && input.disabled) {
      alert("Dieser Sitz ist gesperrt und kann nicht geändert werden.");
      return;
    }

    let payload = null;
    try {
      const raw =
        ev.dataTransfer.getData("application/json") ||
        ev.dataTransfer.getData("text/plain");
      if (raw) payload = JSON.parse(raw);
    } catch (_) {
      payload = null;
    }

    const entries = normalizeEntryArray(payload);
    if (!entries.length) return;

    // Multi/Paket-Drop -> pasteEntriesSequentially nutzt freie Sitze (durch Cursor-Logik)
    // Hinweis: pasteEntriesSequentially startet bei "seat", überspringt aber dort keine belegten Sitze.
    // Wenn du auch beim Drop selbst belegte Sitze überspringen willst, sag Bescheid,
    // dann passen wir den Start-Seat an (erst freien Sitz suchen).
    if (entries.length > 1 || (payload && Array.isArray(payload.entries))) {
      const base = getBaseSeatCount();
      const start = (base && seat > base) ? null : seat;
      await pasteEntriesSequentially(entries, start);
      return;
    }

    // Single-Drop
    const single = entries[0];
    const ok = await setSeatFromEntry(seat, single);
    if (!ok) {
      alert("Eintrag konnte nicht gesetzt werden (Status/Person nicht zulässig oder Sitz gesperrt).");
      return;
    }

    await afterSeatChange();
  });
});

// Wenn Drag irgendwo endet (außerhalb Drop), Preview entfernen
document.addEventListener("dragend", () => __clearDropPreview(), true);
document.addEventListener("drop", () => __clearDropPreview(), true);


  // ---------------------------
  // C) Ctrl+C / Ctrl+V im Editor (Seat-basiert)
  // ---------------------------
  document.addEventListener("keydown", async (ev) => {
    const key = String(ev.key || "").toLowerCase();
    const isCopy = (key === "c" && (ev.ctrlKey || ev.metaKey));
    const isPaste = (key === "v" && (ev.ctrlKey || ev.metaKey));
    if (!isCopy && !isPaste) return;

    const seat = seatFromEventTarget(ev.target);
    if (!seat) return;

    // Nur wenn Fokus im Editor ist
    const table = document.getElementById("load-editor-table");
    if (table && !table.contains(ev.target)) return;

    if (isCopy) {
      const ok = copySeatToClipboard(seat);
      if (ok) ev.preventDefault();
      return;
    }

    if (isPaste) {
      ev.preventDefault();
      await pasteClipboardToSeat(seat);
      // Kein zusätzlicher afterSeatChange nötig:
      // pasteEntriesSequentially() enthält ihn bereits (BLOCK 22). 
    }
  }, true);
}


  // ---------------------------------------------------------------------------
  // 24) Aircraft-Wechsel: KEINE Extrasitze automatisch anzeigen
  // ---------------------------------------------------------------------------
  function bindAircraftSeatVisibility() {
    if (__aircraftVisibilityBound) return;
    __aircraftVisibilityBound = true;

    const aircraftSelect = qs('select[name="aircraft_id"]');
    if (!aircraftSelect) return;

    function parseSeatsFromOptionText(txt) {
      const m = String(txt || "").match(/\((\d+)\s*Sitze\)/i);
      return m ? safeInt(m[1], 0) : null;
    }

    function updateVisibility() {
      const opt = aircraftSelect.options[aircraftSelect.selectedIndex];
      const baseSeats = parseSeatsFromOptionText(opt ? opt.textContent : "");
      if (!baseSeats) return;

      const extraUi = syncExtraSeatsUiCount(baseSeats);
      const maxExtra = MAX_EXTRA_SEATS_PER_LOAD;

      const maxRendered = Math.max(...qsa('tr.seat-row[data-seat]').map((r) => safeInt(r.dataset.seat, 0)), 0);
      for (let s = 1; s <= maxRendered; s++) {
        const row = qs(`tr.seat-row[data-seat="${s}"]`);
        if (!row) continue;

        const isExtra = s > baseSeats && s <= baseSeats + maxExtra;
        if (!isExtra) {
          row.style.display = (s <= baseSeats) ? "" : "none";
          row.classList.remove("extra-seat");
          row.removeAttribute("hidden");
          continue;
        }

        const shouldShow = isSeatRowOccupied(s) || (s <= baseSeats + extraUi);
        row.classList.add("extra-seat");
        if (shouldShow) {
          row.style.display = "";
          row.removeAttribute("hidden");
        } else {
          row.style.display = "none";
          row.setAttribute("hidden", "hidden");
        }
      }
      updateExtraSeatButtonState(baseSeats);
      updateLiveLogic();
    }

    aircraftSelect.addEventListener("change", () => {
      updateVisibility();
      scheduleDraftSave();
    });

    updateVisibility();
  }

  // ---------------------------------------------------------------------------
  // 25) Live Update
  // ---------------------------------------------------------------------------
  function updateLiveLogic() {
    const entries = collectEntriesFromDom();
    applySeatBlockHighlights(entries);
    computeInstructionTwoTeacherWarning(entries);
    applyHeightRowHighlight(entries);
    applyDuplicatePersonHighlights();
    applyGlobalWarnings(computeWarnings(entries));
  }


// ---------------------------------------------------------------------------
// 26) Draft Save/Restore
// - erweitert um gear_rental
// - Restore ist eine "Reset/Rewrite"-Stelle: daher nach Restore Ampel/Hint neu rendern
// ---------------------------------------------------------------------------
function collectDraftSnapshot() {
  const loadId = getLoadIdFromFormAction();
  const form = getSaveForm();
  if (!loadId || !form) return null;

  const airfieldId = safeStr(qs('select[name="airfield_id"]')?.value);
  const aircraftId = safeStr(qs('select[name="aircraft_id"]')?.value);
  const maxPayload = safeStr(qs('input[name="max_payload_kg"]')?.value);
  const actualDate = safeStr(qs('input[name="actual_date"]')?.value);
  const actualTime = safeStr(qs('input[name="actual_time_hm"]')?.value);
  const loadHeight = safeStr(elLoadHeight()?.value);

  const seats = [];
  for (const row of qsa('tr.seat-row[data-seat]')) {
    const seat = safeInt(row.dataset.seat, 0);
    if (!seat) continue;

    const pid = safeStr(elPersonId(seat)?.value);
    const pname = safeStr(elPersonInput(seat)?.value);
    const st = safeStr(elStatus(seat)?.value);
    const h = safeStr(elHeight(seat)?.value);
    const userMod = safeStr(elHeight(seat)?.dataset.userModified);

    // gear_rental (wenn Checkbox existiert)
    let gearRental = false;
    const cbName = getGearRentalInputName(seat);
    const cb = qs(`input[type="checkbox"][name="${CSS.escape(cbName)}"]`);
    if (cb) gearRental = !!cb.checked;

    seats.push({
      seat,
      personId: pid,
      personName: pname,
      status: st,
      height: h,
      userModified: userMod,
      gearRental: gearRental ? "1" : "0",
    });
  }

  return {
    v: 1,
    loadId,
    savedAt: nowMs(),
    airfieldId,
    aircraftId,
    maxPayload,
    actualDate,
    actualTime,
    loadHeight,
    extraSeatsUi: String(getExtraSeatsUiCount()),
    seats
  };
}

function saveDraftNow() {
  const loadId = getLoadIdFromFormAction();
  if (!loadId) return;
  const snap = collectDraftSnapshot();
  if (!snap) return;
  try {
    localStorage.setItem(draftKey(loadId), JSON.stringify(snap));
  } catch (e) {
    console.warn("Draft speichern fehlgeschlagen:", e);
  }
}

function scheduleDraftSave() {
  const loadId = getLoadIdFromFormAction();
  if (!loadId) return;
  if (__draftSaveTimer) window.clearTimeout(__draftSaveTimer);
  __draftSaveTimer = window.setTimeout(() => {
    __draftSaveTimer = null;
    saveDraftNow();
  }, DRAFT_SAVE_DEBOUNCE_MS);
}

function loadDraft(loadId) {
  try {
    const raw = localStorage.getItem(draftKey(loadId));
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj || obj.loadId !== loadId) return null;
    return obj;
  } catch (_) {
    return null;
  }
}

function discardDraft(loadId) {
  try { localStorage.removeItem(draftKey(loadId)); } catch (_) {}
  clearLastSubmit(loadId);
  removeDraftBar();
}

function ensureDraftBar(loadId, draftObj) {
  // nutzt vorhandene Validation-Styles (Draftbar CSS ist dort drin)
  ensureValidationStyles();
  const container = qs(".container") || qs(".container-fluid") || document.body;
  if (!container) return;
  if (qs("#load-editor-draftbar")) return;

  const bar = document.createElement("div");
  bar.id = "load-editor-draftbar";
  bar.className = "load-editor-draftbar";

  const dt = draftObj?.savedAt ? new Date(draftObj.savedAt) : null;
  const timeStr = dt ? dt.toLocaleString() : "unbekannt";

  bar.innerHTML = `
    <div class="msg"><strong>Entwurf gefunden.</strong> Zuletzt gespeichert: ${timeStr}</div>
    <div class="btns">
      <button type="button" class="btn btn-sm btn-outline-primary" id="draft-restore-btn">Wiederherstellen</button>
      <button type="button" class="btn btn-sm btn-outline-secondary" id="draft-discard-btn">Verwerfen</button>
    </div>
  `;
  container.prepend(bar);

  qs("#draft-restore-btn")?.addEventListener("click", async () => {
    await restoreDraft(loadId, draftObj);
  });

  qs("#draft-discard-btn")?.addEventListener("click", () => {
    if (confirm("Entwurf wirklich verwerfen?")) discardDraft(loadId);
  });
}

function removeDraftBar() {
  const bar = qs("#load-editor-draftbar");
  if (bar) bar.remove();
}

function parseDraftGearRental(val) {
  const s = safeStr(val).toLowerCase();
  return s === "1" || s === "true" || s === "on" || s === "ja" || s === "yes";
}

async function restoreDraft(loadId, draftObj) {
  if (!draftObj) return;

  // Grunddaten
  if (draftObj.airfieldId) {
    const s = qs('select[name="airfield_id"]');
    if (s) s.value = draftObj.airfieldId;
  }
  if (draftObj.aircraftId) {
    const s = qs('select[name="aircraft_id"]');
    if (s) s.value = draftObj.aircraftId;
  }
  if (draftObj.maxPayload != null) {
    const i = qs('input[name="max_payload_kg"]');
    if (i) i.value = draftObj.maxPayload;
  }
  if (draftObj.actualDate != null) {
    const i = qs('input[name="actual_date"]');
    if (i) i.value = draftObj.actualDate;
  }
  if (draftObj.actualTime != null) {
    const i = qs('input[name="actual_time_hm"]');
    if (i) i.value = draftObj.actualTime;
  }

  // Extrasitze UI
  if (draftObj.extraSeatsUi != null) {
    setExtraSeatsUiCount(draftObj.extraSeatsUi);
  }

  // Load-Höhe zuerst setzen (damit clamp funktioniert)
  if (draftObj.loadHeight) {
    setLoadHeightValue(draftObj.loadHeight, { fromAuto: true });
  }

  // Sitze anwenden
  const seats = Array.isArray(draftObj.seats) ? draftObj.seats : [];
  for (const e of seats) {
    const seat = safeInt(e.seat, 0);
    if (!seat) continue;

    const inp = elPersonInput(seat);
    const hid = elPersonId(seat);
    const stSel = elStatus(seat);
    const hSel = elHeight(seat);

    if (inp && !inp.disabled) inp.value = safeStr(e.personName);
    if (hid) hid.value = safeStr(e.personId);

    // invalid-person sofort neu bewerten
    evalInvalidPersonForSeat(seat);

    if (hSel && !hSel.disabled) {
      if (e.height) hSel.value = String(e.height);
      if (e.userModified) hSel.dataset.userModified = String(e.userModified);
    }

    // Personwechsel: Statusfilter neu (aber Draft soll Status wiederherstellen)
    hardResetSeatOnPersonChange(seat);
    await applyStatusFilterForSeat(seat);

    if (stSel && !stSel.disabled) {
      const want = safeStr(e.status);
      const exists = Array.from(stSel.options).some(o => o.value === want);
      stSel.value = exists ? want : "";
      stSel.dataset.prevValue = safeStr(stSel.value);
    }

    if (hSel && !hSel.disabled) {
      enforceSeatHeightNotAboveLoad(hSel);
    }

    // gear_rental erst nach Status setzen
    hardResetSeatOnStatusChange(seat);
    const wantGear = parseDraftGearRental(e.gearRental);
    renderGearRentalUi(seat, { checked: wantGear });
  }

  // Sichtbarkeit & Recalc
  bindAircraftSeatVisibility();
  await updatePayloadSum();
  updateLiveLogic();

  // ✅ NEU: nach Restore Ampel/Hint für alle Sitze neu rendern
  await renderAllSeatValidityHints();

  autoAdjustLoadHeightToOccupiedMax({ force: false });

  removeDraftBar();
  clearLastSubmit(loadId);
  scheduleDraftSave();
}

async function maybeAutoRestoreDraft() {
  const loadId = getLoadIdFromFormAction();
  if (!loadId) return;

  const draftObj = loadDraft(loadId);
  if (!draftObj) return;

  ensureDraftBar(loadId, draftObj);

  // Auto-restore nur, wenn kurz zuvor ein Submit war (z.B. Serverfehler)
  const lastSubmit = getLastSubmitMs(loadId);
  const age = lastSubmit ? (nowMs() - lastSubmit) : Number.POSITIVE_INFINITY;

  if (age <= AUTO_RESTORE_WINDOW_MS) {
    await restoreDraft(loadId, draftObj);
  }
}


// ---------------------------------------------------------------------------
// 27) Init
// ---------------------------------------------------------------------------
async function initEditor() {
  __pageLoadedAt = nowMs();
  await loadStatusList();
  bindExtraSeatButton();

  // ----------------------------
  // Load-Höhe
  // ----------------------------
  const loadHeightSelect = elLoadHeight();
  if (loadHeightSelect) {
    const parsed = normalizeHeightValue(loadHeightSelect.value);
    currentLoadHeight = parsed || null;

    loadHeightSelect.addEventListener("change", () => {
      const newH = normalizeHeightValue(loadHeightSelect.value);
      const oldH = currentLoadHeight;
      currentLoadHeight = newH || null;

      applyLoadHeightToSeatDefaults(oldH, currentLoadHeight, { fromAuto: false });
      updateLiveLogic();
      scheduleDraftSave();
    });
  }

  // ----------------------------
  // Status-Selects initialisieren
  // ----------------------------
  qsa(".status-select").forEach((select) => {
    populateStatusSelect(select);

    const match = String(select.id || "").match(/seat_(\d+)_status_code/);
    const seat = match ? safeInt(match[1], 0) : 0;

    if (seat) {
      select.dataset.prevValue = safeStr(select.value);
      applyStatusFilterForSeat(seat).catch(() => {});
      renderGearRentalUi(seat);
    }

    select.addEventListener("change", async () => {
      const match2 = String(select.id || "").match(/seat_(\d+)_status_code/);
      const seat2 = match2 ? safeInt(match2[1], 0) : 0;
      if (!seat2) return;

      clearFieldError(select);
      select.dataset.userSelected = "1";
      select.dataset.initialApplied = "1";
      try { delete select.dataset.initial; } catch (_) {}

      hardResetSeatOnStatusChange(seat2);

      const pid = safeStr(elPersonId(seat2)?.value);
      const newVal = safeStr(select.value);

      // Status muss zur Person passen (Frontend-UX)
      if (pid) {
        const p = await getPerson(pid);
        if (p) {
          const seatStatusList = await loadSeatStatusList(seat2, pid, p);
          const allowed = allowedStatusesForPerson(
            p,
            seatStatusList.length ? seatStatusList : statusList
          );
          if (newVal && !allowed.includes(newVal)) {
            select.value = safeStr(select.dataset.prevValue);
            alert("Status passt nicht zur Person.");
            renderGearRentalUi(seat2);
            return;
          }
        }
      }

      select.dataset.prevValue = safeStr(select.value);
      maybeTriggerFillHintFromStatus(select);
      renderGearRentalUi(seat2);

      await renderSeatValidityHints(seat2);

      // ✅ zentraler Nachlauf: Payload/Warnungen/AutoHeight/Statusrefresh/Draft
      await afterSeatChange({ immediateStatusRefresh: true });
    });
  });

  // ----------------------------
  // Person Inputs
  // ----------------------------
  qsa(".person-input").forEach((input) => {
    const seat = safeInt(input.dataset.seat, 0);
    if (seat) input.setAttribute("name", `seat_${seat}_person_name`);

    window.bindAutocomplete(input, seat);

    input.addEventListener("input", () => {
      evalInvalidPersonForSeat(seat);
      scheduleDraftSave();
    }, true);

    input.addEventListener("change", () => {
      evalInvalidPersonForSeat(seat);
      scheduleDraftSave();
    }, true);

    evalInvalidPersonForSeat(seat);
  });

  // Clear (X) Buttons
  qsa(".clear-seat").forEach((btn) => {
    window.bindClearButton(btn, btn.dataset.seat);
  });

  // Sitz-Höhen
  qsa(".seat-height").forEach((sel) => {
    sel.addEventListener("change", () => {
      sel.dataset.userModified = "1";
      enforceSeatHeightNotAboveLoad(sel);
      updateLiveLogic();
      autoAdjustLoadHeightToOccupiedMax({ force: false });
      scheduleDraftSave();
    });
  });

  // Guards & Styles
  window.bindSubmitGuard();
  window.ensureAutocompleteScrollbarStyles();
  bindMaxPayloadInput();

  // Clipboard: Paste
  const pasteBtn = qs("#paste_from_clipboard");
  if (pasteBtn) {
    pasteBtn.addEventListener("click", async () => {
      await pasteClipboardIntoEditor();
      await afterSeatChange();
    });
  }

  // Clipboard: Clear
  const clearBtn = qs("#clear_clipboard");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      try { localStorage.removeItem(CLIPBOARD_KEY); } catch (_) {}
      alert("Clipboard geleert.");
    });
  }

  // Copy / Drag&Drop aktivieren
  bindSeatDropTargets();

  // Aircraft seat visibility
  bindAircraftSeatVisibility();

  // Draft Auto-Restore (vor Initial-Recalc!)
  await maybeAutoRestoreDraft();

  // Initial clamp + Recalc
  if (currentLoadHeight) {
    applyLoadHeightToSeatDefaults(currentLoadHeight, currentLoadHeight, { fromAuto: true });
  }

  // Initialer Recalc (einmal sauber)
  await updatePayloadSum();
  updateLiveLogic();
  await renderAllSeatValidityHints();
  autoAdjustLoadHeightToOccupiedMax({ force: false });

  const form = getSaveForm();
  if (form) {
    form.addEventListener("input", () => scheduleDraftSave(), true);
    form.addEventListener("change", () => scheduleDraftSave(), true);
  }
}

  // ---------------------------------------------------------------------------
  // 28) Split-View / Re-Init Support (robust)
  // ---------------------------------------------------------------------------
  let __editorInitPromise = null;

  function initEditorOnce() {
    if (__editorInitPromise) return __editorInitPromise;

    const hasEditorTable = document.getElementById("load-editor-table");
    const hasSaveForm = document.getElementById("load-save-form");
    if (!hasEditorTable && !hasSaveForm) {
      return Promise.resolve();
    }

    __editorInitPromise = Promise.resolve()
      .then(() => initEditor())
      .catch((err) => {
        __editorInitPromise = null;
        console.error("[load_editor] initEditor failed:", err);
        throw err;
      });

    return __editorInitPromise;
  }

  window.initLoadEditor = initEditorOnce;

  document.addEventListener("DOMContentLoaded", () => {
    initEditorOnce();
  });

  if (document.readyState !== "loading") {
    initEditorOnce();
  }

})();
// === MANIFEST FILE END: app/static/load/load_editor.js ===
// EOF