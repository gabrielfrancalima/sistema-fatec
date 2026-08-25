from io import BytesIO
from datetime import date, timedelta
import calendar

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from scheduling import DIAS_SEMANA

FATEC_RED = colors.HexColor("#B20000")
FATEC_RED_LIGHT = colors.HexColor("#FF161F")
SLATE = colors.HexColor("#273336")
LIGHT = colors.HexColor("#F3F4F6")

MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("FatecTitle", parent=ss["Title"], fontName="Helvetica-Bold",
                          fontSize=15, textColor=SLATE, spaceAfter=2, alignment=TA_CENTER))
    ss.add(ParagraphStyle("FatecSub", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=9, textColor=colors.HexColor("#555555"), alignment=TA_CENTER))
    ss.add(ParagraphStyle("SectTitle", parent=ss["Normal"], fontName="Helvetica-Bold",
                          fontSize=11, textColor=colors.white, alignment=TA_LEFT))
    ss.add(ParagraphStyle("Meta", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=9, textColor=SLATE, leading=13))
    ss.add(ParagraphStyle("CellSm", parent=ss["Normal"], fontName="Helvetica", fontSize=8, leading=10))
    return ss


def _header(ss, subtitulo):
    els = []
    els.append(Paragraph("CENTRO ESTADUAL DE EDUCAÇÃO TECNOLÓGICA PAULA SOUZA", ss["FatecSub"]))
    els.append(Paragraph("FATEC — Faculdade de Tecnologia", ss["FatecTitle"]))
    els.append(Paragraph(subtitulo, ss["FatecSub"]))
    els.append(Spacer(1, 4))
    els.append(HRFlowable(width="100%", thickness=2, color=FATEC_RED_LIGHT))
    els.append(Spacer(1, 8))
    return els


