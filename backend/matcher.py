import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from analyzer import extract_skills

STOP = {
    "the","and","for","with","that","this","from","your","you","are","our","will",
    "have","has","into","using","use","work","team","job","role","years","year",
    "skills","experience","required","responsibilities","looking","candidate"
}

def keywords(text, limit=40):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text.lower())
    counts = {}
    for w in words:
        if w in STOP or len(w) < 3:
            continue
        counts[w] = counts.get(w, 0) + 1
    return [w for w,_ in sorted(counts.items(), key=lambda x:(-x[1],x[0]))[:limit]]

def match_resume(resume_text, jd_text):
    if not jd_text.strip():
        return None

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
        matrix = vectorizer.fit_transform([resume_text, jd_text])
        similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception:
        similarity = 0.0

    resume_skills = set(extract_skills(resume_text))
    jd_skills = set(extract_skills(jd_text))
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)

    jd_keywords = keywords(jd_text)
    resume_lower = resume_text.lower()
    matched_keywords = [k for k in jd_keywords if k in resume_lower]
    missing_keywords = [k for k in jd_keywords if k not in resume_lower][:20]

    skill_ratio = len(matched) / len(jd_skills) if jd_skills else 0
    keyword_ratio = len(matched_keywords) / len(jd_keywords) if jd_keywords else 0

    score = round((similarity*0.55 + skill_ratio*0.30 + keyword_ratio*0.15)*100)

    return {
        "score": max(0,min(100,score)),
        "similarity": round(similarity*100,2),
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "jd_skills": sorted(jd_skills)
    }

def role_suggestions(analysis):
    skills = set(analysis.get("skills",[]))
    suggestions = []
    if {"python","sql"} <= skills:
        suggestions.append("Build a Python + SQL data analytics project with a dashboard.")
    if {"javascript","react"} <= skills:
        suggestions.append("Build a React dashboard consuming a real REST API.")
    if "machine learning" in skills or "scikit-learn" in skills:
        suggestions.append("Build an end-to-end ML project with evaluation and a small Flask UI.")
    if "excel" in skills or "power bi" in skills:
        suggestions.append("Build a business KPI dashboard using a realistic sales dataset.")
    if not suggestions:
        suggestions.append("Build one end-to-end project that demonstrates your strongest technical skills with measurable results.")
    return suggestions
