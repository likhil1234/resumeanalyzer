import os
import uuid
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from resume_parser import extract_text
from analyzer import analyze_resume
from matcher import match_resume, role_suggestions
from ai_service import chat, rewrite

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, resources={r"/api/*": {"origins": origins.split(",") if origins != "*" else "*"}})

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# PostgreSQL connection string (Neon, Supabase, Render, etc.)
# Example Neon: postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

engine = None
SessionLocal = None
db_ready = False

if DATABASE_URL:
    # Some providers (Render/Heroku) give postgres:// — SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    try:
        connect_args = {}
        if "sslmode" not in DATABASE_URL.lower():
            connect_args["sslmode"] = "require"
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        # Create table if not exists
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    analysis TEXT NOT NULL,
                    job_description TEXT DEFAULT '',
                    match_data TEXT,
                    suggestions TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_resumes_created_at
                ON resumes (created_at DESC)
            """))
        db_ready = True
    except Exception as e:
        print(f"[DB] Failed to connect: {e}")
        engine = None
        SessionLocal = None
        db_ready = False
else:
    print("[DB] DATABASE_URL not set. Set it to a free Postgres URL (Neon/Supabase/Render).")


def require_db():
    if not db_ready or SessionLocal is None:
        raise RuntimeError(
            "Database is not connected. Set DATABASE_URL to a PostgreSQL connection string "
            "(free options: Neon.tech, Supabase, or Render Postgres)."
        )


def serialize_row(row, include_text=False):
    if row is None:
        return None
    data = {
        "id": row["id"],
        "name": row["name"] or "",
        "filename": row["filename"] or "",
        "created_at": row["created_at"] or "",
        "analysis": json.loads(row["analysis"] or "{}"),
        "job_description": row["job_description"] or "",
        "match": json.loads(row["match_data"]) if row["match_data"] else None,
        "suggestions": json.loads(row["suggestions"] or "[]"),
    }
    if include_text:
        data["text"] = row["text"] or ""
    return data


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "database": db_ready,
        "db_type": "postgresql" if db_ready else None,
    })


@app.post("/api/resumes/analyze")
def analyze_upload():
    if "resume" not in request.files:
        return jsonify({"error": "Resume file is required."}), 400
    f = request.files["resume"]
    if not f.filename.lower().endswith((".pdf", ".docx")):
        return jsonify({"error": "Only PDF and DOCX files are supported."}), 400

    name = request.form.get("name") or os.path.splitext(secure_filename(f.filename))[0]
    jd = request.form.get("job_description", "").strip()
    temp = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{secure_filename(f.filename)}")
    f.save(temp)

    try:
        resume_text = extract_text(temp)
        analysis = analyze_resume(resume_text)
        matching = match_resume(resume_text, jd) if jd else None
        suggestions = role_suggestions(analysis)

        rid = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        require_db()
        session = SessionLocal()
        try:
            session.execute(
                text("""
                    INSERT INTO resumes
                    (id, name, filename, text, analysis, job_description, match_data, suggestions, created_at)
                    VALUES
                    (:id, :name, :filename, :text, :analysis, :job_description, :match_data, :suggestions, :created_at)
                """),
                {
                    "id": rid,
                    "name": name,
                    "filename": secure_filename(f.filename),
                    "text": resume_text,
                    "analysis": json.dumps(analysis),
                    "job_description": jd,
                    "match_data": json.dumps(matching) if matching is not None else None,
                    "suggestions": json.dumps(suggestions),
                    "created_at": created_at,
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return jsonify({
            "id": rid,
            "name": name,
            "filename": secure_filename(f.filename),
            "created_at": created_at,
            "analysis": analysis,
            "job_description": jd,
            "match": matching,
            "suggestions": suggestions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.remove(temp)
        except OSError:
            pass


@app.get("/api/resumes")
def list_resumes():
    try:
        require_db()
        session = SessionLocal()
        try:
            result = session.execute(
                text("""
                    SELECT id, name, filename, analysis, job_description, match_data, suggestions, created_at
                    FROM resumes
                    ORDER BY created_at DESC
                """)
            )
            rows = result.mappings().all()
            return jsonify([serialize_row(r) for r in rows])
        finally:
            session.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/resumes/<rid>")
def get_resume(rid):
    try:
        require_db()
        session = SessionLocal()
        try:
            result = session.execute(
                text("SELECT * FROM resumes WHERE id = :id"),
                {"id": rid},
            )
            row = result.mappings().first()
            if not row:
                return jsonify({"error": "Resume not found."}), 404
            return jsonify(serialize_row(row, include_text=True))
        finally:
            session.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.delete("/api/resumes/<rid>")
def delete_resume(rid):
    try:
        require_db()
        session = SessionLocal()
        try:
            result = session.execute(
                text("DELETE FROM resumes WHERE id = :id"),
                {"id": rid},
            )
            session.commit()
            return jsonify({"deleted": result.rowcount == 1})
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/match")
def match():
    data = request.get_json(force=True)
    return jsonify(match_resume(data.get("resume", ""), data.get("job_description", "")) or {})


@app.post("/api/chat")
def ai_chat():
    data = request.get_json(force=True)
    try:
        answer = chat(
            data.get("resume", ""),
            data.get("job_description", ""),
            data.get("analysis", {}),
            data.get("match"),
            data.get("question", ""),
        )
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@app.post("/api/rewrite")
def ai_rewrite():
    data = request.get_json(force=True)
    try:
        answer = rewrite(
            data.get("resume", ""),
            data.get("job_description", ""),
            data.get("analysis", {}),
            data.get("match"),
            data.get("section", "summary"),
        )
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)