def _meta_table(ss, pairs):
    data = []
    for i in range(0, len(pairs), 2):
        row = []
        for j in range(2):
            if i + j < len(pairs):
                k, v = pairs[i + j]
                row.append(Paragraph(f"<b>{k}:</b> {v}", ss["Meta"]))
            else:
                row.append("")
        data.append(row)
    t = Table(data, colWidths=[95 * mm, 95 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _dates_in_month(ano, mes, weekday):
    """weekday: 0=Mon..4=Fri (python weekday). Return list of date objects."""
    dias = []
    _, last = calendar.monthrange(ano, mes)
    for d in range(1, last + 1):
        dt = date(ano, mes, d)
        if dt.weekday() == weekday:
            dias.append(dt)
    return dias


def gerar_folha_professor(professor, curso, entries_prof, ano, mes, feriados, aulas_remotas, disciplinas_map):
    """
    entries_prof: list of grade entries (dicts) for this professor within the given curso context
    feriados: dict {YYYY-MM-DD: descricao}
    aulas_remotas: set of YYYY-MM-DD strings for this professor/curso
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = _styles()
    els = _header(ss, "FOLHA DE PONTO / FREQUÊNCIA DOCENTE")

    els.append(_meta_table(ss, [
        ("Docente", professor.get("nome", "")),
        ("Titulação", professor.get("titulacao", "")),
        ("Curso", f"{curso.get('nome','')} ({curso.get('sigla','')})" if curso else "Todos"),
        ("Período", f"{MESES[mes]} / {ano}"),
        ("Turno", (curso.get("turno", "") if curso else "").capitalize()),
        ("Registro", professor.get("registro", "") or "-"),
    ]))
    els.append(Spacer(1, 8))

    # Build rows: for each grade entry (day of week + time), list every occurrence in month
    header = ["Data", "Dia", "Disciplina", "Horário", "Modalidade", "Assinatura"]
    rows = [header]

    occurrences = []
    for e in entries_prof:
        wd = e["dia_semana"]  # 0=Segunda -> python Monday=0, aligns
        disc = disciplinas_map.get(e["disciplina_id"], {})
        for dt in _dates_in_month(ano, mes, wd):
            occurrences.append((dt, e, disc))
    occurrences.sort(key=lambda x: (x[0], x[1]["hora_inicio"]))

    for dt, e, disc in occurrences:
        iso = dt.isoformat()
        feriado = feriados.get(iso)
        remota = iso in aulas_remotas
        if feriado:
            modalidade = f"FERIADO — {feriado}"
        elif remota:
            modalidade = "Remota (EAD)"
        else:
            modalidade = "Presencial"
        rows.append([
            dt.strftime("%d/%m/%Y"),
            DIAS_SEMANA[e["dia_semana"]].replace("-feira", ""),
            Paragraph(disc.get("nome", "-"), ss["CellSm"]),
            f'{e["hora_inicio"]}–{e["hora_fim"]}',
            modalidade,
            "",
        ])

    if len(rows) == 1:
        rows.append(["—", "—", "Sem aulas cadastradas para o período", "—", "—", ""])

    t = Table(rows, colWidths=[24 * mm, 22 * mm, 52 * mm, 24 * mm, 30 * mm, 30 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), SLATE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, r in enumerate(rows[1:], start=1):
        mod = r[4]
        if isinstance(mod, str) and mod.startswith("FERIADO"):
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FDE8E8")))
        elif isinstance(mod, str) and mod.startswith("Remota"):
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#EAF2FB")))
        elif i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(style))
    els.append(t)

    els.append(Spacer(1, 24))
    total_aulas = len([o for o in occurrences if not feriados.get(o[0].isoformat())])
    els.append(Paragraph(f"<b>Total de aulas no período:</b> {total_aulas}", ss["Meta"]))
    els.append(Spacer(1, 30))

    sign = Table([
        ["_______________________________", "", "_______________________________"],
        ["Assinatura do Docente", "", "Coordenação de Curso"],
    ], colWidths=[75 * mm, 20 * mm, 75 * mm])
    sign.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), SLATE),
    ]))
    els.append(sign)

    doc.build(els, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#808080"))
    canvas.drawString(14 * mm, 8 * mm, "Gerado automaticamente pelo Sistema de Ponto Acadêmico — FATEC / Centro Paula Souza")
    canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_folha_curso(curso, professores_entries, ano, mes, feriados, aulas_remotas_por_prof, disciplinas_map):
    """One consolidated PDF: one section (table) per professor in the course."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = _styles()
    els = _header(ss, f"MAPA DE FREQUÊNCIA — {curso.get('nome','')} ({curso.get('sigla','')})")
    els.append(_meta_table(ss, [
        ("Curso", curso.get("nome", "")),
        ("Período", f"{MESES[mes]} / {ano}"),
        ("Turno", curso.get("turno", "").capitalize()),
        ("Docentes", str(len(professores_entries))),
    ]))
    els.append(Spacer(1, 10))

    for prof, entries_prof in professores_entries:
        band = Table([[Paragraph(f"Docente: {prof.get('nome','')}", ss["SectTitle"])]], colWidths=[182 * mm])
        band.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FATEC_RED),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        els.append(band)
        els.append(Spacer(1, 4))

        rows = [["Data", "Dia", "Disciplina", "Horário", "Modalidade"]]
        occ = []
        aulas_remotas = aulas_remotas_por_prof.get(prof["id"], set())
        for e in entries_prof:
            disc = disciplinas_map.get(e["disciplina_id"], {})
            for dt in _dates_in_month(ano, mes, e["dia_semana"]):
                occ.append((dt, e, disc))
        occ.sort(key=lambda x: (x[0], x[1]["hora_inicio"]))
        for dt, e, disc in occ:
            iso = dt.isoformat()
            fer = feriados.get(iso)
            mod = f"FERIADO — {fer}" if fer else ("Remota (EAD)" if iso in aulas_remotas else "Presencial")
            rows.append([dt.strftime("%d/%m"), DIAS_SEMANA[e["dia_semana"]].replace("-feira", ""),
                         Paragraph(disc.get("nome", "-"), ss["CellSm"]),
                         f'{e["hora_inicio"]}–{e["hora_fim"]}', mod])
        if len(rows) == 1:
            rows.append(["—", "—", "Sem aulas no período", "—", "—"])
        t = Table(rows, colWidths=[20 * mm, 22 * mm, 62 * mm, 26 * mm, 52 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        els.append(t)
        els.append(Spacer(1, 14))

    doc.build(els, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf
