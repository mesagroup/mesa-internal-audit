"""
Seed dati campione per il prototipo MESA ERM.
Eseguire con:  python db/seed_sample.py
Idempotente: svuota tutte le tabelle operative (eccetto controls)
e reinserisce un dataset coerente e completo.
"""
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import get_conn

conn = get_conn()
conn.execute("PRAGMA foreign_keys = OFF")

# ── Pulizia ───────────────────────────────────────────────────────────────────

TABLES_TO_CLEAR = [
    "action_plans", "findings", "verifications",
    "audit_plan_items", "audit_plans",
    "engagements",
    "risk_assessments",
    "risk_control", "procedure_risk", "process_procedure",
    "risks", "procedures", "processes",
    "owners",
    "audit_log",
]
for t in TABLES_TO_CLEAR:
    conn.execute(f"DELETE FROM {t}")
conn.execute("DELETE FROM sqlite_sequence WHERE name NOT IN ('controls')")
conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
print("Tabelle svuotate.")

# ══════════════════════════════════════════════════════════════════════════════
# OWNERS
# ══════════════════════════════════════════════════════════════════════════════

owners_data = [
    ("Mario Rossi",    "Process Owner",    "Acquisti & Procurement"),
    ("Anna Bianchi",   "Control Owner",    "Compliance & Legale"),
    ("Luca Ferrari",   "Process Owner",    "Finance & Controllo"),
    ("Sara Conti",     "IT Risk Manager",  "IT & Cybersecurity"),
    ("Giorgio Manca",  "Internal Auditor", "Internal Audit"),
]
owner_ids = {}
for name, role, area in owners_data:
    cur = conn.execute(
        "INSERT INTO owners (name, role, area) VALUES (?,?,?)",
        (name, role, area),
    )
    owner_ids[name] = cur.lastrowid

conn.commit()
print(f"Owner inseriti: {len(owner_ids)}")

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSI
# ══════════════════════════════════════════════════════════════════════════════

processes_data = [
    ("P01", "Procure-to-Pay",
     "Gestione del ciclo completo degli acquisti, dalla richiesta di acquisto "
     "fino al pagamento del fornitore.", "Mario Rossi"),
    ("P02", "Vendor Management",
     "Selezione, qualifica, contrattualizzazione e monitoraggio continuo "
     "dei fornitori strategici.", "Mario Rossi"),
    ("P03", "Finance & Reporting",
     "Gestione dei processi contabili, riconciliazione bancaria e "
     "produzione del reporting finanziario.", "Luca Ferrari"),
]
proc_ids = {}
for code, name, desc, owner in processes_data:
    cur = conn.execute(
        "INSERT INTO processes (code, name, description, owner) VALUES (?,?,?,?)",
        (code, name, desc, owner),
    )
    proc_ids[code] = cur.lastrowid

conn.commit()
print(f"Processi inseriti: {len(proc_ids)}")

# ══════════════════════════════════════════════════════════════════════════════
# PROCEDURE
# ══════════════════════════════════════════════════════════════════════════════

procedures_data = [
    ("PR01", "Gestione ordini di acquisto",
     "Emissione, approvazione e tracciamento degli ordini di acquisto (PO) "
     "nel sistema ERP. Include verifica soglie e doppia firma.",
     ["P01"]),
    ("PR02", "Selezione e qualifica fornitori",
     "Processo di onboarding dei nuovi fornitori: raccolta documentazione, "
     "due diligence, valutazione finanziaria e inserimento in vendor list.",
     ["P02"]),
    ("PR03", "Approvazione fatture e pagamenti",
     "Ricezione fatture, matching a tre vie (PO-DDT-fattura), workflow "
     "di approvazione e disposizione del pagamento.",
     ["P01", "P03"]),
    ("PR04", "Monitoraggio performance fornitori",
     "KPI periodici su qualità, puntualità e compliance contrattuale "
     "dei fornitori attivi. Include scorecard trimestrale.",
     ["P02"]),
    ("PR05", "Riconciliazione e reporting finanziario",
     "Chiusura mensile dei conti, riconciliazione bancaria, "
     "predisposizione del reporting per il management.",
     ["P03"]),
]
proced_ids = {}
for code, name, desc, linked_procs in procedures_data:
    cur = conn.execute(
        "INSERT INTO procedures (code, name, description) VALUES (?,?,?)",
        (code, name, desc),
    )
    pid = cur.lastrowid
    proced_ids[code] = pid
    for pcode in linked_procs:
        conn.execute(
            "INSERT INTO process_procedure (process_id, procedure_id) VALUES (?,?)",
            (proc_ids[pcode], pid),
        )

