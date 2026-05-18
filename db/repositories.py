"""
Data-access layer per il prototipo Internal Audit.
Tutte le scritture appendono un record in audit_log.
"""
from __future__ import annotations

import json
from typing import Any

from db import get_conn
from core.controls_tree import Control


# ── Controls ──────────────────────────────────────────────────────────────────

def get_all_controls() -> list[Control]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM controls ORDER BY id").fetchall()
    conn.close()
    return [_row_to_control(r) for r in rows]


def get_control(control_id: str) -> Control | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM controls WHERE id = ?", (control_id,)).fetchone()
    conn.close()
    return _row_to_control(row) if row else None


def upsert_control(c: Control, user: str = "system") -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO controls
               (id, title, area, description, check_points, expected_documents, ctrl_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             title=excluded.title, area=excluded.area,
             description=excluded.description,
             check_points=excluded.check_points,
             expected_documents=excluded.expected_documents,
             ctrl_type=excluded.ctrl_type""",
        (
            c.id, c.title, c.area, c.description,
            json.dumps(c.check_points, ensure_ascii=False),
            json.dumps(c.expected_documents, ensure_ascii=False),
            c.ctrl_type,
        ),
    )
    _log(conn, user, "upsert", "control", c.id, f"title={c.title}")
    conn.commit()
    conn.close()


def delete_control(control_id: str, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM controls WHERE id = ?", (control_id,))
    _log(conn, user, "delete", "control", control_id)
    conn.commit()
    conn.close()


def reset_controls_to_defaults(user: str = "system") -> None:
    """Ripristina i 3 controlli del POC, sovrascrivendo quelli esistenti."""
    from core.controls_tree import CONTROLS_TREE
    for c in CONTROLS_TREE:
        upsert_control(c, user=user)


def _row_to_control(row) -> Control:
    keys = row.keys() if hasattr(row, "keys") else []
    return Control(
        id=row["id"],
        title=row["title"],
        area=row["area"],
        description=row["description"],
        check_points=json.loads(row["check_points"]),
        expected_documents=json.loads(row["expected_documents"]),
        ctrl_type=row["ctrl_type"] if "ctrl_type" in keys else "ai",
    )


# ── Owners ────────────────────────────────────────────────────────────────────

def get_all_owners() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM owners ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_owner(
    owner_id: int | None,
    name: str,
    role: str,
    area: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    if owner_id:
        conn.execute(
            "UPDATE owners SET name=?, role=?, area=? WHERE id=?",
            (name, role, area, owner_id),
        )
        new_id = owner_id
    else:
        cur = conn.execute(
            "INSERT INTO owners (name, role, area) VALUES (?, ?, ?)",
            (name, role, area),
        )
        new_id = cur.lastrowid
    _log(conn, user, "upsert", "owner", str(new_id), f"name={name}")
    conn.commit()
    conn.close()
    return new_id


def delete_owner(owner_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM owners WHERE id = ?", (owner_id,))
    _log(conn, user, "delete", "owner", str(owner_id))
    conn.commit()
    conn.close()


# ── Engagements ───────────────────────────────────────────────────────────────

def get_all_engagements() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM engagements ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_engagements() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM engagements WHERE status='active' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_engagement(eng_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM engagements WHERE id = ?", (eng_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_engagement(
    name: str, description: str = "", user: str = "system"
) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO engagements (name, description) VALUES (?, ?)",
        (name, description),
    )
    eng_id = cur.lastrowid
    _log(conn, user, "create", "engagement", str(eng_id), f"name={name}")
    conn.commit()
    conn.close()
    return eng_id


def close_engagement(eng_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE engagements SET status='closed', updated_at=datetime('now') WHERE id=?",
        (eng_id,),
    )
    _log(conn, user, "close", "engagement", str(eng_id))
    conn.commit()
    conn.close()


# ── Verifications ─────────────────────────────────────────────────────────────

def save_verification(
    engagement_id: int,
    control_id: str,
    result: Any,
    user: str = "system",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO verifications
           (engagement_id, control_id, overall_status, summary,
            check_points, mitigation_plan, raw_model_output)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            engagement_id, control_id,
            result.overall_status, result.summary,
            json.dumps(
                [
                    {
                        "check_point": cp.check_point,
                        "status": cp.status,
                        "evidence": cp.evidence,
                        "issue": cp.issue,
                        "mitigation": cp.mitigation,
                    }
                    for cp in result.check_points
                ],
                ensure_ascii=False,
            ),
            json.dumps(result.mitigation_plan, ensure_ascii=False),
            result.raw_model_output,
        ),
    )
    ver_id = cur.lastrowid
    _log(
        conn, user, "create", "verification", str(ver_id),
        f"control={control_id} status={result.overall_status}",
    )
    conn.commit()
    conn.close()
    return ver_id


def get_verifications_for_engagement(engagement_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM verifications
           WHERE engagement_id = ?
           ORDER BY verified_at DESC""",
        (engagement_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["check_points"] = json.loads(d["check_points"])
        d["mitigation_plan"] = json.loads(d["mitigation_plan"])
        result.append(d)
    return result


# ── Findings ──────────────────────────────────────────────────────────────────

def create_finding(
    verification_id: int | None,
    control_id: str,
    engagement_id: int,
    title: str,
    description: str,
    severity: str = "medio",
    user: str = "system",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO findings
           (verification_id, control_id, engagement_id, title, description, severity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (verification_id, control_id, engagement_id, title, description, severity),
    )
    fid = cur.lastrowid
    _log(
        conn, user, "create", "finding", str(fid),
        f"severity={severity} control={control_id}",
    )
    conn.commit()
    conn.close()
    return fid


def get_all_findings() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT f.*,
                  e.name      AS engagement_name,
                  c.title     AS control_title,
                  c.area      AS control_area,
                  c.ctrl_type AS ctrl_type
           FROM findings f
           LEFT JOIN engagements e ON f.engagement_id = e.id
           LEFT JOIN controls    c ON f.control_id    = c.id
           ORDER BY f.control_id ASC, f.detected_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_finding_status(
    finding_id: int, status: str, user: str = "system"
) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE findings SET status=?, updated_at=datetime('now') WHERE id=?",
        (status, finding_id),
    )
    _log(conn, user, "update_status", "finding", str(finding_id), f"status={status}")
    conn.commit()
    conn.close()


# ── Action Plans ──────────────────────────────────────────────────────────────

def create_action_plan(
    finding_id: int,
    description: str,
    owner_name: str,
    due_date: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO action_plans (finding_id, description, owner_name, due_date)
           VALUES (?, ?, ?, ?)""",
        (finding_id, description, owner_name, due_date),
    )
    ap_id = cur.lastrowid
    _log(
        conn, user, "create", "action_plan", str(ap_id),
        f"finding_id={finding_id}",
    )
    conn.commit()
    conn.close()
    return ap_id


def get_action_plans_for_finding(finding_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM action_plans WHERE finding_id = ? ORDER BY created_at",
        (finding_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_action_plans() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT ap.*, f.title AS finding_title, f.control_id, f.severity
           FROM action_plans ap
           JOIN findings f ON ap.finding_id = f.id
           ORDER BY ap.due_date ASC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_action_plan_status(
    ap_id: int, status: str, user: str = "system"
) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE action_plans SET status=?, updated_at=datetime('now') WHERE id=?",
        (status, ap_id),
    )
    _log(
        conn, user, "update_status", "action_plan", str(ap_id),
        f"status={status}",
    )
    conn.commit()
    conn.close()


# ── Audit Plans ───────────────────────────────────────────────────────────────

def get_engagements_by_plan() -> list[dict]:
    """
    Returns all plan items that have an engagement linked, grouped by plan.
    Each row contains: plan_id, plan_name, plan_year, control_id, control_title,
    control_area, ctrl_type, item_status, engagement_id, engagement_name,
    eng_status, planned_date, assigned_to.
    Ordered by plan year DESC, plan name, control_id.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            ap.id          AS plan_id,
            ap.name        AS plan_name,
            ap.year        AS plan_year,
            ap.status      AS plan_status,
            api.id         AS item_id,
            api.control_id,
            api.status     AS item_status,
            api.planned_date,
            api.assigned_to,
            api.engagement_id,
            e.name         AS engagement_name,
            e.status       AS eng_status,
            c.title        AS control_title,
            c.area         AS control_area,
            c.ctrl_type
        FROM audit_plan_items api
        JOIN audit_plans  ap ON ap.id  = api.plan_id
        JOIN engagements  e  ON e.id   = api.engagement_id
        JOIN controls     c  ON c.id   = api.control_id
        WHERE api.engagement_id IS NOT NULL
        ORDER BY ap.year DESC, ap.name, api.control_id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_plans() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_plans ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_plan(name: str, year: int, notes: str = "", user: str = "system") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO audit_plans (name, year, notes) VALUES (?, ?, ?)",
        (name, year, notes),
    )
    plan_id = cur.lastrowid
    _log(conn, user, "create", "audit_plan", str(plan_id), f"name={name} year={year}")
    conn.commit()
    conn.close()
    return plan_id


def update_plan_status(plan_id: int, status: str, user: str = "system") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE audit_plans SET status=?, updated_at=datetime('now') WHERE id=?",
        (status, plan_id),
    )
    _log(conn, user, "update_status", "audit_plan", str(plan_id), f"status={status}")
    conn.commit()
    conn.close()


def add_plan_item(
    plan_id: int,
    control_id: str,
    planned_date: str | None,
    assigned_to: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO audit_plan_items (plan_id, control_id, planned_date, assigned_to)
           VALUES (?, ?, ?, ?)""",
        (plan_id, control_id, planned_date, assigned_to),
    )
    item_id = cur.lastrowid
    _log(conn, user, "create", "plan_item", str(item_id), f"control={control_id}")
    conn.commit()
    conn.close()
    return item_id


def get_plan_items(plan_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT pi.*, c.title AS control_title, c.area AS control_area,
                  e.name AS engagement_name
           FROM audit_plan_items pi
           LEFT JOIN controls c ON pi.control_id = c.id
           LEFT JOIN engagements e ON pi.engagement_id = e.id
           WHERE pi.plan_id = ?
           ORDER BY pi.planned_date ASC""",
        (plan_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_engagement_to_item(item_id: int, engagement_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE audit_plan_items
           SET engagement_id=?, status='in_progress', updated_at=datetime('now')
           WHERE id=?""",
        (engagement_id, item_id),
    )
    _log(conn, user, "link", "plan_item", str(item_id), f"engagement={engagement_id}")
    conn.commit()
    conn.close()


def update_plan_item_status(item_id: int, status: str, user: str = "system") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE audit_plan_items SET status=? WHERE id=?", (status, item_id)
    )
    _log(conn, user, "update_status", "plan_item", str(item_id), f"status={status}")
    conn.commit()
    conn.close()


def delete_plan_item(item_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM audit_plan_items WHERE id=?", (item_id,))
    _log(conn, user, "delete", "plan_item", str(item_id))
    conn.commit()
    conn.close()


# ── Reporting queries ─────────────────────────────────────────────────────────

def get_findings_by_severity() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT severity, COUNT(*) AS count
           FROM findings GROUP BY severity ORDER BY
           CASE severity WHEN 'alto' THEN 1 WHEN 'medio' THEN 2 ELSE 3 END"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_findings_by_status() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM findings GROUP BY status"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_action_plans_by_status() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM action_plans GROUP BY status"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_plan_completion(plan_id: int) -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM audit_plan_items WHERE plan_id=?", (plan_id,)
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM audit_plan_items WHERE plan_id=? AND status='completed'",
        (plan_id,),
    ).fetchone()[0]
    in_progress = conn.execute(
        "SELECT COUNT(*) FROM audit_plan_items WHERE plan_id=? AND status='in_progress'",
        (plan_id,),
    ).fetchone()[0]
    conn.close()
    return {"total": total, "completed": completed, "in_progress": in_progress}


def get_recent_findings(limit: int = 10) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT f.*,
                  e.name      AS engagement_name,
                  c.title     AS control_title,
                  c.area      AS control_area,
                  c.ctrl_type AS ctrl_type
           FROM findings f
           LEFT JOIN engagements e ON f.engagement_id = e.id
           LEFT JOIN controls    c ON f.control_id    = c.id
           ORDER BY f.detected_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_engagement_summary(engagement_id: int) -> dict:
    """Dati per il report PDF di un singolo engagement."""
    conn = get_conn()
    eng = conn.execute(
        "SELECT * FROM engagements WHERE id=?", (engagement_id,)
    ).fetchone()
    verifications = conn.execute(
        "SELECT * FROM verifications WHERE engagement_id=?", (engagement_id,)
    ).fetchall()
    findings = conn.execute(
        "SELECT * FROM findings WHERE engagement_id=?", (engagement_id,)
    ).fetchall()
    action_plans = conn.execute(
        """SELECT ap.* FROM action_plans ap
           JOIN findings f ON ap.finding_id = f.id
           WHERE f.engagement_id=?""",
        (engagement_id,),
    ).fetchall()
    conn.close()
    import json
    return {
        "engagement": dict(eng) if eng else {},
        "verifications": [dict(v) for v in verifications],
        "findings": [dict(f) for f in findings],
        "action_plans": [dict(a) for a in action_plans],
    }


# ── Dashboard counts ──────────────────────────────────────────────────────────

def get_dashboard_counts() -> dict:
    conn = get_conn()
    return {
        "controls": conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0],
        "active_engagements": conn.execute(
            "SELECT COUNT(*) FROM engagements WHERE status='active'"
        ).fetchone()[0],
        "open_findings": conn.execute(
            "SELECT COUNT(*) FROM findings WHERE status='open'"
        ).fetchone()[0],
        "overdue_action_plans": conn.execute(
            "SELECT COUNT(*) FROM action_plans WHERE status NOT IN ('closed') AND due_date < date('now')"
        ).fetchone()[0],
    }


# ── Risk Scores ───────────────────────────────────────────────────────────────

def get_risk_scores(year: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM risk_scores WHERE year=? ORDER BY control_id", (year,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_risk_score(
    control_id: str,
    year: int,
    likelihood: int,
    impact: int,
    notes: str = "",
    user: str = "system",
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO risk_scores (control_id, year, likelihood, impact, notes, scored_by)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(control_id, year) DO UPDATE SET
             likelihood=excluded.likelihood, impact=excluded.impact,
             notes=excluded.notes, scored_by=excluded.scored_by,
             scored_at=datetime('now')""",
        (control_id, year, likelihood, impact, notes, user),
    )
    _log(conn, user, "upsert", "risk_score", f"{control_id}/{year}",
         f"L={likelihood} I={impact}")
    conn.commit()
    conn.close()


def get_risk_ranking(year: int) -> list[dict]:
    """Controlli ordinati per score (L×I) decrescente per l'anno dato."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT rs.control_id, rs.likelihood, rs.impact,
                  rs.likelihood * rs.impact AS score,
                  c.title, c.area
           FROM risk_scores rs
           LEFT JOIN controls c ON rs.control_id = c.id
           WHERE rs.year=?
           ORDER BY score DESC""",
        (year,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Audit Log (read) ──────────────────────────────────────────────────────────

def get_audit_log(limit: int = 100, offset: int = 0) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM audit_log
           ORDER BY ts DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_audit_log_count() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    conn.close()
    return n


# ── Controls per Processo (per auto-popolamento Piano) ───────────────────────

def get_controls_for_process(process_id: int) -> list[Control]:
    """
    Ritorna tutti i controlli (distinti) raggiungibili dalla catena
    Processo → Procedura → Rischio → Controllo.
    Usato per auto-popolare il Piano di Audit a partire da un processo.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT c.*
        FROM processes p
        JOIN process_procedure pp   ON p.id  = pp.process_id
        JOIN procedures pr          ON pr.id = pp.procedure_id
        JOIN procedure_risk prsk    ON pr.id = prsk.procedure_id
        JOIN risks r                ON r.id  = prsk.risk_id
        JOIN risk_control rc        ON r.id  = rc.risk_id
        JOIN controls c             ON c.id  = rc.control_id
        WHERE p.id = ?
        ORDER BY c.id
        """,
        (process_id,),
    ).fetchall()
    conn.close()
    return [_row_to_control(r) for r in rows]


# ── Risk Assessments (scoring per Rischio) ───────────────────────────────────

def get_risks_for_assessment() -> list[dict]:
    """
    Tutti i rischi con i nomi aggregati di processo e procedura associati.
    Usato per costruire la tabella di scoring del Risk Assessment.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            r.id                                        AS risk_id,
            r.code                                      AS risk_code,
            r.name                                      AS risk_name,
            r.category                                  AS category,
            COALESCE(
                GROUP_CONCAT(DISTINCT
                    CASE WHEN p.code != '' THEN p.code || ' — ' || p.name
                         ELSE p.name END
                ), ''
            )                                           AS processi,
            COALESCE(
                GROUP_CONCAT(DISTINCT
                    CASE WHEN pr.code != '' THEN pr.code || ' — ' || pr.name
                         ELSE pr.name END
                ), ''
            )                                           AS procedure
        FROM risks r
        LEFT JOIN procedure_risk prsk ON r.id  = prsk.risk_id
        LEFT JOIN procedures pr       ON pr.id = prsk.procedure_id
        LEFT JOIN process_procedure pp ON pr.id = pp.procedure_id
        LEFT JOIN processes p          ON p.id  = pp.process_id
        GROUP BY r.id
        ORDER BY processi, procedure, r.code, r.name
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_risk_assessment_scores(year: int) -> dict[int, dict]:
    """Ritorna {risk_id: {likelihood, impact, notes}} per l'anno dato."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT risk_id, likelihood, impact, notes FROM risk_assessments WHERE year=?",
        (year,),
    ).fetchall()
    conn.close()
    return {r["risk_id"]: dict(r) for r in rows}


def upsert_risk_assessment(
    risk_id: int,
    year: int,
    likelihood: int,
    impact: int,
    notes: str = "",
    user: str = "system",
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO risk_assessments (risk_id, year, likelihood, impact, notes,
               scored_by, scored_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(risk_id, year) DO UPDATE SET
               likelihood=excluded.likelihood,
               impact=excluded.impact,
               notes=excluded.notes,
               scored_by=excluded.scored_by,
               scored_at=datetime('now')""",
        (risk_id, year, likelihood, impact, notes, user),
    )
    _log(conn, user, "upsert", "risk_assessment", f"{risk_id}/{year}",
         f"L={likelihood} I={impact}")
    conn.commit()
    conn.close()


def get_risk_assessment_ranking(year: int) -> list[dict]:
    """Rischi con score ordinati per punteggio decrescente, con contesto P/PR."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            r.id                                        AS risk_id,
            r.code                                      AS risk_code,
            r.name                                      AS risk_name,
            r.category                                  AS category,
            ra.likelihood,
            ra.impact,
            ra.likelihood * ra.impact                   AS score,
            COALESCE(
                GROUP_CONCAT(DISTINCT
                    CASE WHEN p.code != '' THEN p.code || ' — ' || p.name
                         ELSE p.name END
                ), '—'
            )                                           AS processi,
            COALESCE(
                GROUP_CONCAT(DISTINCT
                    CASE WHEN pr.code != '' THEN pr.code || ' — ' || pr.name
                         ELSE pr.name END
                ), '—'
            )                                           AS procedure
        FROM risk_assessments ra
        JOIN risks r              ON r.id  = ra.risk_id
        LEFT JOIN procedure_risk prsk ON r.id  = prsk.risk_id
        LEFT JOIN procedures pr       ON pr.id = prsk.procedure_id
        LEFT JOIN process_procedure pp ON pr.id = pp.procedure_id
        LEFT JOIN processes p          ON p.id  = pp.process_id
        WHERE ra.year = ?
        GROUP BY r.id
        ORDER BY score DESC, r.code
        """,
        (year,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Processes ────────────────────────────────────────────────────────────────

def get_all_processes() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM processes ORDER BY code, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_process(
    proc_id: int | None,
    code: str, name: str, description: str, owner: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    if proc_id:
        conn.execute(
            "UPDATE processes SET code=?, name=?, description=?, owner=? WHERE id=?",
            (code, name, description, owner, proc_id),
        )
        pid = proc_id
        action = "update"
    else:
        cur = conn.execute(
            "INSERT INTO processes (code, name, description, owner) VALUES (?,?,?,?)",
            (code, name, description, owner),
        )
        pid = cur.lastrowid
        action = "create"
    _log(conn, user, action, "process", str(pid), f"name={name}")
    conn.commit()
    conn.close()
    return pid


def delete_process(proc_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM processes WHERE id=?", (proc_id,))
    _log(conn, user, "delete", "process", str(proc_id))
    conn.commit()
    conn.close()


# ── Procedures ────────────────────────────────────────────────────────────────

def get_all_procedures() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM procedures ORDER BY code, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_procedure(
    proced_id: int | None,
    code: str, name: str, description: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    if proced_id:
        conn.execute(
            "UPDATE procedures SET code=?, name=?, description=? WHERE id=?",
            (code, name, description, proced_id),
        )
        pid = proced_id
        action = "update"
    else:
        cur = conn.execute(
            "INSERT INTO procedures (code, name, description) VALUES (?,?,?)",
            (code, name, description),
        )
        pid = cur.lastrowid
        action = "create"
    _log(conn, user, action, "procedure", str(pid), f"name={name}")
    conn.commit()
    conn.close()
    return pid


def delete_procedure(proced_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM procedures WHERE id=?", (proced_id,))
    _log(conn, user, "delete", "procedure", str(proced_id))
    conn.commit()
    conn.close()


def get_process_ids_for_procedure(proced_id: int) -> list[int]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT process_id FROM process_procedure WHERE procedure_id=?", (proced_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_procedure_processes(
    proced_id: int, process_ids: list[int], user: str = "system"
) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM process_procedure WHERE procedure_id=?", (proced_id,))
    for pid in process_ids:
        conn.execute(
            "INSERT OR IGNORE INTO process_procedure (process_id, procedure_id) VALUES (?,?)",
            (pid, proced_id),
        )
    _log(conn, user, "upsert", "process_procedure", str(proced_id),
         f"process_ids={process_ids}")
    conn.commit()
    conn.close()


# ── Risks ─────────────────────────────────────────────────────────────────────

def get_all_risks() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM risks ORDER BY code, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_risk(
    risk_id: int | None,
    code: str, name: str, description: str, category: str,
    user: str = "system",
) -> int:
    conn = get_conn()
    if risk_id:
        conn.execute(
            "UPDATE risks SET code=?, name=?, description=?, category=? WHERE id=?",
            (code, name, description, category, risk_id),
        )
        rid = risk_id
        action = "update"
    else:
        cur = conn.execute(
            "INSERT INTO risks (code, name, description, category) VALUES (?,?,?,?)",
            (code, name, description, category),
        )
        rid = cur.lastrowid
        action = "create"
    _log(conn, user, action, "risk", str(rid), f"name={name}")
    conn.commit()
    conn.close()
    return rid


def delete_risk(risk_id: int, user: str = "system") -> None:
    conn = get_conn()
    conn.execute("DELETE FROM risks WHERE id=?", (risk_id,))
    _log(conn, user, "delete", "risk", str(risk_id))
    conn.commit()
    conn.close()


def get_procedure_ids_for_risk(risk_id: int) -> list[int]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT procedure_id FROM procedure_risk WHERE risk_id=?", (risk_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_risk_procedures(
    risk_id: int, procedure_ids: list[int], user: str = "system"
) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM procedure_risk WHERE risk_id=?", (risk_id,))
    for pid in procedure_ids:
        conn.execute(
            "INSERT OR IGNORE INTO procedure_risk (procedure_id, risk_id) VALUES (?,?)",
            (pid, risk_id),
        )
    _log(conn, user, "upsert", "procedure_risk", str(risk_id),
         f"procedure_ids={procedure_ids}")
    conn.commit()
    conn.close()


def get_control_ids_for_risk(risk_id: int) -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT control_id FROM risk_control WHERE risk_id=?", (risk_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_risk_controls(
    risk_id: int, control_ids: list[str], user: str = "system"
) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM risk_control WHERE risk_id=?", (risk_id,))
    for cid in control_ids:
        conn.execute(
            "INSERT OR IGNORE INTO risk_control (risk_id, control_id) VALUES (?,?)",
            (risk_id, cid),
        )
    _log(conn, user, "upsert", "risk_control", str(risk_id),
         f"control_ids={control_ids}")
    conn.commit()
    conn.close()


# ── RCM ──────────────────────────────────────────────────────────────────────

def get_rcm() -> list[dict]:
    """
    Ritorna le righe della Risk Control Matrix (catena completa):
    Processo → Procedura → Rischio → Controllo.
    Solo catene complete (inner join).
    Campi restituiti includono id, codici, nomi e metadati
    per consentire raggruppamento gerarchico lato UI.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            p.id                AS proc_id,
            p.code              AS proc_code,
            p.name              AS proc_name,
            p.owner             AS proc_owner,
            pr.id               AS proced_id,
            pr.code             AS proced_code,
            pr.name             AS proced_name,
            pr.description      AS proced_desc,
            r.id                AS risk_id,
            r.code              AS risk_code,
            r.name              AS risk_name,
            r.description       AS risk_desc,
            r.category          AS risk_category,
            c.id                AS ctrl_id,
            c.title             AS ctrl_title,
            c.area              AS ctrl_area
        FROM processes p
        JOIN process_procedure pp   ON p.id  = pp.process_id
        JOIN procedures pr          ON pr.id = pp.procedure_id
        JOIN procedure_risk prsk    ON pr.id = prsk.procedure_id
        JOIN risks r                ON r.id  = prsk.risk_id
        JOIN risk_control rc        ON r.id  = rc.risk_id
        JOIN controls c             ON c.id  = rc.control_id
        ORDER BY p.code, p.name, pr.code, pr.name, r.code, r.name, c.id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rcm_gaps() -> dict:
    """Entità non ancora collegate (per la sezione 'lacune' dell'RCM)."""
    conn = get_conn()

    unlinked_procs = conn.execute(
        """SELECT p.id, p.name FROM processes p
           WHERE p.id NOT IN (SELECT DISTINCT process_id FROM process_procedure)"""
    ).fetchall()

    unlinked_proceds = conn.execute(
        """SELECT pr.id, pr.name FROM procedures pr
           WHERE pr.id NOT IN (SELECT DISTINCT procedure_id FROM procedure_risk)"""
    ).fetchall()

    unlinked_risks = conn.execute(
        """SELECT r.id, r.name FROM risks r
           WHERE r.id NOT IN (SELECT DISTINCT risk_id FROM risk_control)"""
    ).fetchall()

    conn.close()
    return {
        "processes":  [dict(r) for r in unlinked_procs],
        "procedures": [dict(r) for r in unlinked_proceds],
        "risks":      [dict(r) for r in unlinked_risks],
    }


# ── Internal ──────────────────────────────────────────────────────────────────

def _log(
    conn,
    user: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO audit_log (user_name, action, entity_type, entity_id, details)
           VALUES (?, ?, ?, ?, ?)""",
        (user, action, entity_type, entity_id, details),
    )
