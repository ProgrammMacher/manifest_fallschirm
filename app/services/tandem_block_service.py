# C:\manifest_fallschirm\app\services\tandem_block_service.py
def build_tandem_blocks(load):
    """
    Liefert Block-/Single-Struktur für UI (Liste/Editor/Detail).

    Blocktypen:
    - video3: G-TD-Video + r(TD/TD-Vereins-Schirm) + Video
    - tandem2: G-TD + (TD/TD-Vereins-Schirm)
    - instruction: Lehrer + 1..n Schüler (Sitznähe), Schüler ggf. mit 2 Lehrern (Warnung)

    Rückgabeformat:
    [
      {
        "type": "block",
        "block_type": "video3|tandem2|instruction",
        "block_id": int,
        "color_index": int,
        "css_class": str,
        "entries": [LoadEntry, ...],
        "entry_ids": [int, ...],
        "warnings": [str, ...]
      },
      { "type":"single", "entry": LoadEntry, "entry_id": int }
    ]
    """

    STATUS_G_TD_VIDEO = "G-TD-Video"
    STATUS_G_TD = "G-TD"
    STATUS_TD = "TD"
    STATUS_TD_VEREIN = "TD-Vereins-Schirm"
    VIDEO_STATUSES = {"Video", "Videomann"}  # ✅ konsistent zu Client/Validation
    STATUS_TEACHER = "Lehrer"
    STATUS_AFF_TEACHER = "AFF-LEHRER"
    STUDENT_STATUSES = {"Schüler", "Schüler Ek 1", "Schüler Ek 2", "Schüler GK 6"}
    AFF_STUDENT_STATUSES = {"SCHUELER-AFF-1", "SCHUELER-AFF-2"}
    TD_STATUSES = {STATUS_TD, STATUS_TD_VEREIN}

    def seat_key(e):
        return (e.seat if e.seat is not None else 10_000_000)

    entries = sorted(list(load.entries), key=seat_key)

    used_ids = set()
    result = []
    next_block_id = 1

    def is_free(e):
        return e is not None and e.id not in used_ids

    def mark_used(block_entries):
        for x in block_entries:
            used_ids.add(x.id)

    def distinct_persons(block_entries):
        pids = []
        for x in block_entries:
            pid = getattr(x, "person_id", None)
            if pid is None:
                return False
            pids.append(pid)
        return len(pids) == len(set(pids))

    def best_match(candidates, ref_entry, forbidden_person_ids):
        ref_seat = ref_entry.seat if ref_entry and ref_entry.seat is not None else 0
        best = None
        best_dist = None
        for c in candidates:
            if not is_free(c):
                continue
            pid = getattr(c, "person_id", None)
            if pid in forbidden_person_ids:
                continue
            c_seat = c.seat if c.seat is not None else 0
            dist = abs(c_seat - ref_seat)
            if best is None or dist < best_dist:
                best = c
                best_dist = dist
        return best

    # Kandidaten
    gtdv = [e for e in entries if e.status_code == STATUS_G_TD_VIDEO]
    gtd = [e for e in entries if e.status_code == STATUS_G_TD]
    td = [e for e in entries if e.status_code in TD_STATUSES]
    video = [e for e in entries if e.status_code in VIDEO_STATUSES]
    teachers = [
        e for e in entries
        if (e.status_code or "").strip().upper() in {STATUS_TEACHER.upper(), STATUS_AFF_TEACHER}
    ]
    students = [
        e for e in entries
        if (e.status_code in STUDENT_STATUSES) or ((e.status_code or "").strip().upper() in AFF_STUDENT_STATUSES)
    ]

    # -------------------------------
    # 1) Tandem: 3er (G-TD-Video + TD + Video)
    # -------------------------------
    for guest in gtdv:
        if not is_free(guest):
            continue
        forbidden = {guest.person_id}
        td_pick = best_match(td, guest, forbidden)
        if not td_pick:
            continue
        forbidden.add(td_pick.person_id)
        v_pick = best_match(video, guest, forbidden)
        if not v_pick:
            continue
        block_entries = sorted([guest, td_pick, v_pick], key=seat_key)
        if not distinct_persons(block_entries):
            continue
        mark_used(block_entries)
        color_index = ((next_block_id - 1) % 10) + 1
        result.append({
            "type": "block",
            "block_type": "video3",
            "block_id": next_block_id,
            "color_index": color_index,
            "css_class": f"tandem-seat tandem-seat-{color_index}",
            "entries": block_entries,
            "entry_ids": [x.id for x in block_entries],
            "warnings": [],
        })
        next_block_id += 1

    # -------------------------------
    # 2) Tandem: 2er (G-TD + TD)
    # -------------------------------
    for guest in gtd:
        if not is_free(guest):
            continue
        forbidden = {guest.person_id}
        td_pick = best_match(td, guest, forbidden)
        if not td_pick:
            continue
        block_entries = sorted([guest, td_pick], key=seat_key)
        if not distinct_persons(block_entries):
            continue
        mark_used(block_entries)
        color_index = ((next_block_id - 1) % 10) + 1
        result.append({
            "type": "block",
            "block_type": "tandem2",
            "block_id": next_block_id,
            "color_index": color_index,
            "css_class": f"tandem-seat tandem-seat-{color_index}",
            "entries": block_entries,
            "entry_ids": [x.id for x in block_entries],
            "warnings": [],
        })
        next_block_id += 1

    # -------------------------------
    # 3) Lehrer/Schüler: Schüler->nächstgelegener Lehrer (Primary),
    #    und orphan Teacher bekommt notfalls Secondary (Warnung).
    #    Ziel: Ein Lehrer soll nicht "leer" bleiben (außer Admin kann Regeln brechen).
    # -------------------------------
    free_teachers = [t for t in teachers if is_free(t)]
    free_students = [s for s in students if is_free(s)]

    if free_teachers and free_students:
        # Primary: jedem Schüler genau 1 Lehrer (nächstgelegen)
        teacher_list = [(t, (t.seat if t.seat is not None else 0)) for t in free_teachers]

        student_to_teachers = {s.id: [] for s in free_students}  # bis zu 2 Lehrer
        student_primary_teacher = {}  # s.id -> t.id
        teacher_degree = {t.id: 0 for t in free_teachers}

        for s in free_students:
            s_seat = s.seat if s.seat is not None else 0
            best_t = None
            best_d = None
            for t, t_seat in teacher_list:
                if t.person_id == s.person_id:
                    continue
                d = abs(s_seat - t_seat)
                if best_t is None or d < best_d:
                    best_t = t
                    best_d = d
            if best_t:
                student_to_teachers[s.id].append(best_t)
                student_primary_teacher[s.id] = best_t.id
                teacher_degree[best_t.id] += 1

        # Orphan teachers (kein Schüler) -> Reassign wenn möglich, sonst Secondary (Warnung)
        orphan_teachers = [t for t in free_teachers if teacher_degree.get(t.id, 0) == 0]

        def closest_student_for_teacher(t):
            t_seat = t.seat if t.seat is not None else 0
            best_s = None
            best_d = None
            for s in free_students:
                if s.person_id == t.person_id:
                    continue
                s_seat = s.seat if s.seat is not None else 0
                d = abs(t_seat - s_seat)
                if best_s is None or d < best_d:
                    best_s = s
                    best_d = d
            return best_s

        warn_two_teachers_student_ids = set()

        for t in orphan_teachers:
            # Versuch 1: student von einem Lehrer abziehen, der >1 Schüler hat (unique, keine Überlappung)
            candidate = None
            candidate_d = None
            for s in free_students:
                primary_tid = student_primary_teacher.get(s.id)
                if primary_tid is None:
                    continue
                if teacher_degree.get(primary_tid, 0) <= 1:
                    continue  # würde den anderen Lehrer "leer" machen
                if s.person_id == t.person_id:
                    continue
                d = abs((s.seat or 0) - (t.seat or 0))
                if candidate is None or d < candidate_d:
                    candidate = s
                    candidate_d = d

            if candidate is not None:
                # Reassign: candidate wechselt primary zu orphan teacher
                old_primary_tid = student_primary_teacher.get(candidate.id)
                if old_primary_tid is not None:
                    teacher_degree[old_primary_tid] = max(0, teacher_degree.get(old_primary_tid, 0) - 1)
                student_primary_teacher[candidate.id] = t.id
                # Ersetze den primary teacher im teachers-array (erste Position)
                student_to_teachers[candidate.id] = [t]
                teacher_degree[t.id] = teacher_degree.get(t.id, 0) + 1
                continue

            # Versuch 2: Secondary anhängen (max 2), Warnung
            s = closest_student_for_teacher(t)
            if not s:
                continue
            if len(student_to_teachers[s.id]) >= 2:
                continue
            student_to_teachers[s.id].append(t)
            teacher_degree[t.id] = teacher_degree.get(t.id, 0) + 1
            warn_two_teachers_student_ids.add(s.id)

        # Blocks pro Lehrer: Lehrer + alle Schüler, deren Primary dieser Lehrer ist,
        # plus ggf. Schüler, die ihn als Secondary haben (für Orphans/2-Lehrer-Warnung).
        # Wichtig: Wir verhindern Overwrite später in Templates (first wins).
        instruction_block_index = 1

        # Hilfsmap: teacher_id -> students
        teacher_to_students = {t.id: [] for t in free_teachers}
        for s in free_students:
            ts = student_to_teachers.get(s.id, [])
            for t in ts:
                if t.id in teacher_to_students:
                    teacher_to_students[t.id].append(s)

        for t in sorted(free_teachers, key=seat_key):
            assigned_students = teacher_to_students.get(t.id, [])
            if not assigned_students:
                # "Lehrer nie ohne Schüler" wird serverseitig beim Save geprüft/gebremst
                continue

            block_entries = sorted([t] + assigned_students, key=seat_key)
            if not distinct_persons(block_entries):
                continue

            # Mark used erst hier (damit Tandem/Singles nicht doppelt werden)
            mark_used(block_entries)

            color_index = ((instruction_block_index - 1) % 5) + 1
            warnings = []
            if any(s.id in warn_two_teachers_student_ids for s in assigned_students):
                warnings.append("Achtung, zwei Lehrer für einen Schüler!")

            result.append({
                "type": "block",
                "block_type": "instruction",
                "block_id": next_block_id,
                "color_index": color_index,
                "css_class": f"instruction-seat instruction-seat-{color_index}",
                "entries": block_entries,
                "entry_ids": [x.id for x in block_entries],
                "warnings": warnings,
            })
            next_block_id += 1
            instruction_block_index += 1

    # -------------------------------
    # 4) Singles
    # -------------------------------
    for e in entries:
        if e.id in used_ids:
            continue
        used_ids.add(e.id)
        result.append({"type": "single", "entry": e, "entry_id": e.id})

    return result