conn.commit()
print(f"Procedure inserite: {len(proced_ids)}")

# ══════════════════════════════════════════════════════════════════════════════
# RISCHI
# ══════════════════════════════════════════════════════════════════════════════

risks_data = [
    ("R01", "Emissione PO non autorizzata",
     "Ordini di acquisto emessi senza la necessaria doppia approvazione "
     "o al di sopra della soglia autorizzativa del firmatario.",
     "Operativo",
     ["PR01"], ["C01", "C04"]),   # C04 = supervisory review manuale

    ("R02", "Mancata segregation of duties",
     "Lo stesso soggetto svolge attivita' incompatibili: richiesta, "
     "approvazione PO e/o gestione del pagamento.",
     "Compliance",
     ["PR01", "PR03"], ["C01", "C04"]),  # C04 complementare

    ("R03", "Onboarding fornitori non qualificati",
     "Inserimento in vendor list di fornitori che non superano "
     "la due diligence finanziaria, legale o reputazionale.",
     "Operativo",
     ["PR02", "PR04"], ["C02", "C05"]),  # C05 = revisione periodica manuale

    ("R04", "Documentazione RFQ/PO non completa",
     "Richieste di offerta o ordini di acquisto privi di documentazione "
     "obbligatoria (offerte comparative, autorizzazioni, specifiche tecniche).",
     "Compliance",
     ["PR02"], ["C02"]),

    ("R05", "Pagamenti verso fornitori non approvati",
     "Disposizioni di pagamento a fornitori non presenti in vendor list "
     "approvata o con dati bancari non verificati.",
     "Frode",
     ["PR03"], ["C03", "C06"]),   # C06 = three-way match manuale

    ("R06", "Condizioni di pagamento non allineate al contratto",
     "Scadenze, sconti e condizioni di pagamento applicate "
     "in modo difforme rispetto ai termini contrattuali concordati.",
     "Finanziario",
     ["PR03", "PR04"], ["C02", "C03", "C06"]),  # C06 complementare
]
risk_ids = {}
for code, name, desc, cat, linked_proceds, linked_ctrls in risks_data:
    cur = conn.execute(
        "INSERT INTO risks (code, name, description, category) VALUES (?,?,?,?)",
        (code, name, desc, cat),
    )
    rid = cur.lastrowid
    risk_ids[code] = rid
    for prcode in linked_proceds:
        conn.execute(
            "INSERT INTO procedure_risk (procedure_id, risk_id) VALUES (?,?)",
            (proced_ids[prcode], rid),
        )
    for ctrl_id in linked_ctrls:
        conn.execute(
            "INSERT INTO risk_control (risk_id, control_id) VALUES (?,?)",
            (rid, ctrl_id),
        )

conn.commit()
print(f"Rischi inseriti: {len(risk_ids)}")

# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLI MANUALI (C04, C05, C06) — inseriti dopo i rischi perché
# risk_control li referenzia tramite id testuale, non FK integer
# ══════════════════════════════════════════════════════════════════════════════

