// C:\manifest_fallschirm\app\static\load\load_blocks_view.js
// READ-ONLY Block-Färbung für LISTE & DETAIL
// - Keine Requests, keine Datenänderung, keine Form-Interaktion
// - Setzt nur CSS-Klassen: tandem-seat(-n) und instruction-seat(-n)
// - Nutzt vorhandene data-Attribute (wird von Templates gesetzt)
(() => {
  "use strict";
  // Statuskonstanten (müssen zur App passen)
  const STUDENT_STATUSES = ["Schüler", "Schüler Ek 1", "Schüler Ek 2", "Schüler GK 6"];
  const AFF_TEACHER_STATUS = "AFF-LEHRER";
  const AFF_STUDENT_STATUSES = ["SCHUELER-AFF-1", "SCHUELER-AFF-2"];
  const TD_STATUSES = ["TD", "TD-Vereins-Schirm"];
  // Historisch kann Video als "Videomann" vorkommen – Anzeige bleibt "Video", Logik akzeptiert beides
  const VIDEO_STATUS_CODES = ["Video", "Videomann"];
  const TANDEM_PALETTE_SIZE = 10;
  // ✅ Konsistent zum Backend: 5 Gelbtöne rotierend für Instruction-Blöcke
  const INSTRUCTION_PALETTE_SIZE = 5;

  function safeStr(v) {
    return String(v || "").trim();
  }

  function normalizeAffStatus(v) {
    return safeStr(v)
      .toUpperCase()
      .replace(/Ü/g, "UE")
      .replace(/Ä/g, "AE")
      .replace(/Ö/g, "OE");
  }

  function isAffTeacherStatus(v) {
    return normalizeAffStatus(v) === AFF_TEACHER_STATUS;
  }

  function isAffStudentStatus(v) {
    return AFF_STUDENT_STATUSES.includes(normalizeAffStatus(v));
  }

  function clearBlockClasses(el) {
    if (!el || !el.classList) return;
    const rm = [];
    el.classList.forEach((c) => {
      if (
        c === "tandem-seat" ||
        c.startsWith("tandem-seat-") ||
        c === "instruction-seat" ||
        c.startsWith("instruction-seat-")
      ) rm.push(c);
    });
    rm.forEach((c) => el.classList.remove(c));
  }

  function hasAnyBlockClass(el, base) {
    if (!el || !el.classList) return false;
    if (el.classList.contains(base)) return true;
    for (const c of el.classList) {
      if (c.startsWith(base + "-")) return true;
    }
    return false;
  }

  function addBlockClasses(el, base, idx, { skipIfAlready = false } = {}) {
    if (!el || !el.classList) return;
    if (skipIfAlready && hasAnyBlockClass(el, base)) return;
    el.classList.add(base);
    el.classList.add(`${base}-${idx}`);
  }

  function parseEntries(scopeEl) {
    const nodes = scopeEl.querySelectorAll("[data-block-entry='1']");
    const out = [];
    nodes.forEach((el) => {
      const seat = parseInt(el.dataset.seat || "", 10);
      const status = (el.dataset.status || "").trim();
      const personId = (el.dataset.personId || "").trim();
      const height = parseInt(el.dataset.height || "0", 10);
      if (!Number.isFinite(seat) || !status) return;
      out.push({ seat, status, personId, height, el });
    });
    out.sort((a, b) => a.seat - b.seat);
    return out;
  }

  // ---------------- Tandem-Blocks (matching wie Editor, read-only) ----------------
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
        if (disallowPersonId && c.personId && String(c.personId) === String(disallowPersonId)) continue;
        const d = Math.abs(target.seat - c.seat);
        if (best === null || d < bestD || (d === bestD && c.seat < best.seat)) {
          best = c;
          bestD = d;
        }
      }
      return best;
    }

    // 3er: G-TD-Video + TD + Video
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

    // 2er: G-TD + TD
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

  // ---------------- Instruction Blocks: Schüler -> nächster Lehrer ----------------
  function computeInstructionBlocks(entries, tandemSeats) {
    const teachers = entries.filter((e) => (safeStr(e.status) === "Lehrer" || isAffTeacherStatus(e.status)) && !tandemSeats.has(e.seat));
    const students = entries.filter((e) => (STUDENT_STATUSES.includes(safeStr(e.status)) || isAffStudentStatus(e.status)) && !tandemSeats.has(e.seat));
    const blocks = [];
    if (!teachers.length || !students.length) {
      return { blocks, studentSeats: students.map(s => s.seat) };
    }

    const teacherSeatsSorted = [...teachers].sort((a, b) => a.seat - b.seat);

    // Primary mapping: each student -> nearest teacher
    const studentPrimary = new Map(); // studentSeat -> teacherSeat
    const studentToTeachers = new Map(); // studentSeat -> [teacherSeat...]
    const teacherToStudents = new Map(); // teacherSeat -> [studentSeat...]
    teacherSeatsSorted.forEach(t => teacherToStudents.set(t.seat, []));
    students.forEach(s => studentToTeachers.set(s.seat, []));

    for (const s of students) {
      let bestT = null;
      let bestD = null;
      for (const t of teacherSeatsSorted) {
        if (t.personId && s.personId && String(t.personId) === String(s.personId)) continue;
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

    // Ensure no teacher stays empty: reassign, otherwise add as secondary teacher.
    for (const t of teacherSeatsSorted) {
      const assigned = teacherToStudents.get(t.seat) || [];
      if (assigned.length > 0) continue;

      let bestStudentSeat = null;
      let bestD = null;

      for (const s of students) {
        const currentTeacherSeat = studentPrimary.get(s.seat);
        if (currentTeacherSeat == null) continue;
        const currentList = teacherToStudents.get(currentTeacherSeat) || [];
        if (currentList.length <= 1) continue; // don't orphan the other teacher

        const d = Math.abs(s.seat - t.seat);
        if (bestStudentSeat === null || d < bestD) {
          bestStudentSeat = s.seat;
          bestD = d;
        }
      }

      if (bestStudentSeat !== null) {
        const oldT = studentPrimary.get(bestStudentSeat);
        if (oldT != null) {
          teacherToStudents.set(oldT, (teacherToStudents.get(oldT) || []).filter(x => x !== bestStudentSeat));
        }
        studentPrimary.set(bestStudentSeat, t.seat);
        studentToTeachers.set(bestStudentSeat, [t.seat]);
        teacherToStudents.get(t.seat).push(bestStudentSeat);
        continue;
      }

      let secondarySeat = null;
      let secondaryD = null;
      for (const s of students) {
        if (s.personId && t.personId && String(s.personId) === String(t.personId)) continue;
        const assignedTeachers = studentToTeachers.get(s.seat) || [];
        if (assignedTeachers.includes(t.seat)) continue;
        if (assignedTeachers.length >= 2) continue;
        const d = Math.abs((s.seat || 0) - (t.seat || 0));
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

    // Build blocks per teacher (teacher + all students assigned)
    for (const t of teacherSeatsSorted) {
      const sts = Array.from(new Set((teacherToStudents.get(t.seat) || []).slice().sort((a, b) => a - b)));
      if (!sts.length) continue;
      blocks.push([t.seat, ...sts]);
    }

    return { blocks, studentSeats: students.map(s => s.seat) };
  }

  function applyForScope(scopeEl) {
    const entries = parseEntries(scopeEl);
    if (!entries.length) return;

    // Reset
    entries.forEach((e) => clearBlockClasses(e.el));
    const bySeat = new Map(entries.map((e) => [e.seat, e.el]));

    // Tandem anwenden
    const tandemBlocks = computeTandemBlocks(entries);
    const tandemSeats = new Set();
    tandemBlocks.forEach((b) => b.forEach((s) => tandemSeats.add(s)));
    tandemBlocks.forEach((seats, i) => {
      const idx = (i % TANDEM_PALETTE_SIZE) + 1;
      seats.forEach((seat) => addBlockClasses(bySeat.get(seat), "tandem-seat", idx));
    });

    // Instruction anwenden (Schüler->Lehrer)
    const instr = computeInstructionBlocks(entries, tandemSeats);
    let blockNo = 0;

    instr.blocks.forEach((seats) => {
      blockNo++;
      const idx = ((blockNo - 1) % INSTRUCTION_PALETTE_SIZE) + 1;
      seats.forEach((seat) =>
        addBlockClasses(bySeat.get(seat), "instruction-seat", idx, { skipIfAlready: true })
      );
    });

    // ✅ Schüler generell gelb darstellen, auch ohne erkannten Lehrer-Block
    instr.studentSeats.forEach((sSeat) => {
      const el = bySeat.get(sSeat);
      if (!el) return;
      if (hasAnyBlockClass(el, "tandem-seat")) return;
      if (!hasAnyBlockClass(el, "instruction-seat")) {
        addBlockClasses(el, "instruction-seat", 1);
      }
    });
  }

  function run() {
    const scopes = document.querySelectorAll("[data-block-scope='load']");
    if (!scopes.length) return;
    // defensive: niemals UI blockieren, keine Exceptions nach außen
    requestAnimationFrame(() => {
      scopes.forEach((scope) => {
        try {
          applyForScope(scope);
        } catch (e) {
          console.warn("load_blocks_view.js: Fehler bei Block-Färbung (ignoriert):", e);
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
  
  
    // ------------------------------------------------------------
  // 🔄 Öffentliche Refresh-Funktion (Option B)
  // ------------------------------------------------------------
  // Diese Funktion erlaubt es, die Block-Färbung erneut auszuführen,
  // z.B. nach HTMX-Updates, AJAX-Reloads oder dynamischen DOM-Änderungen.
  //
  // Sie ist vollständig stabil:
  // - keine doppelten Klassen
  // - keine Nebenwirkungen
  // - keine Requests
  // - keine Abhängigkeiten vom Editor
  // - defensive Fehlerbehandlung
  //
  // Aufruf:
  //    refreshLoadBlockColors();              // gesamte Seite
  //    refreshLoadBlockColors(containerEl);   // nur bestimmter Bereich
  //
  window.refreshLoadBlockColors = function refreshLoadBlockColors(root) {
    try {
      const scopeRoot = root || document;
      const scopes = scopeRoot.querySelectorAll("[data-block-scope='load']");
      if (!scopes.length) return;

      requestAnimationFrame(() => {
        scopes.forEach((scope) => {
          try {
            applyForScope(scope);
          } catch (e) {
            console.warn("refreshLoadBlockColors: Fehler (ignoriert):", e);
          }
        });
      });
    } catch (e) {
      console.warn("refreshLoadBlockColors: globaler Fehler (ignoriert):", e);
    }
  };

  
  
})();
