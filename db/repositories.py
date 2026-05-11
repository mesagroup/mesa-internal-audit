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
        """INSERT INTO controls (id, title, area, description, check_points, expected_documents)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             title=excluded.title, area=excluded.area,
             description=excluded.description,
             check_points=excluded.check_points,
             expected_documents=excluded.expected_documents""",
        (
            c.id, c.title, c.area, c.description,
            json.dumps(c.check_points, ensure_ascii=False),
            json.dumps(c.expected_documents, ensure_ascii=False),
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
    return Control(
        id=row["id"],
        title=row["title"],
        area=row["area"],
        description=row["description"],
        check_points=json.loads(row["check_points"]),
        expected_documents=json.loads(row["expected_documents"]),
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
        """SELECT f.*, e.name AS engagement_name
           FROM findings f
           LEFT JOIN engagements e ON f.engagement_id = e.id
           ORDER BY f.detected_at DESC"""
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
        """SELECT f.*, e.name AS engagement_name
           FROM findings f
           LEFT JOIN engagements e ON f.engagement_id = e.id
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