manual_controls = [
    {
        "id": "C04",
        "title": "Supervisory Review — Approvazioni PO",
        "area": "Procure-to-Pay",
        "description": (
            "Revisione periodica (mensile) da parte del Responsabile Acquisti "
            "del log delle approvazioni PO. Verifica che tutte le PO siano state "
            "approvate nel rispetto della Delegation of Authority vigente e che "
            "nessun singolo utente abbia esercitato ruoli incompatibili "
            "(SoD check manuale)."
        ),
        "check_points": [
            "Il log mensile delle approvazioni PO e' stato esaminato dal Responsabile Acquisti",
            "Nessuna PO e' stata approvata da un unico firmatario oltre soglia",
            "Non si rilevano utenti con ruoli incompatibili (creatore e approvatore PO coincidenti)",
            "Le eccezioni riscontrate sono state documentate e escalate al CFO",
        ],
        "expected_documents": [
            "Report mensile approvazioni PO (export ERP)",
            "Matrice Delegation of Authority vigente",
            "Eventuali note di eccezione documentate e firmate",
        ],
        "ctrl_type": "manual",
    },
    {
        "id": "C05",
        "title": "Vendor List Review — Revisione Periodica Trimestrale",
        "area": "Vendor Management",
        "description": (
            "Revisione trimestrale della vendor list approvata da parte del "
            "Procurement Manager. Verifica l'aggiornamento delle qualifiche, "
            "la completezza documentale per ogni fornitore attivo e l'assenza "
            "di soggetti sospesi, blacklisted o con rating finanziario scaduto."
        ),
        "check_points": [
            "La vendor list e' stata revisionata nell'ultimo trimestre",
            "Tutti i fornitori attivi hanno la due diligence finanziaria aggiornata (< 12 mesi)",
            "Nessun fornitore attivo risulta su liste di esclusione o blacklist settoriali",
            "I fornitori con documentazione scaduta sono stati sospesi o aggiornati",
        ],
        "expected_documents": [
            "Vendor list aggiornata con data di ultima qualifica",
            "Report due diligence finanziaria per fornitore",
            "Evidenza di controllo su blacklist/sanction list",
            "Verbale revisione trimestrale firmato dal Procurement Manager",
        ],
        "ctrl_type": "manual",
    },
    {
        "id": "C06",
        "title": "Three-Way Match Manuale — Forniture ad Alto Valore",
        "area": "Accounts Payable",
        "description": (
            "Per tutte le forniture con importo fattura superiore a EUR 50.000, "
            "verifica manuale della corrispondenza a tre vie tra: ordine di acquisto "
            "(PO), documento di trasporto o bolla di consegna (DDT) e fattura "
            "del fornitore. L'esito viene documentato su apposita checklist firmata."
        ),
        "check_points": [
            "Il three-way match e' stato eseguito per tutte le fatture > EUR 50.000",
            "Gli importi su PO, DDT e fattura corrispondono (tolleranza: 0,5%)",
            "I beni/servizi fatturati corrispondono a quelli effettivamente ricevuti",
            "Le condizioni di pagamento applicate sono coerenti con il contratto/PO",
            "La checklist di three-way match e' firmata dal responsabile AP",
        ],
        "expected_documents": [
            "Purchase Order (PO) originale",
            "Documento di trasporto / bolla di consegna (DDT)",
            "Fattura fornitore",
            "Checklist three-way match compilata e firmata",
        ],
        "ctrl_type": "manual",
    },
]

for mc in manual_controls:
    conn.execute(
        """INSERT OR REPLACE INTO controls
               (id, title, area, description, check_points, expected_documents, ctrl_type)
           VALUES (?,?,?,?,?,?,?)""",
        (
            mc["id"], mc["title"], mc["area"], mc["description"],
            json.dumps(mc["check_points"], ensure_ascii=False),
            json.dumps(mc["expected_documents"], ensure_ascii=False),
            mc["ctrl_type"],
        ),
    )

conn.commit()
print(f"Controlli manuali inseriti: {len(manual_controls)} (C04, C05, C06)")

# ══════════════════════════════════════════════════════════════════════════════
# RISK ASSESSMENT 2026
# ══════════════════════════════════════════════════════════════════════════════

ra_data = [
    # (risk_code, likelihood, impact, notes)
    ("R01", 4, 5, "Rischio critico: rilevato 1 caso di PO over-threshold Q1 2026"),
    ("R02", 3, 4, "SoD parzialmente coperta; alcune aree IT ancora escluse"),
    ("R03", 3, 3, "Due diligence non completata per 2 nuovi fornitori"),
    ("R04", 2, 4, "Documentazione mancante su ~15% delle RFQ analizzate"),
    ("R05", 2, 5, "Impatto potenziale molto elevato — presidi in revisione"),
    ("R06", 3, 3, "Sconto 2/10 non applicato in 3 casi su top-5 supplier"),
]
for rcode, l, i, notes in ra_data:
    conn.execute(
        """INSERT INTO risk_assessments
               (risk_id, year, likelihood, impact, notes, scored_by, scored_at)
           VALUES (?, 2026, ?, ?, ?, 'head_ia', datetime('now'))""",
        (risk_ids[rcode], l, i, notes),
    )

conn.commit()
print(f"Risk assessment 2026 inseriti: {len(ra_data)}")

# ══════════════════════════════════════════════════════════════════════════════
# PIANO DI AUDIT 2026
# ══════════════════════════════════════════════════════════════════════════════

# Piano costruito a partire dal Processo P01 (Procure-to-Pay).
# Catena: P01 -> PR01/PR03 -> R01/R02/R05/R06 -> C01, C02, C03, C04, C06
# (tutti i controlli associati al processo, AI + manuali)
plan_id = conn.execute(
    "INSERT INTO audit_plans (name, year, notes, status) VALUES (?,?,?,?)",
    (
        "Audit Procure-to-Pay 2026",
        2026,
        "Piano generato dalla catena Processo P01 (Procure-to-Pay). "
        "Include tutti i controlli AI e manuali associati al processo "
        "attraverso la catena Procedura -> Rischio -> Controllo. "
        "Priorita' su C01 e C04 per score di rischio elevato (R01=20, R02=12).",
        "active",
    ),
).lastrowid

