import json
import re
import logging
from typing import Any, Dict
from agents.utils import groq_client, USE_LLM

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _extract_json_block(text: str) -> str:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    try:
        start = text.index("{")
        end = text.rindex("}")
        return text[start : end + 1]
    except ValueError:
        raise ValueError("No JSON object found in LLM response")


def _validate_and_normalize(plan: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a JSON object")
    slides = plan.get("slides")
    if not isinstance(slides, list):
        raise ValueError("Plan missing 'slides' list")
    normalized = {"slides": [], "title": plan.get("title", "")}
    for s in slides:
        title = s.get("title") if isinstance(s, dict) else None
        bullets = s.get("bullets") if isinstance(s, dict) else None
        if title is None:
            raise ValueError("Each slide must have a 'title'")
        if bullets is None:
            bullets = []
        if isinstance(bullets, str):
            bullets = [bullets]
        if not isinstance(bullets, list):
            raise ValueError("'bullets' must be a list or string")
        normalized["slides"].append({"title": title, "bullets": bullets})
    return normalized


_CLI_PREFIXES = (
    "git ", "npm ", "pip ", "python ", "docker", "kubectl",
    "cd ", "mkdir", "rm ", "cp ", "mv ", "curl ", "wget ",
    "$", "./", "yarn ", "composer", "php ", "```",
)

_TECH_HEADERS = [
    "installation", "stack", "architecture", "déploiement", "deployment",
    "configuration", "setup", "requirements", "prérequis", "api",
    "docker", "kubernetes", "ci/cd", "roadmap", "performance",
    "sécurité", "security", "contributing", "contribuer", "license",
    "changelog", "tests", "testing", "technical", "technique"
]


def _strip_readme_for_audience(readme_content: str, audience: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", readme_content)
    text = re.sub(r"`[^`]+`", "", text)
    if audience in ("manager", "investor"):
        lines = text.splitlines()
        filtered = []
        skip_section = False
        for line in lines:
            stripped_lower = line.strip().lower().lstrip("#- *").strip()
            is_header = line.strip().startswith("#")
            if is_header:
                skip_section = any(h in stripped_lower for h in _TECH_HEADERS)
            if skip_section:
                continue
            if any(stripped_lower.startswith(p) for p in _CLI_PREFIXES):
                continue
            filtered.append(line)
        text = "\n".join(filtered)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_markdown_sections(readme_content: str, audience: str = "developer") -> Dict[str, Any]:
    text = _strip_readme_for_audience(readme_content, audience)
    lines = text.splitlines()
    slides = []
    current_section = None
    current_bullets = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_section and current_bullets:
                slides.append({"title": current_section, "bullets": current_bullets})
            current_section = stripped[3:].strip()
            current_bullets = []
        elif current_section and stripped:
            bullet_text = stripped.lstrip("- *+ ").strip()
            if bullet_text and not any(bullet_text.lower().startswith(p) for p in _CLI_PREFIXES):
                current_bullets.append(bullet_text)

    if current_section and current_bullets:
        slides.append({"title": current_section, "bullets": current_bullets})

    if not slides:
        clean_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        bullets = clean_lines[:5] if clean_lines else ["Aucun contenu trouvé dans le README"]
        slides = [{"title": "Présentation automatique", "bullets": bullets}]

    return {"slides": slides}


SKELETONS_FR = {
    "developer": [
        "Vue d'ensemble technique",
        "Stack technique",
        "Architecture & composants",
        "Installation & déploiement",
        "Fonctionnalités techniques",
        "Performance & sécurité",
        "Roadmap technique",
    ],
    "manager": [
        "Résumé exécutif",
        "Le problème que nous résolvons",
        "Notre solution",
        "Résultats & KPIs attendus",
        "Planning & ressources",
        "Ce qu'il faut retenir",
    ],
    "investor": [
        "Le problème",
        "Notre solution",
        "Fonctionnalités qui font la différence",
        "Résultats & traction",
        "Modèle économique",
        "Passez à l'action",
    ],
}

SKELETONS_EN = {
    "developer": [
        "Technical Overview",
        "Tech Stack",
        "Architecture & Components",
        "Installation & Deployment",
        "Key Technical Features",
        "Performance & Security",
        "Technical Roadmap",
    ],
    "manager": [
        "Executive Summary",
        "The Problem We Solve",
        "Our Solution",
        "Results & Expected KPIs",
        "Planning & Resources",
        "Key Takeaways",
    ],
    "investor": [
        "The Problem",
        "Our Solution",
        "Features That Make the Difference",
        "Results & Traction",
        "Business Model",
        "Take Action",
    ],
}


def _detect_lang(text: str) -> str:
    fr_words = {"le", "la", "les", "de", "du", "des", "et", "est", "une", "un",
                "pour", "dans", "sur", "avec", "par", "qui", "que", "ce", "se",
                "nous", "vous", "ils", "sont", "aux", "au"}
    en_words = {"the", "a", "an", "is", "are", "of", "to", "in", "and", "for",
                "with", "that", "this", "it", "we", "you", "they", "be", "has",
                "have", "from", "by", "at", "our", "your"}
    words = set(re.findall(r'\b[a-z]+\b', text[:2000].lower()))
    return "en" if len(words & en_words) > len(words & fr_words) else "fr"


def _build_skeleton_json(titles: list) -> str:
    slides = [{"title": t, "bullets": ["...", "...", "..."]} for t in titles]
    return json.dumps({"title": "TITRE_A_REMPLIR", "slides": slides}, ensure_ascii=False, indent=2)


def _get_audience_rules(audience: str, lang: str) -> str:
    rules = {
        "developer": "Vocabulaire technique : APIs, CI/CD, microservices, Docker, versions exactes. PAS de prix ni ROI.",
        "manager":   "Langage business : chiffres, pourcentages, ROI, délais. INTERDIT : Docker, API, code, commandes bash.",
        "investor":  "Langage persuasif : benefices, ROI, chiffres impact. INTERDIT : code, architecture technique, commandes.",
    }
    if lang == "en":
        rules_en = {
            "developer": "Technical vocabulary: APIs, CI/CD, microservices, Docker, exact versions. NO prices or ROI.",
            "manager":   "Business language: numbers, percentages, ROI, timelines. FORBIDDEN: Docker, API, code, bash commands.",
            "investor":  "Persuasive language: benefits, ROI, impact numbers. FORBIDDEN: code, technical architecture, commands.",
        }
        return rules_en.get(audience, "")
    return rules.get(audience, "")


def _call_llm_api(readme_content: str, lang: str = "auto", audience: str = "developer") -> Dict[str, Any]:
    cleaned_readme = _strip_readme_for_audience(readme_content, audience)
    effective_lang = lang if lang != "auto" else _detect_lang(readme_content)
    skeletons = SKELETONS_EN if effective_lang == "en" else SKELETONS_FR
    titles = skeletons.get(audience, SKELETONS_FR["developer"])
    skeleton = _build_skeleton_json(titles)
    rules = _get_audience_rules(audience, effective_lang)

    if effective_lang == "en":
        system_msg = "You are a PowerPoint expert. Reply ONLY with valid JSON, no extra text."
        prompt = f"""Fill in the bullets for each slide of this PowerPoint presentation.
The slide TITLES are FIXED — do NOT change them.
Only fill in the "bullets" arrays with 3-5 relevant points extracted from the README.
Translate everything to ENGLISH.

RULES: {rules}

README (source of information):
{cleaned_readme}

JSON to complete (keep exact titles, only fill bullets and the main title):
{skeleton}

Reply ONLY with the completed JSON."""
    else:
        system_msg = "Tu es un expert PowerPoint. Reponds UNIQUEMENT avec du JSON valide, sans texte supplementaire."
        lang_note = "Tous les textes doivent etre en FRANCAIS."
        prompt = f"""Remplis les bullets de chaque slide de cette presentation PowerPoint.
Les TITRES des slides sont FIXES — ne les change PAS.
Remplis uniquement les tableaux "bullets" avec 3 a 5 points pertinents extraits du README.
{lang_note}

REGLES : {rules}

README (source d information) :
{cleaned_readme}

JSON a completer (garde les titres exacts, remplis seulement les bullets et le titre principal) :
{skeleton}

Reponds UNIQUEMENT avec le JSON complete."""

    response = groq_client.chat.completions.create(
        model="anthropic/claude-haiku-4-5",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.2
    )

    raw_text = response.choices[0].message.content
    logger.info("LLM response received (%d chars)", len(raw_text))

    json_str = _extract_json_block(raw_text)
    plan = json.loads(json_str)
    return _validate_and_normalize(plan)


def parser_agent(state: dict) -> dict:
    readme_content = state.get("readme_content", "")
    lang = state.get("lang", "auto")
    audience = state.get("audience", "developer")

    if not USE_LLM or groq_client is None:
        logger.info("USE_LLM disabled or LLM client not configured. Using Markdown fallback.")
        fallback = _parse_markdown_sections(readme_content, audience)
        return {**state, "slides_plan": fallback}

    try:
        logger.info("Calling LLM API (lang=%s, audience=%s)...", lang, audience)
        plan = _call_llm_api(readme_content, lang, audience)
        logger.info("LLM API returned %d slides.", len(plan["slides"]))
        return {**state, "slides_plan": plan}
    except Exception as e:
        logger.warning("LLM API failed (%s). Falling back to Markdown parser.", e)
        fallback = _parse_markdown_sections(readme_content, audience)
        return {**state, "slides_plan": fallback}
