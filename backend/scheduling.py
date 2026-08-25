DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]
DIAS_ABREV = ["SEG", "TER", "QUA", "QUI", "SEX"]

TURNO_SLOTS = {
    "matutino": [
        ("07:00", "07:50"), ("07:50", "08:40"), ("08:50", "09:40"),
        ("09:40", "10:30"), ("10:40", "11:30"), ("11:30", "12:20"),
    ],
    "vespertino": [
        ("13:00", "13:50"), ("13:50", "14:40"), ("14:50", "15:40"),
        ("15:40", "16:30"), ("16:40", "17:30"), ("17:30", "18:20"),
    ],
    "noturno": [
        ("19:00", "19:50"), ("19:50", "20:40"), ("20:50", "21:40"), ("21:40", "22:30"),
    ],
}


def get_slots(turno: str):
    return TURNO_SLOTS.get(turno, TURNO_SLOTS["noturno"])


def auto_generate(disciplinas, professor_busy, turno):
    """
    disciplinas: list of dicts with id, professor_id, aulas_por_semana, nome
    professor_busy: set of (professor_id, dia_semana, hora_inicio) already occupied in OTHER grades
    Returns (entries, conflicts)
    """
    slots = get_slots(turno)
    n_days = len(DIAS_SEMANA)
    n_slots = len(slots)

    cell_used = set()          # (dia, slot) used in this grade
    prof_used = set(professor_busy)  # (prof, dia, hora_inicio) globally
    entries = []
    conflicts = []

    # order disciplines by demand descending for better packing
    ordered = sorted(disciplinas, key=lambda d: d.get("aulas_por_semana", 0), reverse=True)

    for disc in ordered:
        needed = int(disc.get("aulas_por_semana", 0) or 0)
        prof = disc.get("professor_id")
        placed = 0
        # try to spread across days: iterate slot-major then day
        for slot_i in range(n_slots):
            for day in range(n_days):
                if placed >= needed:
                    break
                if (day, slot_i) in cell_used:
                    continue
                hi, hf = slots[slot_i]
                if prof and (prof, day, hi) in prof_used:
                    continue
                cell_used.add((day, slot_i))
                if prof:
                    prof_used.add((prof, day, hi))
                entries.append({
                    "dia_semana": day,
                    "slot_index": slot_i,
                    "hora_inicio": hi,
                    "hora_fim": hf,
                    "disciplina_id": disc["id"],
                    "professor_id": prof,
                })
                placed += 1
            if placed >= needed:
                break
        if placed < needed:
            conflicts.append({
                "disciplina_id": disc["id"],
                "disciplina_nome": disc.get("nome", ""),
                "solicitado": needed,
                "alocado": placed,
                "motivo": "Sem horário disponível sem conflito de professor",
            })

    return entries, conflicts