# Controlli di P01: C01 (AI), C02 (AI), C03 (AI), C04 (manuale), C06 (manuale)
plan_items = [
    ("C01", "2026-06-30", "Giorgio Manca",  "in_progress"),
    ("C02", "2026-07-31", "Giorgio Manca",  "planned"),
    ("C03", "2026-09-30", "Giorgio Manca",  "planned"),
    ("C04", "2026-06-15", "Anna Bianchi",   "in_progress"),  # manuale, priorita' alta
    ("C06", "2026-10-31", "Anna Bianchi",   "planned"),      # manuale
]
plan_item_ids = []
for ctrl_id, planned_date, assigned, status in plan_items:
    iid = conn.execute(
        """INSERT INTO audit_plan_items
               (plan_id, control_id, planned_date, assigned_to, status)
           VALUES (?,?,?,?,?)""",
        (plan_id, ctrl_id, planned_date, assigned, status),
    ).lastrowid
    plan_item_ids.append(iid)

conn.commit()
print(f"Piano 'Audit P2P 2026' creato (ID #{plan_id}), {len(plan_items)} controlli da P01")

# ══════════════════════════════════════════════════════════════════════════════
# ENGAGEMENTS
# ══════════════════════════════════════════════════════════════════════════════

engagements_data = [
    ("Audit P2P — Autorizzazioni PO (C01)",
     "Verifica del controllo C01: matrice SoD e log approvazioni PO Q1-Q2 2026",
     "active"),
    ("Audit Vendor Management — Qualifica Fornitori (C02)",
     "Verifica documentazione RFQ/PO e processo di onboarding fornitori 2026",
     "active"),
]
eng_ids = []
for name, desc, status in engagements_data:
    eid = conn.execute(
        "INSERT INTO engagements (name, description, status) VALUES (?,?,?)",
        (name, desc, status),
    ).lastrowid
    eng_ids.append(eid)

# Collega il primo engagement al piano (item C01)
conn.execute(
    "UPDATE audit_plan_items SET engagement_id=?, status='in_progress' WHERE id=?",
    (eng_ids[0], plan_item_ids[0]),
)
conn.commit()
print(f"Engagement inseriti: {len(eng_ids)}")

# ══════════════════════════════════════════════════════════════════════════════
# VERIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

def ver(engagement_id, control_id, overall_status, summary, checkpoints, mitigation):
    return conn.execute(
        """INSERT INTO verifications
               (engagement_id, control_id, overall_status, summary,
                check_points, mitigation_plan, raw_model_output)
           VALUES (?,?,?,?,?,?,'[AI seed]')""",
        (engagement_id, control_id, overall_status, summary,
         json.dumps(checkpoints, ensure_ascii=False),
         json.dumps(mitigation, ensure_ascii=False)),
    ).lastrowid

# Verification C01 — non conforme
v1_id = ver(
    eng_ids[0], "C01", "non_conforme",
    "L'analisi ha evidenziato che la matrice SoD non è aggiornata: 3 utenti "
    "dispongono di accessi incompatibili (creazione+approvazione PO). "
    "Il log delle approvazioni mostra 4 PO approvate da un unico firmatario "
    "oltre soglia nel periodo Q1 2026.",
    [
        {"check_point": "Verifica aggiornamento matrice SoD",
         "status": "non_conforme",
         "evidence": "Matrice SoD versione 2024 — non aggiornata",
         "issue": "3 utenti con profili incompatibili attivi",
         "mitigation": "Aggiornare matrice SoD entro 30 gg e revocare accessi"},
        {"check_point": "Revisione log approvazioni PO",
         "status": "non_conforme",
         "evidence": "Export log ERP periodo 01/01-31/03/2026",
         "issue": "4 PO over-threshold approvate da singolo firmatario",
         "mitigation": "Implementare blocco automatico su PO > soglia senza seconda firma"},
        {"check_point": "Verifica workflow di escalation per PO urgenti",
         "status": "parziale",
         "evidence": "Policy PR-ACQ-001 rev.3",
         "issue": "Procedura di urgenza non formalmente documentata",
         "mitigation": "Integrare policy con procedura urgenze e formare il personale"},
    ],
    [
        "Aggiornare la matrice SoD e revocare gli accessi incompatibili entro 30 giorni",
        "Configurare blocco automatico nel sistema ERP per PO oltre soglia senza doppia firma",
        "Documentare e approvare la procedura di escalation per acquisti urgenti",
    ],
)

