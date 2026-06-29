import json
import logging
from agents.parser_agent import _validate_and_normalize
from agents.utils import groq_client

logger = logging.getLogger(__name__)

# OpenRouter models — best first, fallback second
_CHAT_MODELS = ["anthropic/claude-sonnet-4-6", "google/gemini-2.5-flash"]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "change_colors",
            "description": (
                "Changer les COULEURS uniquement (rouge, bleu, vert, noir, blanc, hex...). "
                "INTERDIT pour : gras, italique, souligne, police, taille — ce sont des STYLES, pas des couleurs. "
                "Modification GLOBALE sur toutes les slides. "
                "SI l utilisateur cible UNE slide precise → utiliser execute_pptx_code. "
                "REGLES couleur : 'couleur du texte/lettres en X' → text_color + title_color, JAMAIS primary_color. "
                "'couleur du fond en X' → bg_color. 'couleur de la barre/bandeau en X' → primary_color."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "primary_color":  {"type": "array", "items": {"type": "integer"}, "description": "UNIQUEMENT la bande de fond coloree en haut de chaque slide [R,G,B]. NE PAS utiliser pour le texte."},
                    "accent_color":   {"type": "array", "items": {"type": "integer"}, "description": "Couleur accent/decorative [R,G,B]"},
                    "bg_color":       {"type": "array", "items": {"type": "integer"}, "description": "Couleur de fond blanc des slides [R,G,B]"},
                    "text_color":     {"type": "array", "items": {"type": "integer"}, "description": "Couleur du texte des bullets/corps [R,G,B]. Utiliser quand l utilisateur dit 'ecriture', 'texte', 'lettres'."},
                    "title_color":    {"type": "array", "items": {"type": "integer"}, "description": "Couleur du texte des titres de slides [R,G,B]. Utiliser avec text_color quand l utilisateur dit 'ecriture' ou 'texte'."},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_fonts",
            "description": "Changer la police UNIQUEMENT si l'utilisateur demande une police ou typographie",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_font": {"type": "string", "description": "Police du titre (Calibri, Arial, Times New Roman, Georgia...)"},
                    "body_font":  {"type": "string", "description": "Police du corps"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_sizes",
            "description": "Changer la taille du texte UNIQUEMENT si l'utilisateur demande un changement de taille",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_size": {"type": "integer", "description": "Taille titre (ex: 44, 52)"},
                    "body_size":  {"type": "integer", "description": "Taille corps (ex: 14, 17, 20)"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_bullet_style",
            "description": "Changer le caractère des puces",
            "parameters": {
                "type": "object",
                "properties": {
                    "bullet_char": {"type": "string", "description": "Caractere puce : bullet, fleche, coche, etoile, tiret"},
                },
                "required": ["bullet_char"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_title_style",
            "description": (
                "Changer le STYLE d ecriture (gras ou non-gras) des titres et/ou du corps de texte. "
                "Utiliser pour : 'gras', 'bold', 'en gras', 'non gras'. "
                "NE PAS utiliser pour les couleurs — la couleur n est pas un style d ecriture."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title_bold": {"type": "boolean", "description": "Titres en gras (true) ou non (false)"},
                    "body_bold":  {"type": "boolean", "description": "Corps/bullets en gras (true) ou non (false)"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Appliquer un theme complet uniquement si demande explicitement",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "enum": ["dark", "corporate", "minimal", "ocean", "sunset", "forest", "elegant"]}
                },
                "required": ["theme"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_logo_position",
            "description": "Changer la position du logo",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {"type": "string", "enum": ["top-right", "top-left", "bottom-right", "bottom-left"]}
                },
                "required": ["position"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_cover_title",
            "description": (
                "Changer le titre de la slide de COUVERTURE uniquement. "
                "La slide de couverture est la toute premiere slide (slide 1 dans PowerPoint) avec le grand titre centre sur fond colore. "
                "Utiliser SEULEMENT si l utilisateur mentionne explicitement : 'slide 1', 'premiere slide', 'slide de couverture', 'slide de titre', 'titre principal'. "
                "NE PAS utiliser pour les slides 2, 3, 4... — utiliser edit_slide a la place."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Nouveau titre de la slide de couverture"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_slide",
            "description": (
                "Ajouter UNE SEULE slide NOUVELLE avec titre et bullets UNIQUES — jamais copies d une slide existante. "
                "NE JAMAIS appeler delete_slide avant ou apres : l insertion decale automatiquement les slides. "
                "POSITION = NUMERO PPT que la nouvelle slide aura (meme systeme que delete_slide et edit_slide) : "
                "'au debut' → position=2 (la nouvelle slide devient PPT 2). "
                "'avant slide N PPT' → position=N. "
                "'apres slide N PPT' → position=N+1. "
                "'a la fin' / 'en dernier' / sans precision → NE PAS passer position (omettre). "
                "EXEMPLES : 'au debut' → position=2 | 'avant slide 4 PPT' → position=4 | 'apres slide 3 PPT' → position=4 | 'a la fin' → omettre position."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string"},
                    "bullets":  {"type": "array", "items": {"type": "string"}},
                    "position": {"type": "integer", "description": "Numero PPT que la nouvelle slide aura (2=premiere de contenu, 3=deuxieme...). Omettre pour ajouter a la fin."},
                },
                "required": ["title", "bullets"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_slide",
            "description": "Supprimer une slide par son NUMERO PPT (slide 1=couverture, slide 2=premiere de contenu, slide 3=deuxieme de contenu...). NE PAS supprimer slide 1 sauf si explicitement demande.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slide_number": {"type": "integer", "description": "Numero PPT de la slide a supprimer (2=premiere de contenu, 3=deuxieme, etc.)"}
                },
                "required": ["slide_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_slide",
            "description": (
                "Modifier le titre ou les bullets d une slide de CONTENU (toutes les slides sauf la couverture). "
                "NUMEROTATION : slide_number = NUMERO PPT direct (slide 1=couverture, slide 2=premiere de contenu). "
                "Exemples : 'slide 2' → slide_number=2 | 'slide 3' → slide_number=3 | 'slide 4' → slide_number=4. "
                "N envoyer QUE le champ a modifier (title OU bullets), pas les deux sauf si les deux sont demandes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slide_number": {"type": "integer", "description": "Numero PPT direct de la slide (2=premiere de contenu, 3=deuxieme, etc.)"},
                    "title":        {"type": "string",  "description": "Nouveau titre — omettre si non demande"},
                    "bullets":      {"type": "array", "items": {"type": "string"}, "description": "Nouveau contenu — omettre si non demande"},
                },
                "required": ["slide_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reorder_slides",
            "description": "Changer l ordre des slides",
            "parameters": {
                "type": "object",
                "properties": {
                    "order": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["order"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_pptx_code",
            "description": (
                "Executer du code python-pptx pour des modifications ciblant UNE slide precise, ou pour des effets avances. "
                "UTILISER OBLIGATOIREMENT quand l utilisateur mentionne une slide specifique (ex: 'slide 3', 'la deuxieme slide') pour : "
                "changer la couleur du texte/fond, la police, la taille sur CETTE slide seulement. "
                "Aussi pour : italique, souligne, tableaux, notes, formes, alignement, espacement, hyperliens. "
                "NE PAS utiliser pour : ajout/suppression/reordonnancement de slides, themes globaux. "
                "STRUCTURE : "
                "Slide de couverture : prs.slides[0] → shapes[2]=titre, shapes[3]=date. "
                "Slide de contenu N (N>=1) : prs.slides[N] → shapes[4]=titre textbox, shapes[5]=bullets textbox. "
                "Changer couleur texte slide N : for run in prs.slides[N].shapes[5].text_frame.paragraphs[i].runs: run.font.color.rgb = RGBColor(R,G,B). "
                "Changer couleur titre slide N : for run in prs.slides[N].shapes[4].text_frame.paragraphs[0].runs: run.font.color.rgb = RGBColor(R,G,B). "
                "VARIABLES DISPONIBLES : prs, Inches, Pt, RGBColor, PP_ALIGN, enumerate, len, range, int, float, str."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code python-pptx valide utilisant uniquement les variables disponibles listees."
                    }
                },
                "required": ["code"]
            }
        }
    },
]

THEMES = {
    "dark":      {"primary_color": [20,20,30],    "accent_color": [100,200,255], "bg_color": [30,30,45],    "text_color": [220,220,220]},
    "corporate": {"primary_color": [30,58,95],    "accent_color": [249,115,22],  "bg_color": [248,249,255], "text_color": [51,51,68]},
    "minimal":   {"primary_color": [50,50,50],    "accent_color": [200,200,200], "bg_color": [255,255,255], "text_color": [40,40,40]},
    "ocean":     {"primary_color": [0,80,120],    "accent_color": [0,210,180],   "bg_color": [230,245,250], "text_color": [10,50,70]},
    "sunset":    {"primary_color": [180,50,20],   "accent_color": [255,180,0],   "bg_color": [255,245,235], "text_color": [80,30,10]},
    "forest":    {"primary_color": [30,90,50],    "accent_color": [120,200,80],  "bg_color": [240,250,240], "text_color": [20,60,30]},
    "elegant":   {"primary_color": [80,20,100],   "accent_color": [220,180,255], "bg_color": [250,245,255], "text_color": [50,10,70]},
}

BULLET_MAP = {
    "bullet": "•", "fleche": "→", "coche": "✓", "etoile": "★",
    "tiret": "-", "triangle": "▶", "check": "✓", "arrow": "→",
}


def _apply_tool(name, args, slides_plan, design_params):
    import copy
    slides = copy.deepcopy(slides_plan.get("slides", []))

    if name == "change_colors":
        for key in ["primary_color", "accent_color", "bg_color", "text_color", "title_color"]:
            if key in args and args[key]:
                design_params[key] = args[key]

    elif name == "change_fonts":
        for key in ["title_font", "body_font"]:
            if key in args and args[key]:
                design_params[key] = args[key]

    elif name == "change_sizes":
        for key in ["title_size", "body_size"]:
            if key in args and args[key]:
                design_params[key] = int(args[key])

    elif name == "change_bullet_style":
        char = args.get("bullet_char", "•")
        design_params["bullet_char"] = BULLET_MAP.get(char.lower(), char)

    elif name == "change_title_style":
        if "title_bold" in args:
            design_params["title_bold"] = bool(args["title_bold"])
        if "body_bold" in args:
            design_params["body_bold"] = bool(args["body_bold"])

    elif name == "set_theme":
        design_params.update(THEMES.get(args.get("theme", "corporate"), {}))

    elif name == "change_cover_title":
        slides_plan["title"] = args["title"]

    elif name == "change_logo_position":
        design_params["logo_position"] = args["position"]

    elif name == "add_slide":
        new_slide = {"title": args["title"], "bullets": args.get("bullets", [])}
        pos = args.get("position")
        if pos is not None:
            # position = numéro PPT → index contenu = ppt - 2 (cohérent avec delete_slide et edit_slide)
            idx = max(0, int(pos) - 2)
            if idx >= len(slides):
                slides.append(new_slide)
            else:
                slides.insert(idx, new_slide)
        else:
            slides.append(new_slide)

    elif name == "delete_slide":
        # slide_number = numéro PPT → index contenu = ppt - 2
        idx = int(args["slide_number"]) - 2
        if 0 <= idx < len(slides):
            slides.pop(idx)

    elif name == "edit_slide":
        # slide_number = numéro PPT → index contenu = ppt - 2
        idx = int(args["slide_number"]) - 2
        if 0 <= idx < len(slides):
            if args.get("title"):
                slides[idx]["title"] = args["title"]
            if args.get("bullets"):
                slides[idx]["bullets"] = args["bullets"]

    elif name == "reorder_slides":
        # order contient des numéros PPT → convertir en indices contenu
        order = [int(i) - 2 for i in args["order"]]
        slides = [slides[i] for i in order if 0 <= i < len(slides)]

    return {"slides": slides, "title": slides_plan.get("title", "")}, design_params


def chat_agent(state: dict) -> dict:
    if groq_client is None:
        logger.warning("OPENROUTER_API_KEY not set. Chat agent unavailable.")
        return state

    import copy
    slides_plan    = state.get("slides_plan", {})
    instruction    = state.get("instruction", "")
    current_design = copy.deepcopy(state.get("design_params", {}))
    readme_content = state.get("readme_content", "")

    slides = slides_plan.get("slides", [])
    slides_detail = f"\n[{len(slides)} slides de contenu — couverture=PPT1, contenu1=PPT2, contenu2=PPT3...]\n"
    for i, s in enumerate(slides):
        slides_detail += f"\n[Contenu {i+1} / PPT slide {i+2}] {s['title']}\n"
        for b in s.get("bullets", []):
            slides_detail += f"  • {b}\n"

    system_prompt = (
        "Tu es un assistant PowerPoint. Reponds TOUJOURS en appelant un outil — jamais de texte seul.\n\n"
        "NUMEROTATION DES SLIDES — TOUJOURS UTILISER LE NUMERO PPT DIRECT :\n"
        "- Slide 1 = couverture → change_cover_title\n"
        "- Slide 2 = premiere de contenu → edit_slide(slide_number=2)\n"
        "- Slide 3 = deuxieme de contenu → edit_slide(slide_number=3)\n"
        "- Slide N = edit_slide(slide_number=N) — PAS N-1, le numero PPT directement\n\n"
        "CHOIX DE L OUTIL :\n"
        "- Changer titre/contenu slide 1 → change_cover_title\n"
        "- Changer titre/contenu slide 2+ → edit_slide(slide_number=NUMERO_PPT)\n"
        "- Couleur → change_colors\n"
        "- Police → change_fonts\n"
        "- Taille texte → change_sizes\n"
        "- Theme complet → set_theme\n"
        "- Ajouter slide → add_slide (UNE SEULE fois, position=NUMERO_PPT)\n"
        "- Supprimer slide → delete_slide(slide_number=NUMERO_PPT)\n"
        "- Italic, souligne, tableau, note, forme → execute_pptx_code\n\n"
        "REGLE DE PORTEE — CRITIQUE :\n"
        "- L utilisateur mentionne UNE slide precise → modifier SEULEMENT cette slide, aucune autre.\n"
        "- L utilisateur dit 'toutes', 'la presentation', sans numero → modifier globalement.\n"
        "- Pour cibler UNE slide → TOUJOURS utiliser edit_slide ou execute_pptx_code, JAMAIS change_colors.\n"
        "- change_colors = modification GLOBALE de toutes les slides a la fois.\n\n"
        "STYLE vs COULEUR — NE JAMAIS CONFONDRE :\n"
        "- STYLE = gras/bold, italique, souligne, police, taille → JAMAIS change_colors pour ca.\n"
        "- COULEUR = rouge, bleu, vert, noir, blanc, #hex → change_colors ou execute_pptx_code.\n"
        "- 'en gras' / 'bold' → change_title_style(title_bold=True, body_bold=True).\n"
        "- 'titre en gras seulement' → change_title_style(title_bold=True).\n"
        "- 'corps/bullets en gras' → change_title_style(body_bold=True).\n"
        "- 'italique' → execute_pptx_code.\n"
        "- NE JAMAIS appeler change_colors quand l utilisateur parle de gras, italique ou police.\n\n"
        "REGLES COULEURS :\n"
        "- Couleur sur UNE slide precise → execute_pptx_code.\n"
        "- Couleur du texte sur TOUTES les slides → change_colors(text_color + title_color).\n"
        "- primary_color = bande coloree en haut, PAS le texte.\n\n"
        "REGLES ADD_SLIDE :\n"
        "- Appeler add_slide UNE SEULE fois. Ne jamais appeler delete_slide en meme temps.\n"
        "- position = NUMERO PPT que la nouvelle slide aura (meme logique que delete_slide).\n"
        "- 'au debut' → position=2 | 'avant slide N' → position=N | 'apres slide N' → position=N+1 | 'a la fin' → omettre.\n\n"
        "STRUCTURE pour execute_pptx_code :\n"
        "- prs.slides[0] = couverture : shapes[2]=titre\n"
        "- prs.slides[N] = slide contenu N (N>=1) : shapes[4]=titre, shapes[5]=bullets\n"
        "- Note : prs.slides[N].notes_slide.notes_text_frame.text = 'texte'\n"
        "- Italic bullet I : prs.slides[N].shapes[5].text_frame.paragraphs[I].runs[1].font.italic = True\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"README (resume):\n{readme_content[:500]}\n\n"
                f"[SLIDE DE COUVERTURE] Titre actuel: {slides_plan.get('title', '')}\n"
                f"Slides de contenu [{len(slides)} au total — slide 2 a {len(slides)+1} dans PowerPoint]:{slides_detail}\n"
                f"Design actuel: {json.dumps(current_design)}\n\n"
                f"Instruction: {instruction}"
            )
        }
    ]

    try:
        response = None
        for model in _CHAT_MODELS:
            try:
                response = groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="required",
                    max_tokens=1000,
                    temperature=0.0,
                )
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate" in err_str or "429" in err_str:
                    logger.warning("Rate limit sur %s, fallback vers modèle suivant.", model)
                    if model == _CHAT_MODELS[-1]:
                        raise
                    continue
                raise

        tool_calls = response.choices[0].message.tool_calls or []  # type: ignore[union-attr]
        logger.info("Tools appelés: %s", [tc.function.name for tc in tool_calls])

        if not tool_calls:
            logger.warning("LLM n'a appelé aucun outil pour: %s", instruction)
            return {**state, "chat_actions": []}

        import copy
        new_plan   = {"slides": copy.deepcopy(slides_plan.get("slides", [])), "title": slides_plan.get("title", "")}
        new_design = copy.deepcopy(current_design)
        actions    = []
        pptx_codes = [state["pptx_code"]] if state.get("pptx_code") else []

        STRUCTURAL_TOOLS = {"add_slide", "delete_slide", "reorder_slides"}
        if any(tc.function.name in STRUCTURAL_TOOLS for tc in tool_calls):
            pptx_codes = []

        for tc in tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            if name == "execute_pptx_code":
                code = args.get("code", "").strip()
                if code:
                    pptx_codes.append(code)
            else:
                new_plan, new_design = _apply_tool(name, args, new_plan, new_design)
            actions.append(name)

        new_plan = _validate_and_normalize(new_plan)
        accumulated_code = "\n# ---BLOCK---\n".join(pptx_codes) if pptx_codes else None
        return {
            **state,
            "slides_plan":   new_plan,
            "design_params": new_design,
            "chat_actions":  actions,
            "pptx_code":     accumulated_code,
        }

    except Exception as e:
        logger.warning("Chat agent failed: %s", e)
        return {**state, "chat_actions": [], "chat_error": str(e)}
