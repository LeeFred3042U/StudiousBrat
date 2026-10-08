"""FastAPI endpoints.

POST   /profiles                     create a student profile
PATCH  /profiles/{id}                explicit edit only
DELETE /profiles/{id}                "Delete my data" - cascade does the rest
GET    /profiles/{id}/sessions       sidebar session list
POST   /chat                         one orchestrator turn
POST   /sessions/{id}/end            explicit end
GET    /sessions/{id}                full history + assets (resume the UI)
POST   /sessions/{id}/export         WeasyPrint PDF -> {pdf_url}
GET    /health                       liveness
"""
import json
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from .config import settings
from .export_pdf import export_session_pdf
from .messages import GENERIC_TROUBLE
from .orchestrator import run_turn
from .tools import ToolFailure, generate_memes

os.makedirs("static", exist_ok=True)
os.makedirs(settings.export_dir, exist_ok=True)

app = FastAPI(title="Analogy Tutor API")

_origins = ["*"] if settings.frontend_origin == "*" else [settings.frontend_origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup() -> None:
    await db.init()


@app.on_event("shutdown")
async def shutdown() -> None:
    await db.close()


class ProfileIn(BaseModel):
    name: str | None = None
    grade_level: str | None = None
    subjects: list[str] = []
    preferred_universe: str | None = None


class ProfilePatch(BaseModel):
    name: str | None = None
    grade_level: str | None = None
    subjects: list[str] | None = None
    preferred_universe: str | None = None


class ChatIn(BaseModel):
    student_id: str
    session_id: str | None = None
    message: str
    # Frontend "New topic" button sets this so /chat never silently resumes
    # the previous active session.
    new_session: bool = False


def _load(content):
    return json.loads(content) if isinstance(content, str) else content


async def _profile_or_404(pid: str) -> dict:
    try:
        uid = uuid.UUID(pid)
    except ValueError:
        raise HTTPException(400, "invalid profile id")
    try:
        row = await db.fetchrow("SELECT * FROM student_profiles WHERE id=$1", uid)
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    if row is None:
        raise HTTPException(404, "profile not found")
    return dict(row)


async def _resolve_session(student_uuid, body: ChatIn) -> dict:
    if body.session_id:
        row = await db.fetchrow(
            "SELECT * FROM sessions WHERE id=$1 AND student_id=$2",
            uuid.UUID(body.session_id),
            student_uuid,
        )
        if row is None:
            raise HTTPException(404, "session not found")
        return dict(row)
    if not body.new_session:
        # Resume the most recent active session opened within the last 24h.
        row = await db.fetchrow(
            "SELECT * FROM sessions WHERE student_id=$1 AND status='active' "
            "AND created_at > NOW() - INTERVAL '24 hours' "
            "ORDER BY created_at DESC LIMIT 1",
            student_uuid,
        )
        if row is not None:
            return dict(row)
    row = await db.fetchrow(
        "INSERT INTO sessions (student_id, topic) VALUES ($1, $2) RETURNING *",
        student_uuid,
        body.message[:80],
    )
    return dict(row)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/profiles")
async def create_profile(p: ProfileIn):
    try:
        row = await db.fetchrow(
            "INSERT INTO student_profiles (name, grade_level, subjects, preferred_universe) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            p.name,
            p.grade_level,
            p.subjects,
            p.preferred_universe,
        )
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    return dict(row)


@app.patch("/profiles/{pid}")
async def patch_profile(pid: str, p: ProfilePatch):
    prof = await _profile_or_404(pid)  # explicit edit only; never inferred
    name = p.name if p.name is not None else prof["name"]
    grade = p.grade_level if p.grade_level is not None else prof["grade_level"]
    subjects = p.subjects if p.subjects is not None else list(prof["subjects"] or [])
    universe = (
        p.preferred_universe if p.preferred_universe is not None
        else prof["preferred_universe"]
    )
    try:
        row = await db.fetchrow(
            "UPDATE student_profiles SET name=$1, grade_level=$2, subjects=$3, "
            "preferred_universe=$4, updated_at=NOW() WHERE id=$5 RETURNING *",
            name,
            grade,
            subjects,
            universe,
            prof["id"],
        )
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    return dict(row)


@app.delete("/profiles/{pid}")
async def delete_profile(pid: str):
    # "Delete my data": a single DELETE; ON DELETE CASCADE removes every
    # dependent session, message, evaluation and asset row.
    prof = await _profile_or_404(pid)
    try:
        await db.execute("DELETE FROM student_profiles WHERE id=$1", prof["id"])
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    return {"deleted": True}


@app.get("/profiles/{pid}/sessions")
async def list_sessions(pid: str):
    prof = await _profile_or_404(pid)
    try:
        rows = await db.fetch(
            "SELECT id, topic, status, created_at FROM sessions "
            "WHERE student_id=$1 ORDER BY created_at DESC LIMIT 50",
            prof["id"],
        )
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    return [dict(r) for r in rows]


@app.post("/chat")
async def chat(body: ChatIn):
    profile = await _profile_or_404(body.student_id)
    student_uuid = profile["id"]

    # Best-effort housekeeping: end idle sessions, replay queued writes.
    try:
        await db.execute(
            "UPDATE sessions s SET status='ended', ended_at=NOW() "
            "WHERE s.student_id=$1 AND s.status='active' AND NOT EXISTS ("
            "  SELECT 1 FROM session_messages m WHERE m.session_id=s.id "
            "  AND m.created_at > NOW() - make_interval(mins => $2))",
            student_uuid,
            settings.session_idle_minutes,
        )
        await db.flush_pending()
    except db.DatabaseError:
        pass

    try:
        session = await _resolve_session(student_uuid, body)
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")

    if isinstance(session.get("sub_concepts"), str):
        session["sub_concepts"] = json.loads(session["sub_concepts"])

    persisted = True

    # Conversation history BEFORE this message, for the orchestrator.
    try:
        rows = await db.fetch(
            "SELECT role, content FROM session_messages WHERE session_id=$1 "
            "ORDER BY created_at, id",
            session["id"],
        )
        history = [
            {"role": "user" if r["role"] == "student" else "assistant",
             "content": r["content"]}
            for r in rows
        ]
    except db.DatabaseError:
        history = []
        persisted = False

    result = await run_turn(profile, session, history, body.message)

    # Memes are an app-side extra: generate once per new topic, tolerate
    # failure (the turn's text never depends on them).
    if (
        not result["error"]
        and result.get("session_update")
        and not any(a["asset_type"] == "memes" for a in result["assets"])
    ):
        try:
            memes = await generate_memes(
                session.get("topic") or "",
                result["session_update"]["sub_concepts"],
            )
            result["assets"].append({"asset_type": "memes", "content": memes})
        except ToolFailure:
            pass

    error = result["error"] or not result["reply"]
    reply = GENERIC_TROUBLE if error else result["reply"]

    # Persist this turn. Failed writes queue for replay on the next action;
    # a failed LLM step already produced no assets/evaluation, so nothing
    # partial is written.
    ops: list[tuple[str, tuple]] = [
        (
            "INSERT INTO session_messages (session_id, role, content, message_type) "
            "VALUES ($1, 'student', $2, $3)",
            (session["id"], body.message, None),
        ),
        (
            "INSERT INTO session_messages (session_id, role, content, message_type) "
            "VALUES ($1, 'ai', $2, $3)",
            (session["id"], reply, "error" if error else None),
        ),
    ]
    if result.get("session_update"):
        su = result["session_update"]
        ops.append((
            "UPDATE sessions SET sub_concepts=$1::jsonb, has_sequence=$2 WHERE id=$3",
            (json.dumps(su["sub_concepts"]), su["has_sequence"], session["id"]),
        ))
    for a in result.get("assets") or []:
        ops.append((
            "INSERT INTO generated_assets (session_id, asset_type, content) "
            "VALUES ($1, $2, $3::jsonb)",
            (session["id"], a["asset_type"], json.dumps(a["content"])),
        ))
    ev = result.get("evaluation")
    if ev:
        ops.append((
            "INSERT INTO evaluations (session_id, student_analogy, sub_concepts_covered, "
            "sub_concepts_missing, relationship_correct, coverage_pct, band, feedback) "
            "VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7, $8)",
            (session["id"], ev["student_analogy"], json.dumps(ev["covered"]),
             json.dumps(ev["missing"]), ev["relationship_correct"], ev["coverage_pct"],
             ev["band"], ev["feedback"]),
        ))

    for sql, args in ops:
        try:
            await db.execute(sql, *args)
        except db.DatabaseError:
            db.queue_write(sql, args)
            persisted = False

    return {
        "session_id": str(session["id"]),
        "reply": reply,
        "assets": result.get("assets") or [],
        "error": error,
        "persisted": persisted,
    }


@app.post("/sessions/{sid}/end")
async def end_session(sid: str):
    try:
        uid = uuid.UUID(sid)
    except ValueError:
        raise HTTPException(400, "invalid session id")
    try:
        row = await db.fetchrow(
            "UPDATE sessions SET status='ended', ended_at=NOW() "
            "WHERE id=$1 AND status='active' RETURNING id",
            uid,
        )
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    if row is None:
        raise HTTPException(404, "session not found or already ended")
    return {"ended": True}


@app.get("/sessions/{sid}")
async def get_session(sid: str):
    try:
        uid = uuid.UUID(sid)
    except ValueError:
        raise HTTPException(400, "invalid session id")
    try:
        row = await db.fetchrow("SELECT * FROM sessions WHERE id=$1", uid)
        if row is None:
            raise HTTPException(404, "session not found")
        msgs = await db.fetch(
            "SELECT id, role, content, message_type, created_at FROM session_messages "
            "WHERE session_id=$1 ORDER BY created_at, id",
            uid,
        )
        arows = await db.fetch(
            "SELECT asset_type, content, created_at FROM generated_assets "
            "WHERE session_id=$1 ORDER BY created_at",
            uid,
        )
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    return {
        "session": dict(row),
        "messages": [dict(m) for m in msgs],
        "assets": [
            {
                "asset_type": r["asset_type"],
                "content": _load(r["content"]),
                "created_at": r["created_at"].isoformat(),
            }
            for r in arows
        ],
    }


@app.post("/sessions/{sid}/export")
async def export_session(sid: str):
    try:
        uid = uuid.UUID(sid)
    except ValueError:
        raise HTTPException(400, "invalid session id")
    try:
        row = await db.fetchrow("SELECT id FROM sessions WHERE id=$1", uid)
        if row is None:
            raise HTTPException(404, "session not found")
        result = await export_session_pdf(uid)
        await db.execute(
            "INSERT INTO generated_assets (session_id, asset_type, url) "
            "VALUES ($1, 'pdf', $2)",
            uid,
            result["pdf_url"],
        )
    except HTTPException:
        raise
    except db.DatabaseError:
        raise HTTPException(503, "database unavailable")
    except Exception:
        raise HTTPException(500, "export failed")
    return result