# Verification C02 — parziale
v2_id = ver(
    eng_ids[1], "C02", "parziale",
    "La documentazione RFQ risulta presente per l'85% dei casi esaminati. "
    "Tuttavia, 2 fornitori inseriti in vendor list nel 2025 non hanno completato "
    "la due diligence finanziaria. La coerenza tra RFQ e PO è complessivamente soddisfatta.",
    [
        {"check_point": "Completezza documentazione RFQ",
         "status": "parziale",
         "evidence": "Campione 20 RFQ periodo 2025-2026",
         "issue": "3 RFQ prive di almeno 2 offerte comparative",
         "mitigation": "Rendere obbligatorio il caricamento di min. 3 offerte nel portale"},
        {"check_point": "Due diligence finanziaria fornitori",
         "status": "non_conforme",
         "evidence": "Vendor list aggiornata al 01/01/2026",
         "issue": "2 fornitori senza rating finanziario aggiornato",
         "mitigation": "Completare due diligence entro 60 gg e bloccare ordini nel frattempo"},
        {"check_point": "Coerenza RFQ-PO (quantità, prezzi, condizioni)",
         "status": "conforme",
         "evidence": "Riconciliazione automatica ERP — scostamenti < 1%",
         "issue": "",
         "mitigation": ""},
    ],
    [
        "Rendere obbligatorio il caricamento minimo di 3 offerte nel portale acquisti",
        "Completare la due diligence finanziaria dei 2 fornitori non conformi entro 60 giorni",
    ],
)

conn.commit()
print(f"Verifications inserite: 2 (v1=#{v1_id}, v2=#{v2_id})")

# ══════════════════════════════════════════════════════════════════════════════
# FINDINGS
# ══════════════════════════════════════════════════════════════════════════════

f1_id = conn.execute(
    """INSERT INTO findings
           (verification_id, control_id, engagement_id,
            title, description, severity, status)
       VALUES (?,?,?,?,?,?,?)""",
    (v1_id, "C01", eng_ids[0],
     "[C01] Non conformità — Segregation of Duties e approvazioni PO",
     "Matrice SoD non aggiornata con 3 utenti con accessi incompatibili. "
     "4 PO over-threshold approvate da singolo firmatario nel Q1 2026.",
     "alto", "open"),
).lastrowid

f2_id = conn.execute(
    """INSERT INTO findings
           (verification_id, control_id, engagement_id,
            title, description, severity, status)
       VALUES (?,?,?,?,?,?,?)""",
    (v2_id, "C02", eng_ids[1],
     "[C02] Parziale — Due diligence fornitori incompleta",
     "2 fornitori inseriti in vendor list senza completamento della due "
     "diligence finanziaria. 3 RFQ prive di offerte comparative sufficienti.",
     "medio", "open"),
).lastrowid

conn.commit()
print(f"Finding inseriti: 2 (f1=#{f1_id}, f2=#{f2_id})")

# ══════════════════════════════════════════════════════════════════════════════
# ACTION PLANS
# ══════════════════════════════════════════════════════════════════════════════

aps = [
    # Finding 1 — alto
    (f1_id, "Aggiornare matrice SoD e revocare profili incompatibili",
     "Anna Bianchi", "2026-06-30", "in_progress"),
    (f1_id, "Configurare blocco automatico ERP per PO over-threshold senza doppia firma",
     "Sara Conti", "2026-07-31", "open"),
    (f1_id, "Formare il personale acquisti sulla nuova procedura di approvazione",
     "Mario Rossi", "2026-08-15", "open"),
    # Finding 2 — medio
    (f2_id, "Completare due diligence finanziaria per i 2 fornitori non conformi",
     "Mario Rossi", "2026-07-15", "in_progress"),
    (f2_id, "Rendere obbligatorio upload min. 3 offerte nel portale acquisti",
     "Sara Conti", "2026-09-30", "open"),
]
for finding_id, desc, owner, due, status in aps:
    conn.execute(
        """INSERT INTO action_plans (finding_id, description, owner_name, due_date, status)
           VALUES (?,?,?,?,?)""",
        (finding_id, desc, owner, due, status),
    )

conn.commit()
print(f"Action plan inseriti: {len(aps)}")

# ══════════════════════════════════════════════════════════════════════════════
# RIEPILOGO FINALE
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*60)
print("  SEED COMPLETATO — riepilogo DB")
print("="*60)
for t in ["owners","processes","procedures","risks","process_procedure",
          "procedure_risk","risk_control","risk_assessments",
          "audit_plans","audit_plan_items","engagements",
          "verifications","findings","action_plans"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:<25} {n:>4} righe")

conn.close()
