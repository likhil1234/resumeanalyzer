import os
import requests

SYSTEM = """You are an expert resume coach. Give practical, truthful, concise advice.
Never invent experience, employers, degrees, certifications, projects, metrics, or skills.
Use only information present in the supplied resume unless the user explicitly asks for suggestions.
When rewriting, preserve factual meaning and improve clarity, impact, ATS keyword usage, and grammar.
"""

def _ollama(prompt):
    url = os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/") + "/api/chat"
    model = os.getenv("OLLAMA_MODEL","llama3.2")
    r = requests.post(url, json={
        "model": model,
        "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
        "stream": False,
        "options":{"temperature":0.3}
    }, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _openai_compatible(prompt):
    base = os.getenv("AI_BASE_URL","").rstrip("/")
    key = os.getenv("AI_API_KEY","")
    model = os.getenv("AI_MODEL","")
    if not base or not key or not model:
        raise RuntimeError("AI_BASE_URL, AI_API_KEY and AI_MODEL are required.")
    r = requests.post(base + "/chat/completions",
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
        json={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],"temperature":0.3},
        timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def ask_ai(prompt):
    provider = os.getenv("AI_PROVIDER","ollama").lower()
    if provider == "ollama":
        return _ollama(prompt)
    if provider == "openai_compatible":
        return _openai_compatible(prompt)
    raise RuntimeError("Unsupported AI_PROVIDER.")

def build_context(resume, jd="", analysis=None, match=None):
    return f"""RESUME:
{resume[:18000]}

JOB DESCRIPTION (OPTIONAL):
{jd[:12000]}

ANALYSIS:
{analysis or {}}

MATCH:
{match or {}}
"""

def chat(resume, jd, analysis, match, question):
    prompt = build_context(resume,jd,analysis,match) + f"""

USER QUESTION:
{question}

Answer directly. If asked to rewrite something, return the improved text first, then a short explanation."""
    return ask_ai(prompt)

def rewrite(resume, jd, analysis, match, section):
    prompt = build_context(resume,jd,analysis,match) + f"""

TASK:
Rewrite the {section} section to be stronger and ATS-friendly for the target role.
If there is no job description, improve it for general professional use.
Do not invent facts. Return only the rewritten section followed by 2 short notes explaining the changes."""
    return ask_ai(prompt)
