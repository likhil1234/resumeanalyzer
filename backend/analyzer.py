import re

SKILLS = [
    "python","java","c","c++","c#","javascript","typescript","html","css","react",
    "angular","vue","node.js","express","flask","django","php","spring","sql",
    "mysql","postgresql","mongodb","sqlite","supabase","git","github","docker",
    "kubernetes","aws","azure","gcp","excel","power bi","tableau","pandas",
    "numpy","scikit-learn","tensorflow","pytorch","machine learning","nlp",
    "data analysis","data visualization","rest api","api","bootstrap","tailwind",
    "chart.js","figma","linux","selenium","pytest","fastapi","next.js"
]

SECTION_ALIASES = {
    "summary": ["summary","profile","objective","professional summary","career objective"],
    "skills": ["skills","technical skills","core skills","technical expertise"],
    "education": ["education","academic background","academic qualifications"],
    "experience": ["experience","work experience","professional experience","employment"],
    "projects": ["projects","academic projects","personal projects","project experience"],
    "certifications": ["certifications","certificates","licenses"],
    "achievements": ["achievements","awards","honors"],
}

def normalize(s):
    return re.sub(r"[^a-z0-9+#. ]+", " ", s.lower())

def extract_skills(text):
    t = normalize(text)
    found = []
    for skill in SKILLS:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, t):
            found.append(skill)
    return sorted(set(found))

def find_sections(text):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    sections = {}
    current = None
    for line in lines:
        n = normalize(line).strip()
        matched = None
        for key, aliases in SECTION_ALIASES.items():
            if n in aliases or any(n == a for a in aliases):
                matched = key
                break
        if matched:
            current = matched
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k,v in sections.items()}

def extract_contact(text):
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}\b", text.replace("(","").replace(")",""))
    links = re.findall(r"https?://\S+|(?:www\.)\S+", text)
    return {
        "email": email.group(0) if email else "",
        "phone": phone.group(0) if phone else "",
        "links": links[:10],
    }

def analyze_resume(text):
    sections = find_sections(text)
    skills = extract_skills(text)
    contact = extract_contact(text)
    checks = []

    expected = ["summary","skills","education","projects"]
    for s in expected:
        if s not in sections or len(sections[s].strip()) < 15:
            checks.append({"type":"warning","message":f"{s.title()} section is missing or too short."})

    if not contact["email"]:
        checks.append({"type":"warning","message":"No email address detected."})
    if not contact["phone"]:
        checks.append({"type":"warning","message":"No phone number detected."})
    if len(text.split()) < 180:
        checks.append({"type":"warning","message":"Resume appears quite short; consider adding relevant evidence and achievements."})
    if len(text.split()) > 900:
        checks.append({"type":"warning","message":"Resume is lengthy; consider removing less relevant content."})

    action_words = ["developed","built","created","designed","implemented","analyzed","automated","improved","optimized","led"]
    action_count = sum(len(re.findall(r"\b"+w+r"\b", text.lower())) for w in action_words)
    if action_count < 2:
        checks.append({"type":"info","message":"Add stronger action verbs to project and experience bullets."})

    score = 100
    score -= min(30, sum(8 for c in checks if c["type"]=="warning"))
    score += min(10, len(skills)//3)
    score = max(0, min(100, score))

    return {
        "score": score,
        "skills": skills,
        "sections": sections,
        "contact": contact,
        "checks": checks,
        "word_count": len(text.split()),
        "character_count": len(text),
    }
