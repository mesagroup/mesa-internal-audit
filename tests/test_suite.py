"""
Test suite completo per il prototipo Internal Audit.
Eseguire da: python -m pytest tests/test_suite.py -v
oppure:      python tests/test_suite.py
"""
import json
import sys
import os
import traceback
from pathlib import Path
from datetime import date

# Assicura che il progetto sia nel path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

PASS  = "✅ PASS"
FAIL  = "❌ FAIL"
WARN  = "⚠️  WARN"

results: list[tuple[str, str, str]] = []  # (area, test, status+note)


def check(area: str, name: str, fn):
    try:
        note = fn()
        results.append((area, name, f"{PASS}  {note or ''}"))
    except AssertionError as e:
        results.append((area, name, f"{FAIL}  AssertionError: {e}"))
    except Exception as e:
        results.append((area, name, f"{FAIL}  {type(e).__name__}: {e}"))


# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORT — tutte le pagine devono importarsi senza errori
# ══════════════════════════════════════════════════════════════════════════════

def _import_check(module_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_mod", ROOT / module_path)
    mod  = importlib.util.module_from_spec(spec)
    # Non eseguiamo il corpo Streamlit (richiederebbe runtime);
    # verifichiamo solo che il file si compili senza errori di sintassi.
    import py_compile
    py_compile.compile(str(ROOT / module_path), doraise=True)
    return "compile OK"

for page in [
    "app.py",
    "auth/utils.py",
    "db/__init__.py",
    "db/init_db.py",
    "db/repositories.py",
    "ui/common.py",
    "pages/1_Anagrafica.py",
    "pages/2_Risk.py",
    "pages/3_Piano.py",
    "pages/4_Engagement.py",
    "pages/5_Findings.py",
    "pages/6_Reporting.py",
    "core/controls_tree.py",
    "core/llm_verifier.py",
    "core/document_loader.py",
    "core/report_generator.py",
]:
    check("IMPORT", page, lambda p=page: _import_check(p))


# ══════════════════════════════════════════════════════════════════════════════
# 2. DATABASE — schema e init
# ══════════════════════════════════════════════════════════════════════════════

import sqlite3
import tempfile

def _make_test_db():
    """Crea un DB temporaneo isolato per i test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    schema = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn, Path(tmp.name)

def test_schema_tables():
    conn, p = _make_test_db()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    expected = {"controls","owners","engagements","verifications",
                "findings","action_plans","audit_log",
                "audit_plans","audit_plan_items","risk_scores"}
    missing = expected - tables
    conn.close(); p.unlink()
    assert not missing, f"Tabelle mancanti: {missing}"
    return f"{len(tables)} tabelle OK"

check("DATABASE", "schema — tutte le tabelle presenti", test_schema_tables)

def test_seed_controls():
    conn, p = _make_test_db()
    from core.controls_tree import CONTROLS_TREE
    for c in CONTROLS_TREE:
        conn.execute(
            "INSERT INTO controls (id,title,area,description,check_points,expected_documents)"
            " VALUES (?,?,?,?,?,?)",
            (c.id, c.title, c.area, c.description,
             json.dumps(c.check_points), json.dumps(c.expected_documents))
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
    conn.close(); p.unlink()
    assert count == len(CONTROLS_TREE), f"attesi {len(CONTROLS_TREE)}, trovati {count}"
    return f"{count} controlli seedati"

check("DATABASE", "seed controlli default", test_seed_controls)

def test_risk_scores_unique():
    """UNIQUE(control_id, year) con ON CONFLICT REPLACE."""
    conn, p = _make_test_db()
    conn.execute("INSERT INTO risk_scores (control_id,year,likelihood,impact) VALUES ('C01',2026,3,3)")
    conn.execute("INSERT INTO risk_scores (control_id,year,likelihood,impact) VALUES ('C01',2026,5,5)")
    conn.commit()
    rows = conn.execute("SELECT * FROM risk_scores WHERE control_id='C01' AND year=2026").fetchall()
    conn.close(); p.unlink()
    assert len(rows) == 1, f"attesa 1 riga, trovate {len(rows)}"
    assert rows[0]["likelihood"] == 5, "upsert non ha sovrascritto"
    return "ON CONFLICT REPLACE funziona"

check("DATABASE", "risk_scores UNIQUE ON CONFLICT REPLACE", test_risk_scores_unique)

def test_audit_log_append():
    conn, p = _make_test_db()
    for i in range(5):
        conn.execute(
            "INSERT INTO audit_log (user_name,action,entity_type,entity_id) VALUES (?,?,?,?)",
            ("test_user", "create", "control", str(i))
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    conn.close(); p.unlink()
    assert count == 5
    return "5 righe inserite"

check("DATABASE", "audit_log append", test_audit_log_append)


# ══════════════════════════════════════════════════════════════════════════════
# 3. REPOSITORIES — CRUD su DB reale
# ══════════════════════════════════════════════════════════════════════════════

# Usiamo il DB reale ma con dati puliti dove possibile
from db.repositories import (
    get_all_controls, get_control, upsert_control, delete_control,
    reset_controls_to_defaults,
    get_all_owners, upsert_owner, delete_owner,
    get_active_engagements, create_engagement, close_engagement, get_engagement,
    save_verification, get_verifications_for_engagement,
    create_finding, get_all_findings, update_finding_status,
    create_action_plan, get_action_plans_for_finding, update_action_plan_status,
    get_all_action_plans,
    create_plan, get_all_plans, add_plan_item, get_plan_items,
    get_plan_completion, update_plan_item_status,
    upsert_risk_score, get_risk_scores, get_risk_ranking,
    get_dashboard_counts, get_audit_log, get_audit_log_count,
    get_findings_by_severity, get_findings_by_status, get_action_plans_by_status,
)
from core.controls_tree import Control

def test_repo_controls():
    controls = get_all_controls()
    assert len(controls) >= 3, f"attesi >= 3 controlli, trovati {len(controls)}"
    c = get_control("C01")
    assert c is not None, "C01 non trovato"
    assert c.id == "C01"
    assert len(c.check_points) > 0, "C01 senza check points"
    assert len(c.expected_documents) > 0, "C01 senza documenti attesi"
    return f"{len(controls)} controlli, C01 OK"

check("REPOSITORY", "get_all_controls / get_control", test_repo_controls)

def test_repo_upsert_delete_control():
    test_ctrl = Control(
        id="C99", title="Test Control", area="Test Area",
        description="Desc", check_points=["CP1","CP2"],
        expected_documents=["Doc1"]
    )
    upsert_control(test_ctrl, user="test")
    c = get_control("C99")
    assert c is not None and c.title == "Test Control"
    # update
    test_ctrl.title = "Test Control Updated"
    upsert_control(test_ctrl, user="test")
    c2 = get_control("C99")
    assert c2.title == "Test Control Updated"
    delete_control("C99", user="test")
    assert get_control("C99") is None
    return "upsert e delete OK"

check("REPOSITORY", "upsert_control / delete_control", test_repo_upsert_delete_control)

def test_repo_check_points_roundtrip():
    """Verifica che i check_points sopravvivano al round-trip JSON nel DB."""
    cps = ["Check point con virgole, e accenti àèì", "CP con «guillemets»", "CP3"]
    ctrl = Control(id="C98", title="Round-trip", area="Test",
                   description="", check_points=cps, expected_documents=[])
    upsert_control(ctrl, user="test")
    c = get_control("C98")
    delete_control("C98", user="test")
    assert c.check_points == cps, f"Round-trip fallito: {c.check_points}"
    return "JSON round-trip OK"

check("REPOSITORY", "check_points JSON round-trip", test_repo_check_points_roundtrip)

def test_repo_owners():
    oid = upsert_owner(None, "Test Owner", "Process Owner", "P2P", user="test")
    assert isinstance(oid, int) and oid > 0
    owners = get_all_owners()
    assert any(o["id"] == oid for o in owners)
    delete_owner(oid, user="test")
    assert not any(o["id"] == oid for o in get_all_owners())
    return "owner CRUD OK"

check("REPOSITORY", "owner CRUD", test_repo_owners)

def test_repo_engagement_lifecycle():
    eid = create_engagement("Test Eng", "Test desc", user="test")
    assert isinstance(eid, int) and eid > 0
    eng = get_engagement(eid)
    assert eng["status"] == "active"
    active = get_active_engagements()
    assert any(e["id"] == eid for e in active)
    close_engagement(eid, user="test")
    eng2 = get_engagement(eid)
    assert eng2["status"] == "closed"
    return f"engagement #{eid} aperto e chiuso"

check("REPOSITORY", "engagement lifecycle (create/close)", test_repo_engagement_lifecycle)

def test_repo_verification_save():
    from core.llm_verifier import VerificationResult, CheckPointResult
    eid = create_engagement("Eng for verification test", user="test")
    result = VerificationResult(
        control_id="C01", control_title="Test",
        overall_status="non_conforme", summary="Test summary",
        check_points=[
            CheckPointResult("CP1", "non_conforme", "evidence", "issue", "mitigation"),
            CheckPointResult("CP2", "conforme", "evidence2", "", ""),
        ],
        mitigation_plan=["Azione 1", "Azione 2"],
    )
    vid = save_verification(eid, "C01", result, user="test")
    assert isinstance(vid, int) and vid > 0
    vers = get_verifications_for_engagement(eid)
    assert len(vers) == 1
    v = vers[0]
    assert v["overall_status"] == "non_conforme"
    assert len(v["check_points"]) == 2
    assert v["check_points"][0]["status"] == "non_conforme"
    assert v["mitigation_plan"] == ["Azione 1", "Azione 2"]
    return f"verification #{vid} salvata, check_points e mitigation OK"

check("REPOSITORY", "save_verification + get_verifications", test_repo_verification_save)

def test_repo_finding_lifecycle():
    eid = create_engagement("Eng for finding test", user="test")
    fid = create_finding(None, "C01", eid, "Test Finding",
                         "Descrizione finding", "alto", user="test")
    assert isinstance(fid, int)
    findings = get_all_findings()
    f = next((x for x in findings if x["id"] == fid), None)
    assert f is not None
    assert f["severity"] == "alto"
    assert f["status"] == "open"
    update_finding_status(fid, "validated", user="test")
    findings2 = get_all_findings()
    f2 = next(x for x in findings2 if x["id"] == fid)
    assert f2["status"] == "validated"
    return f"finding #{fid}: create→validated OK"

check("REPOSITORY", "finding lifecycle (create/update_status)", test_repo_finding_lifecycle)

def test_repo_action_plan():
    eid = create_engagement("Eng for AP test", user="test")
    fid = create_finding(None, "C02", eid, "AP Finding", "desc", "medio", user="test")
    ap_id = create_action_plan(fid, "Correggere processo", "Mario Rossi",
                               "2026-12-31", user="test")
    assert isinstance(ap_id, int)
    aps = get_action_plans_for_finding(fid)
    assert len(aps) == 1
    assert aps[0]["owner_name"] == "Mario Rossi"
    assert aps[0]["due_date"] == "2026-12-31"
    assert aps[0]["status"] == "open"
    update_action_plan_status(ap_id, "in_progress", user="test")
    aps2 = get_action_plans_for_finding(fid)
    assert aps2[0]["status"] == "in_progress"
    return f"action plan #{ap_id}: create→in_progress OK"

check("REPOSITORY", "action_plan lifecycle", test_repo_action_plan)

def test_repo_overdue_count():
    """get_dashboard_counts conta correttamente gli AP scaduti."""
    eid = create_engagement("Eng overdue", user="test")
    fid = create_finding(None, "C01", eid, "Overdue finding", "d", "basso", user="test")
    create_action_plan(fid, "AP scaduto", "Owner", "2020-01-01", user="test")  # passato
    create_action_plan(fid, "AP futuro", "Owner", "2099-12-31", user="test")   # futuro
    counts = get_dashboard_counts()
    assert counts["overdue_action_plans"] >= 1, \
        f"overdue non rilevato: {counts}"
    return f"overdue={counts['overdue_action_plans']}, open_findings={counts['open_findings']}"

check("REPOSITORY", "dashboard_counts overdue AP", test_repo_overdue_count)

def test_repo_audit_plan():
    pid = create_plan("Piano Test 9999", 9999, "note test", user="test")
    assert isinstance(pid, int)
    iid = add_plan_item(pid, "C01", "2026-06-30", "Tester", user="test")
    assert isinstance(iid, int)
    items = get_plan_items(pid)
    assert len(items) == 1
    assert items[0]["control_id"] == "C01"
    comp = get_plan_completion(pid)
    assert comp["total"] == 1
    assert comp["completed"] == 0
    update_plan_item_status(iid, "completed", user="test")
    comp2 = get_plan_completion(pid)
    assert comp2["completed"] == 1
    return f"piano #{pid}: item planned→completed OK"

check("REPOSITORY", "audit_plan + items lifecycle", test_repo_audit_plan)

def test_repo_risk_scores():
    upsert_risk_score("C01", 9999, 4, 5, "Test note", user="test")
    upsert_risk_score("C02", 9999, 2, 3, "", user="test")
    upsert_risk_score("C01", 9999, 5, 5, "Updated", user="test")  # upsert
    scores = get_risk_scores(9999)
    c01 = next(s for s in scores if s["control_id"] == "C01")
    assert c01["likelihood"] == 5, "upsert non ha aggiornato"
    ranking = get_risk_ranking(9999)
    assert ranking[0]["control_id"] == "C01"  # score 25 > 6
    assert ranking[0]["score"] == 25
    return f"risk scores OK, top={ranking[0]['control_id']} score={ranking[0]['score']}"

check("REPOSITORY", "risk_scores upsert + ranking", test_repo_risk_scores)

def test_repo_audit_log_readable():
    entries = get_audit_log(limit=50)
    count = get_audit_log_count()
    assert count >= len(entries)
    if entries:
        assert "ts" in entries[0]
        assert "action" in entries[0]
        assert "entity_type" in entries[0]
    return f"{count} righe nel log, lettura OK"

check("REPOSITORY", "audit_log read", test_repo_audit_log_readable)

def test_repo_reporting_queries():
    sev  = get_findings_by_severity()
    stat = get_findings_by_status()
    ap   = get_action_plans_by_status()
    # non crashano e restituiscono liste
    assert isinstance(sev, list)
    assert isinstance(stat, list)
    assert isinstance(ap, list)
    return f"sev={len(sev)} gruppi, stat={len(stat)} gruppi, ap={len(ap)} gruppi"

check("REPOSITORY", "reporting queries (findings/AP by status)", test_repo_reporting_queries)


# ══════════════════════════════════════════════════════════════════════════════
# 4. AUTH — credenziali e logica di ruolo
# ══════════════════════════════════════════════════════════════════════════════

def test_auth_credentials_file():
    import yaml
    creds_path = ROOT / "auth/credentials.yaml"
    assert creds_path.exists(), "credentials.yaml non trovato"
    with open(creds_path) as f:
        config = yaml.safe_load(f)
    users = config["credentials"]["usernames"]
    assert "auditor1" in users
    assert "head_ia" in users
    assert "auditee1" in users
    for u, d in users.items():
        assert "role" in d, f"utente {u} senza campo 'role'"
        assert "name" in d, f"utente {u} senza campo 'name'"
        assert d["password"].startswith("$2b$"), f"utente {u}: password non hashata"
    cookie = config.get("cookie", {})
    assert "key" in cookie and "name" in cookie
    return f"{len(users)} utenti, bcrypt OK"

check("AUTH", "credentials.yaml valido", test_auth_credentials_file)

def test_auth_bcrypt_verify():
    import bcrypt, yaml
    with open(ROOT / "auth/credentials.yaml") as f:
        config = yaml.safe_load(f)
    users = config["credentials"]["usernames"]
    plain_passwords = {
        "auditor1": "audit123",
        "head_ia":  "head123",
        "auditee1": "aud123",
    }
    for username, plain in plain_passwords.items():
        hashed = users[username]["password"].encode()
        ok = bcrypt.checkpw(plain.encode(), hashed)
        assert ok, f"password errata per {username}"
    return "tutte le password verificate con bcrypt"

check("AUTH", "bcrypt password verify", test_auth_bcrypt_verify)

def test_auth_roles():
    from auth.utils import ROLE_LABELS, ROLE_INITIALS
    for role in ("auditor", "head_ia", "auditee"):
        assert role in ROLE_LABELS, f"ROLE_LABELS manca '{role}'"
        assert role in ROLE_INITIALS, f"ROLE_INITIALS manca '{role}'"
    return "ROLE_LABELS e ROLE_INITIALS completi"

check("AUTH", "ROLE_LABELS / ROLE_INITIALS completi", test_auth_roles)

def test_auth_get_authenticator():
    from auth.utils import get_authenticator
    auth, config = get_authenticator()
    assert auth is not None
    assert "credentials" in config
    return "get_authenticator() OK"

check("AUTH", "get_authenticator() instanziabile", test_auth_get_authenticator)


# ══════════════════════════════════════════════════════════════════════════════
# 5. CORE — document_loader e report_generator
# ══════════════════════════════════════════════════════════════════════════════

def test_core_controls_tree():
    from core.controls_tree import CONTROLS_TREE, get_control as gc
    assert len(CONTROLS_TREE) == 3
    for c in CONTROLS_TREE:
        assert c.id and c.title and c.area
        assert len(c.check_points) > 0
        assert len(c.expected_documents) > 0
    c01 = gc("C01")
    assert c01.id == "C01"
    return f"{len(CONTROLS_TREE)} controlli, get_control OK"

check("CORE", "controls_tree (CONTROLS_TREE + get_control)", test_core_controls_tree)

def test_core_document_loader_txt():
    import tempfile
    from core.document_loader import load_document
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     encoding="utf-8", delete=False)
    tmp.write("Contenuto di test con accenti àèì\nSeconda riga.")
    tmp.close()
    text = load_document(tmp.name)
    Path(tmp.name).unlink()
    assert "Contenuto di test" in text
    assert "accenti" in text
    return "loader TXT OK"

check("CORE", "document_loader — TXT", test_core_document_loader_txt)

def test_core_document_loader_xlsx():
    import tempfile, openpyxl
    from core.document_loader import load_document
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test"
    ws["A1"] = "Vendor"
    ws["B1"] = "Amount"
    ws["A2"] = "Fornitore ABC"
    ws["B2"] = 12345.67
    wb.save(tmp.name)
    text = load_document(tmp.name)
    Path(tmp.name).unlink()
    assert "Fornitore ABC" in text
    assert "Test" in text  # sheet name
    return "loader XLSX OK"

check("CORE", "document_loader — XLSX", test_core_document_loader_xlsx)

def test_core_document_loader_missing():
    from core.document_loader import load_document
    try:
        load_document("/nonexistent/file.txt")
        assert False, "doveva sollevare FileNotFoundError"
    except FileNotFoundError:
        return "FileNotFoundError correttamente sollevato"

check("CORE", "document_loader — file mancante", test_core_document_loader_missing)

def test_core_pdf_report():
    import tempfile
    from core.llm_verifier import VerificationResult, CheckPointResult
    from core.report_generator import generate_pdf_report
    results_data = [
        VerificationResult(
            control_id="C01", control_title="Test Control",
            overall_status="non_conforme", summary="Test summary",
            check_points=[
                CheckPointResult("CP1","non_conforme","evid","issue","mit"),
                CheckPointResult("CP2","conforme","evid2","",""),
            ],
            mitigation_plan=["Azione 1"],
        )
    ]
    out = Path(tempfile.mktemp(suffix=".pdf"))
    generate_pdf_report(results_data, out)
    size = out.stat().st_size
    out.unlink()
    assert size > 1000, f"PDF troppo piccolo: {size} bytes"
    return f"PDF generato {size} bytes"

check("CORE", "generate_pdf_report", test_core_pdf_report)

def test_core_engagement_pdf():
    import tempfile
    from core.report_generator import generate_engagement_pdf
    engagement = {"name": "Test Eng", "created_at": "2026-05-01"}
    verifications = [{
        "control_id": "C01", "overall_status": "non_conforme",
        "verified_at": "2026-05-01",
        "check_points": [{"status":"non_conforme","check_point":"CP","evidence":"e","issue":"i","mitigation":"m"}],
        "summary": "Summary",
    }]
    findings = [{"id":1,"title":"Finding 1","severity":"alto","status":"open",
                 "control_id":"C01","detected_at":"2026-05-01","description":"desc"}]
    action_plans = [{"finding_id":1,"description":"Azione","owner_name":"Owner",
                     "due_date":"2026-12-31","status":"open"}]
    out = Path(tempfile.mktemp(suffix=".pdf"))
    generate_engagement_pdf(engagement, verifications, findings, action_plans, out)
    size = out.stat().st_size
    out.unlink()
    assert size > 1000, f"PDF troppo piccolo: {size} bytes"
    return f"engagement PDF generato {size} bytes"

check("CORE", "generate_engagement_pdf", test_core_engagement_pdf)

def test_core_excel_report():
    import tempfile
    from core.llm_verifier import VerificationResult, CheckPointResult
    from core.report_generator import generate_excel_report
    results_data = [
        VerificationResult(
            control_id="C02", control_title="Test C02",
            overall_status="parziale", summary="Test",
            check_points=[CheckPointResult("CP","parziale","e","","")],
            mitigation_plan=[],
        )
    ]
    out = Path(tempfile.mktemp(suffix=".xlsx"))
    generate_excel_report(results_data, out)
    size = out.stat().st_size
    out.unlink()
    assert size > 3000, f"Excel troppo piccolo: {size} bytes"
    return f"Excel generato {size} bytes"

check("CORE", "generate_excel_report", test_core_excel_report)


# ══════════════════════════════════════════════════════════════════════════════
# 6. NAVIGAZIONE — page_link puntano a file esistenti
# ══════════════════════════════════════════════════════════════════════════════

def test_nav_pages_exist():
    pages = [
        "app.py",
        "pages/1_Anagrafica.py",
        "pages/2_Risk.py",
        "pages/3_Piano.py",
        "pages/4_Engagement.py",
        "pages/5_Findings.py",
        "pages/6_Reporting.py",
    ]
    missing = [p for p in pages if not (ROOT / p).exists()]
    assert not missing, f"File mancanti: {missing}"
    return f"{len(pages)} pagine presenti"

check("NAVIGATION", "tutti i file di pagina esistono", test_nav_pages_exist)

def test_nav_links_in_common():
    common = (ROOT / "ui/common.py").read_text(encoding="utf-8")
    expected_links = [
        "app.py",
        "pages/1_Anagrafica.py",
        "pages/2_Risk.py",
        "pages/3_Piano.py",
        "pages/4_Engagement.py",
        "pages/5_Findings.py",
        "pages/6_Reporting.py",
    ]
    missing = [l for l in expected_links if l not in common]
    assert not missing, f"Link mancanti in common.py: {missing}"
    return "tutti i page_link presenti in common.py"

check("NAVIGATION", "page_link in ui/common.py", test_nav_links_in_common)


# ══════════════════════════════════════════════════════════════════════════════
# 7. CONSISTENZA — .gitignore e requirements
# ══════════════════════════════════════════════════════════════════════════════

def test_gitignore_db():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "audit.db" in gi, "audit.db non nel .gitignore"
    return "audit.db ignorato"

check("CONFIG", ".gitignore — audit.db escluso", test_gitignore_db)

def test_requirements_complete():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    expected = ["streamlit", "openai", "python-dotenv", "pypdf",
                "python-docx", "openpyxl", "reportlab",
                "plotly", "streamlit-authenticator", "PyYAML"]
    missing = [p for p in expected if p.lower() not in req.lower()]
    assert not missing, f"Dipendenze mancanti in requirements.txt: {missing}"
    return f"{len(expected)} dipendenze presenti"

check("CONFIG", "requirements.txt completo", test_requirements_complete)

def test_env_example():
    ex = ROOT / ".env.example"
    assert ex.exists(), ".env.example non trovato"
    content = ex.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in content
    return ".env.example presente con OPENAI_API_KEY"

check("CONFIG", ".env.example presente", test_env_example)


# ══════════════════════════════════════════════════════════════════════════════
# REPORT FINALE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═" * 80)
    print("  INTERNAL AUDIT PROTOTYPE — TEST SUITE")
    print("═" * 80)

    current_area = None
    passes = fails = 0

    for area, name, status in results:
        if area != current_area:
            print(f"\n── {area} {'─' * (60 - len(area))}")
            current_area = area
        icon = status[:2]
        print(f"  {icon}  {name}")
        if "FAIL" in status:
            detail = status[status.index("FAIL")+4:].strip()
            print(f"       └─ {detail}")
            fails += 1
        else:
            passes += 1

    print("\n" + "═" * 80)
    total = passes + fails
    print(f"  Risultato: {passes}/{total} test superati", end="")
    if fails:
        print(f"  |  {fails} FALLITI ← da correggere")
    else:
        print("  — tutto OK ✅")
    print("═" * 80 + "\n")
    sys.exit(0 if fails == 0 else 1)
