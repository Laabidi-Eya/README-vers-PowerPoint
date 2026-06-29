from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from graph.pipeline import build_graph
from agents.chat_agent import chat_agent
from agents.branding_agent import branding_agent
from agents.pptx_agent import pptx_agent
from dotenv import load_dotenv
import zipfile
import uuid
import os
import json
from datetime import datetime

load_dotenv()

app = FastAPI()
sessions = {}  # session_id -> state

SESSIONS_FILE = os.path.join("output", "sessions.json")


def _session_to_json(session: dict) -> dict:
    """Garde uniquement les champs JSON-sérialisables."""
    return {
        "slides_plan":     session.get("slides_plan", {}),
        "readme_content":  session.get("readme_content", ""),
        "lang":            session.get("lang", "fr"),
        "audience":        session.get("audience", "developer"),
        "logo_path":       session.get("logo_path"),
        "design_params":   session.get("design_params", {}),
        "pptx_code":       session.get("pptx_code"),
        "output_path":     session.get("output_path", ""),
        "is_zip":          session.get("is_zip", False),
        "effective_colors": session.get("effective_colors", {}),
        "title":           session.get("slides_plan", {}).get("title", "Présentation"),
        "created_at":      session.get("created_at", datetime.now().isoformat()),
    }


def save_sessions():
    try:
        os.makedirs("output", exist_ok=True)
        data = {sid: _session_to_json(s) for sid, s in sessions.items()}
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("save_sessions failed: %s", e)


def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sid, s in data.items():
            # Ne restaure que les sessions dont le fichier existe encore
            if s.get("output_path") and os.path.exists(s["output_path"]):
                sessions[sid] = s
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("load_sessions failed: %s", e)


load_sessions()

HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>README to PowerPoint — OmnIA</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

        /* ── Reset & Base ── */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-weight: 400;
            font-size: 14px;
            line-height: 1.5;
            background: #EFF1F5;
            color: #0F1D33;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #EFF1F5; }
        ::-webkit-scrollbar-thumb { background: #D5D8DE; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #354A6B; }

        @keyframes fadeSlideUp {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideWrapFade {
            from { opacity: 0; transform: translateX(14px); }
            to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes progress {
            0% { width: 0%; }
            60% { width: 75%; }
            100% { width: 92%; }
        }
        @keyframes blink { 0%,80%,100%{opacity:.15} 40%{opacity:1} }
        @keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.4} }

        .source-locked { opacity: 0.3; pointer-events: none; user-select: none; transition: opacity 0.3s; }

        /* ── Layout principal ── */
        .app-layout { display: flex; height: 100vh; overflow: hidden; }

        /* ── Sidebar ── */
        .sidebar {
            width: 260px;
            flex-shrink: 0;
            background: #0F1D33;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow-y: auto;
        }
        .sidebar-logo {
            height: 52px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 16px;
            border-bottom: 1px solid rgba(255,255,255,0.07);
            flex-shrink: 0;
        }
        .sidebar-logo-text { font-size: 18px; font-weight: 900; color: white; letter-spacing: -0.3px; }
        .sidebar-section-label {
            font-size: 10px;
            font-weight: 700;
            color: rgba(255,255,255,0.3);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 16px 16px 6px;
        }
        .sidebar-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            margin: 1px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 400;
            color: #AABFC2;
            transition: all 0.15s;
            text-decoration: none;
            border: none;
            background: none;
            width: calc(100% - 16px);
            text-align: left;
            font-family: inherit;
        }
        .sidebar-item:hover { background: #1B2A4A; color: white; }
        .sidebar-item.active { background: #1B2A4A; color: white; font-weight: 500; }
        .sidebar-divider { height: 1px; background: rgba(255,255,255,0.07); margin: 8px 16px; }
        .sidebar-history-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 7px 12px;
            margin: 1px 8px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.15s;
        }
        .sidebar-history-item:hover { background: #1B2A4A; }
        .sidebar-history-item .h-title {
            font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.75);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;
        }
        .sidebar-history-item .h-time { font-size: 10px; color: rgba(255,255,255,0.3); white-space: nowrap; }
        .sidebar-dl-btn {
            padding: 3px 8px; border-radius: 4px;
            background: rgba(170,191,194,0.12); border: 1px solid rgba(170,191,194,0.2);
            color: #AABFC2; font-size: 11px; font-weight: 600;
            text-decoration: none; flex-shrink: 0; transition: all 0.15s;
        }
        .sidebar-dl-btn:hover { background: rgba(170,191,194,0.22); color: white; }
        .hist-dl-btn {
            color: rgba(255,255,255,0.4); font-size: 13px; text-decoration: none;
            flex-shrink: 0; padding: 3px 5px; border-radius: 4px; transition: color 0.15s;
        }
        .hist-dl-btn:hover { color: #F97316; }
        .hist-del-btn {
            background: none; border: none; cursor: pointer; color: rgba(255,255,255,0.3);
            font-size: 13px; padding: 3px 5px; border-radius: 4px; flex-shrink: 0;
            font-family: inherit; transition: color 0.15s;
        }
        .hist-del-btn:hover { color: #E53E3E; }
        .result-del-btn {
            background: none; border: 1px solid #D5D8DE; cursor: pointer; color: #A0ABBD;
            font-size: 13px; padding: 6px 10px; border-radius: 8px; font-family: inherit;
            transition: all 0.15s; flex-shrink: 0;
        }
        .result-del-btn:hover { background: #FFF0F0; border-color: #E53E3E; color: #E53E3E; }
        .sidebar-clear-btn {
            background: none; border: none; color: rgba(255,255,255,0.25);
            font-size: 11px; cursor: pointer; font-family: inherit;
            padding: 2px 8px; border-radius: 4px; margin: 0 8px 8px;
            transition: color 0.15s; text-align: left;
        }
        .sidebar-clear-btn:hover { color: #B91C1C; }

        /* ── Main content ── */
        .main-content {
            flex: 1;
            min-width: 0;
            height: 100vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }

        /* ── Page header navy ── */
        .page-header {
            background: #0F1D33;
            padding: 18px 28px;
            flex-shrink: 0;
        }
        .page-header-inner { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
        .page-header-title { font-size: 22px; font-weight: 900; color: white; letter-spacing: -0.5px; }
        .page-header-title span { color: #AABFC2; }
        .page-header-sub { font-size: 12px; font-weight: 300; color: rgba(255,255,255,0.5); margin-top: 2px; }
        .stat-boxes { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
        .stat-box {
            background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px; padding: 6px 12px; text-align: center; min-width: 56px;
        }
        .stat-box-num { font-size: 15px; font-weight: 900; color: white; line-height: 1; }
        .stat-box-label { font-size: 9px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; color: rgba(255,255,255,0.5); margin-top: 2px; }

        /* ── Tab bar ── */
        .tab-bar-wrap { padding: 16px 28px 0; background: #EFF1F5; }
        .tab-bar {
            background: white; border-radius: 10px; border: 1px solid #D5D8DE;
            padding: 4px; display: inline-flex; gap: 2px; box-shadow: 0 1px 3px rgba(15,29,51,0.06);
        }
        .tab-btn {
            padding: 9px 16px; border-radius: 6px; border: none; cursor: pointer;
            font-family: inherit; font-size: 13px; font-weight: 400;
            color: #4A5568; background: none; transition: all 0.15s;
            display: flex; align-items: center; gap: 6px;
        }
        .tab-btn:hover { background: #EFF1F5; color: #0F1D33; }
        .tab-btn.active { font-size: 14px; font-weight: 700; background: #0F1D33; color: white; box-shadow: 0 1px 3px rgba(15,29,51,0.15); }

        /* ── Page body ── */
        .page-body { padding: 20px 28px; flex: 1; }

        /* ── Card ── */
        .card {
            background: white;
            border: 1px solid #D5D8DE;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 16px;
        }
        .card-header {
            background: #0F1D33;
            padding: 10px 16px;
        }
        .card-header-title { font-size: 13px; font-weight: 700; color: white; letter-spacing: -0.1px; }
        .card-body { padding: 20px; }

        /* ── Upload zones ── */
        .upload-area {
            border: 2px dashed #D5D8DE;
            border-radius: 8px;
            padding: 28px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: #EFF1F5;
            position: relative;
            margin-bottom: 16px;
        }
        .upload-area:hover { border-color: #354A6B; background: #E4E6EC; }
        .upload-area.drag-over {
            border-color: #0F1D33; border-style: solid;
            background: #E4E6EC;
            box-shadow: 0 0 0 3px rgba(15,29,51,0.08);
        }
        .upload-area.drag-over .upload-icon { transform: scale(1.2) translateY(-3px); }
        .upload-area input { display: none; }
        .upload-icon { font-size: 32px; margin-bottom: 8px; transition: transform 0.2s; display: block; }
        .upload-area .label-text { color: #4A5568; font-size: 13px; }
        .upload-area .label-text span { color: #1D4ED8; font-weight: 600; }
        .upload-area .hint { color: #A0ABBD; font-size: 11px; margin-top: 4px; }

        .filename-badge {
            display: none;
            margin-top: 10px;
            background: #E6F4EE; border: 1px solid rgba(11,122,62,0.3);
            color: #0B7A3E; font-size: 12px; font-weight: 600;
            padding: 4px 12px; border-radius: 4px; display: inline-flex; align-items: center; gap: 6px;
        }

        /* ── OR divider ── */
        .or-divider { display: flex; align-items: center; gap: 12px; margin: 0 0 16px; }
        .or-divider hr { flex: 1; border: none; border-top: 1px solid #D5D8DE; }
        .or-divider span { color: #A0ABBD; font-size: 11px; font-weight: 600; letter-spacing: 1px; }

        /* ── GitHub import ── */
        .github-import {
            border: 1px solid #D5D8DE; border-radius: 8px;
            padding: 14px 16px; margin-bottom: 16px;
            background: #EFF1F5; transition: border-color 0.2s, background 0.2s;
        }
        .github-import:focus-within { border-color: #354A6B; background: white; }
        .github-import-label { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
        .github-import-label span { color: #354A6B; font-size: 12px; font-weight: 600; }
        .github-input-row {
            display: flex; align-items: center; gap: 8px;
            background: white; border: 1px solid #D5D8DE; border-radius: 6px; padding: 7px 12px;
        }
        .github-prefix { color: #A0ABBD; font-size: 12px; white-space: nowrap; }
        .github-input {
            flex: 1; min-width: 0; background: transparent; border: none;
            color: #0F1D33; font-size: 13px; font-family: inherit; outline: none;
        }
        .github-input::placeholder { color: #A0ABBD; }
        .github-fetch-btn {
            padding: 6px 14px; background: #0F1D33;
            color: white; border: none; border-radius: 6px;
            font-size: 12px; font-weight: 700; cursor: pointer;
            font-family: inherit; white-space: nowrap; transition: background 0.15s;
        }
        .github-fetch-btn:hover:not(:disabled) { background: #1B2A4A; }
        .github-fetch-btn:disabled { opacity: 0.45; cursor: not-allowed; }
        .github-badge {
            display: none; background: #E6F4EE; border: 1px solid rgba(11,122,62,0.3);
            color: #0B7A3E; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 4px;
        }
        .github-error { display: none; color: #B91C1C; font-size: 12px; margin-top: 6px; }

        /* ── Bouton principal ── */
        .btn-generate {
            width: 100%; padding: 13px;
            background: #0F1D33; color: white; border: none;
            border-radius: 6px; font-size: 14px; font-weight: 700;
            cursor: pointer; transition: background 0.15s; font-family: inherit;
        }
        .btn-generate:hover:not(:disabled) { background: #1B2A4A; }
        .btn-generate:disabled { background: #D5D8DE; color: #A0ABBD; cursor: not-allowed; }

        /* ── Progress bar ── */
        .progress-bar {
            display: none; margin-top: 14px;
            background: #E4E6EC; border-radius: 4px; height: 4px; overflow: hidden;
        }
        .progress-fill {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, #0F1D33, #354A6B);
            border-radius: 4px; animation: progress 2.5s ease-in-out forwards;
        }

        /* ── Status ── */
        .status {
            margin-top: 12px; font-size: 13px; text-align: center;
            color: #4A5568; min-height: 18px;
        }

        /* ── Download box ── */
        .download-box {
            display: none; margin-top: 16px;
            background: white; border: 1px solid #D5D8DE;
            border-radius: 8px; overflow: hidden;
            animation: fadeSlideUp 0.4s ease forwards;
        }
        .download-box-header { background: #0F1D33; padding: 10px 16px; }
        .download-box-header span { font-size: 13px; font-weight: 700; color: white; }
        .dl-card { display: flex; align-items: center; gap: 14px; padding: 16px; }
        .dl-icon {
            width: 44px; height: 44px; flex-shrink: 0;
            background: #EFF1F5; border: 1px solid #D5D8DE;
            border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 22px;
        }
        .dl-info { flex: 1; min-width: 0; }
        .dl-info-name { color: #0F1D33; font-weight: 700; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .dl-info-sub { color: #A0ABBD; font-size: 11px; margin-top: 2px; }
        .dl-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        .btn-preview-small {
            height: 36px; padding: 0 14px; border-radius: 6px;
            border: 1px solid #D5D8DE; background: white; color: #354A6B;
            font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
            display: flex; align-items: center; gap: 6px; transition: all 0.15s;
        }
        .btn-preview-small:hover { background: #EFF1F5; border-color: #354A6B; color: #0F1D33; }
        .btn-download {
            height: 36px; padding: 0 18px; border-radius: 6px;
            background: #0F1D33; color: white; border: none;
            font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit;
            text-decoration: none; display: inline-flex; align-items: center; gap: 6px;
            transition: background 0.15s;
        }
        .btn-download:hover { background: #1B2A4A; }

        /* ── Séparateur IA ── */
        .ai-divider {
            display: flex; align-items: center; gap: 14px; margin: 24px 0 16px;
        }
        .ai-divider hr { flex: 1; border: none; border-top: 1px solid #D5D8DE; }
        .ai-divider-badge {
            display: inline-flex; align-items: center; gap: 6px;
            background: #EFF1F5; border: 1px solid #D5D8DE;
            border-radius: 20px; padding: 5px 14px;
        }
        .ai-divider-badge span { color: #354A6B; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }

        /* ── Chat panel redesign ── */
        #panel-chat { display: flex; flex-direction: column; height: calc(100vh - 160px); min-height: 500px; }
        .chat-wrap {
            display: flex; flex-direction: column; flex: 1; overflow: hidden;
            background: white; border: 1px solid #D5D8DE; border-radius: 14px;
            box-shadow: 0 4px 24px rgba(15,29,51,0.09);
        }
        /* topbar */
        .chat-topbar {
            display: flex; align-items: center; gap: 12px;
            padding: 14px 20px; background: #0F1D33; flex-shrink: 0;
            border-radius: 14px 14px 0 0;
        }
        .chat-topbar-icon {
            width: 36px; height: 36px; border-radius: 10px;
            background: linear-gradient(135deg,#F97316,#ea580c);
            display: flex; align-items: center; justify-content: center;
            font-size: 17px; flex-shrink: 0;
        }
        .chat-topbar-info { flex: 1; }
        .chat-topbar-title { font-size: 14px; font-weight: 700; color: white; }
        .chat-topbar-sub { font-size: 11px; color: rgba(255,255,255,0.38); margin-top: 1px; }
        .chat-online-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: #22c55e; flex-shrink: 0;
            box-shadow: 0 0 0 2px rgba(34,197,94,0.3);
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%,100% { box-shadow: 0 0 0 2px rgba(34,197,94,0.3); }
            50%      { box-shadow: 0 0 0 5px rgba(34,197,94,0.1); }
        }
        /* messages area */
        #chat-messages {
            flex: 1; overflow-y: auto; padding: 20px 20px 12px;
            display: flex; flex-direction: column; gap: 12px;
            background: #F6F8FC;
            scrollbar-width: thin; scrollbar-color: #D5D8DE transparent;
        }
        #chat-messages::-webkit-scrollbar { width: 4px; }
        #chat-messages::-webkit-scrollbar-thumb { background: #D5D8DE; border-radius: 4px; }
        /* empty state */
        .chat-empty-state {
            flex: 1; display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            gap: 6px; text-align: center; padding: 40px 24px; margin: auto;
        }
        .chat-empty-icon { font-size: 44px; margin-bottom: 6px; }
        .chat-empty-title { font-size: 15px; font-weight: 700; color: #1E3A5F; }
        .chat-empty-sub { font-size: 12px; color: #8896A7; line-height: 1.7; max-width: 280px; }
        .chat-suggestions {
            display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 14px;
        }
        .chat-suggestion-chip {
            padding: 7px 15px; background: white; border: 1px solid #D5D8DE;
            border-radius: 20px; font-size: 12px; color: #354A6B; font-weight: 500;
            cursor: pointer; transition: all 0.15s; font-family: inherit;
        }
        .chat-suggestion-chip:hover { background: #0F1D33; color: white; border-color: #0F1D33; }
        /* input zone */
        #chat-input-bar {
            padding: 12px 16px; background: white; flex-shrink: 0;
            border-top: 1px solid #E8EAF0; border-radius: 0 0 14px 14px;
        }
        .chat-input-inner {
            display: flex; align-items: center; gap: 10px;
            background: #F0F2F7; border-radius: 12px; padding: 8px 8px 8px 16px;
            border: 2px solid transparent; transition: border-color 0.2s, background 0.2s;
        }
        .chat-input-inner:focus-within { border-color: #0F1D33; background: white; }
        #chat-input {
            flex: 1; background: transparent; border: none; outline: none;
            color: #0F1D33; font-size: 13px; font-family: inherit; padding: 4px 0;
        }
        #chat-input::placeholder { color: #A0ABBD; }
        .chat-send-btn {
            width: 36px; height: 36px; flex-shrink: 0;
            background: #0F1D33; color: white; border: none; border-radius: 9px;
            font-size: 16px; cursor: pointer; display: flex; align-items: center;
            justify-content: center; transition: background 0.15s, transform 0.1s;
        }
        .chat-send-btn:hover { background: #F97316; transform: scale(1.05); }
        .chat-send-btn:disabled { background: #D5D8DE; cursor: not-allowed; transform: none; }

        /* ── Bulles chat ── */
        .typing-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #8896A7; animation: bounce-dot 1.2s ease-in-out infinite; }
        .typing-dot:nth-child(2) { animation-delay: .18s; }
        .typing-dot:nth-child(3) { animation-delay: .36s; }
        @keyframes bounce-dot { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)} }
        .bubble-row { display: flex; align-items: flex-end; gap: 8px; }
        .bubble-row.user-row { flex-direction: row-reverse; }
        .bubble-avatar {
            width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 13px;
        }
        .bubble-avatar.ai-av { background: linear-gradient(135deg,#0F1D33,#1B2A4A); color: white; }
        .bubble-avatar.user-av { background: linear-gradient(135deg,#F97316,#ea580c); color: white; }
        .bubble-user {
            background: linear-gradient(135deg,#0F1D33,#1B2A4A); color: white;
            padding: 10px 15px; border-radius: 14px 14px 4px 14px;
            font-size: 13px; max-width: 75%; line-height: 1.5;
            box-shadow: 0 2px 8px rgba(15,29,51,0.15);
        }
        .bubble-ai {
            background: white; border: 1px solid #E8EAF0; color: #1E3A5F;
            padding: 11px 15px; border-radius: 14px 14px 14px 4px;
            font-size: 13px; max-width: 80%; line-height: 1.6;
            box-shadow: 0 2px 6px rgba(15,29,51,0.06);
        }
        .bubble-ai-success {
            background: white; border: 1px solid #BBF7D0;
            padding: 13px 16px; border-radius: 14px 14px 14px 4px; max-width: 80%;
            box-shadow: 0 2px 6px rgba(15,29,51,0.06);
        }
        .bubble-error {
            background: #FEF2F2; border: 1px solid #FECACA;
            padding: 11px 15px; border-radius: 14px 14px 14px 4px;
            max-width: 80%; color: #B91C1C; font-size: 13px;
            box-shadow: 0 2px 6px rgba(185,28,28,0.08);
        }
        .bubble-typing {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 12px 16px;
            background: white; border: 1px solid #E8EAF0;
            border-radius: 14px 14px 14px 4px;
            box-shadow: 0 2px 6px rgba(15,29,51,0.06);
        }

        /* ── Modal overlay ── */
        .modal-overlay {
            display: none; position: fixed; inset: 0;
            background: rgba(15,29,51,0.6); backdrop-filter: blur(4px);
            z-index: 100; align-items: center; justify-content: center;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: white; border: 1px solid #D5D8DE;
            border-radius: 8px; overflow: hidden; width: 400px;
            animation: fadeSlideUp 0.3s ease forwards;
            box-shadow: 0 20px 60px rgba(15,29,51,0.2);
        }
        .modal-head { background: #0F1D33; padding: 14px 18px; }
        .modal-head h2 { color: white; font-size: 15px; font-weight: 700; }
        .modal-head p { color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 2px; }
        .modal-body { padding: 16px; display: flex; flex-direction: column; gap: 8px; }
        .lang-btn {
            padding: 13px 16px; border-radius: 6px;
            border: 1px solid #D5D8DE; background: #EFF1F5;
            color: #0F1D33; font-size: 13px; font-weight: 500;
            font-family: inherit; cursor: pointer; transition: all 0.15s;
            display: flex; align-items: center; gap: 10px;
        }
        .lang-btn:hover { background: #E4E6EC; border-color: #354A6B; }
        .modal-cancel {
            margin: 0 16px 14px; background: none; border: none;
            color: #A0ABBD; font-size: 12px; cursor: pointer; font-family: inherit;
            text-align: center; display: block; transition: color 0.15s;
        }
        .modal-cancel:hover { color: #4A5568; }

        /* ── Score modal ── */
        .score-overlay {
            display: none; position: fixed; inset: 0;
            background: rgba(15,29,51,0.6); backdrop-filter: blur(4px);
            z-index: 300; align-items: center; justify-content: center;
        }
        .score-overlay.show { display: flex; }
        .score-modal {
            width: 90%; max-width: 480px; background: white;
            border: 1px solid #D5D8DE; border-radius: 8px; overflow: hidden;
            animation: fadeSlideUp 0.3s ease forwards;
            box-shadow: 0 20px 60px rgba(15,29,51,0.2);
        }
        .score-modal-header {
            background: #0F1D33; padding: 14px 18px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .score-modal-title { color: white; font-weight: 700; font-size: 14px; }
        .close-btn {
            background: none; border: none; color: rgba(255,255,255,0.4);
            font-size: 20px; cursor: pointer; line-height: 1; padding: 0 3px;
            transition: color 0.15s;
        }
        .close-btn:hover { color: white; }
        .sp-yes {
            padding: 9px 22px; border-radius: 6px; background: #0F1D33;
            color: white; border: none; font-size: 13px; font-weight: 700;
            cursor: pointer; font-family: inherit; transition: background 0.15s;
        }
        .sp-yes:hover { background: #1B2A4A; }
        .sp-no {
            padding: 9px 18px; border-radius: 6px;
            background: #EFF1F5; border: 1px solid #D5D8DE;
            color: #4A5568; font-size: 13px; font-weight: 500;
            cursor: pointer; font-family: inherit; transition: all 0.15s;
        }
        .sp-no:hover { background: #E4E6EC; color: #0F1D33; }
        .score-circle {
            width: 64px; height: 64px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 15px; font-weight: 800; flex-shrink: 0;
            transition: all 0.3s;
        }
        .sc-loading  { background: #EFF1F5; border: 2px solid #D5D8DE; color: #A0ABBD; }
        .sc-excellent{ background: #E6F4EE; border: 2px solid rgba(11,122,62,0.4); color: #0B7A3E; }
        .sc-bon      { background: #FEF3C7; border: 2px solid rgba(180,83,9,0.4); color: #B45309; }
        .sc-moyen    { background: #FEF3C7; border: 2px solid rgba(180,83,9,0.3); color: #B45309; }
        .sc-faible   { background: #FEE2E2; border: 2px solid rgba(185,28,28,0.4); color: #B91C1C; }

        /* ── Preview modal ── */
        .preview-overlay {
            display: none; position: fixed; inset: 0;
            background: rgba(15,29,51,0.6); backdrop-filter: blur(4px);
            z-index: 200; align-items: center; justify-content: center;
        }
        .preview-overlay.show { display: flex; }
        .preview-modal {
            width: 90%; max-width: 820px; background: white;
            border: 1px solid #D5D8DE; border-radius: 8px; overflow: hidden;
            box-shadow: 0 20px 60px rgba(15,29,51,0.2);
            animation: fadeSlideUp 0.3s ease forwards;
        }
        .preview-header {
            background: #0F1D33; padding: 14px 18px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .preview-header-title { color: white; font-weight: 700; font-size: 14px; }
        /* ── Slide visuelle (reproduit fidèlement le PPTX généré) ── */
        .preview-slide-wrap {
            padding: 28px 32px; background: #2a2a3a;
            display: flex; align-items: center; justify-content: center;
        }
        .preview-slide-wrap.slide-animate { animation: slideWrapFade 0.2s ease forwards; }
        .slide-card-sm { box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; }
        .slide-card {
            width: 100%;
            background: #F8F9FF;
            border-radius: 3px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.5);
            overflow: hidden;
            aspect-ratio: 10/7.5;
            display: flex; flex-direction: column;
            position: relative;
        }
        /* Bande accent gauche */
        .slide-card::before {
            content: ''; position: absolute; left: 0; top: 0;
            width: 7px; height: 100%; background: #F97316; z-index: 2;
        }
        .slide-card-header {
            background: #1E3A5F;
            padding: 14px 20px 14px 22px;
            flex-shrink: 0; position: relative;
        }
        /* Bande accent bas du header */
        .slide-card-header::after {
            content: ''; position: absolute; bottom: 0; left: 0;
            width: 100%; height: 3px; background: #F97316;
        }
        .slide-card-num {
            font-size: 9px; font-weight: 700; color: rgba(204,221,255,0.6);
            letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px;
        }
        .preview-slide-title {
            font-size: clamp(14px, 2.2vw, 22px); font-weight: 700;
            color: white; line-height: 1.2;
        }
        .slide-card-body {
            flex: 1; padding: 14px 20px 14px 22px; overflow: hidden;
            display: flex; flex-direction: column; justify-content: center;
            border-left: 4px solid #F97316;
        }
        .preview-slide-bullets { list-style: none; display: flex; flex-direction: column; gap: 8px; }
        .preview-slide-bullets li {
            display: flex; align-items: flex-start; gap: 9px;
            color: #333344; font-size: clamp(10px, 1.4vw, 14px); line-height: 1.5;
        }
        .preview-slide-bullets li::before {
            content: '▶'; flex-shrink: 0;
            color: #F97316; font-size: 8px; margin-top: 3px;
        }
        .preview-footer {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 18px; border-top: 1px solid #D5D8DE; background: #EFF1F5;
        }
        .preview-nav { display: flex; align-items: center; gap: 10px; }
        .preview-nav-btn {
            width: 32px; height: 32px; border-radius: 6px;
            border: 1px solid #D5D8DE; background: white; color: #0F1D33;
            font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;
            transition: all 0.15s;
        }
        .preview-nav-btn:hover:not(:disabled) { background: #0F1D33; color: white; border-color: #0F1D33; }
        .preview-nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }
        .preview-counter { color: #A0ABBD; font-size: 12px; font-weight: 600; min-width: 44px; text-align: center; }
        .btn-edit-preview {
            height: 34px; padding: 0 14px; border-radius: 6px;
            border: 1px solid #D5D8DE; background: white; color: #354A6B;
            font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
            display: flex; align-items: center; gap: 6px; transition: all 0.15s;
        }
        .btn-edit-preview:hover { background: #EFF1F5; border-color: #0F1D33; color: #0F1D33; }
        .btn-dl-preview {
            height: 34px; padding: 0 16px; border-radius: 6px;
            background: #0F1D33; color: white; border: none;
            font-size: 12px; font-weight: 700; cursor: pointer; font-family: inherit;
            text-decoration: none; display: inline-flex; align-items: center; gap: 6px;
            transition: background 0.15s;
        }
        .btn-dl-preview:hover { background: #1B2A4A; }

        /* ── Header controls ── */
        .header-controls { display: flex; align-items: center; gap: 12px; }

        /* Toggle dark/light */
        .theme-toggle { display: flex; align-items: center; gap: 9px; cursor: pointer; }
        .theme-toggle-icon { font-size: 17px; line-height: 1; }
        .theme-switch {
            width: 44px; height: 24px; border-radius: 24px;
            background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);
            position: relative; cursor: pointer; transition: background 0.25s;
            flex-shrink: 0;
        }
        .theme-switch::after {
            content: ''; position: absolute; top: 3px; left: 3px;
            width: 18px; height: 18px; border-radius: 50%;
            background: white; transition: transform 0.25s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        body.dark .theme-switch { background: rgba(170,191,194,0.3); }
        body.dark .theme-switch::after { transform: translateX(20px); }

        /* Lang pill */
        .lang-pill {
            display: flex; border-radius: 6px; overflow: hidden;
            border: 1px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.2);
        }
        .lang-pill-opt {
            padding: 6px 14px; font-size: 13px; font-weight: 700;
            color: rgba(255,255,255,0.4); cursor: pointer; transition: all 0.15s;
            border: none; background: none; font-family: inherit; letter-spacing: 0.5px;
        }
        .lang-pill-opt.active { background: rgba(255,255,255,0.15); color: white; }

        /* ── Inline preview bullets ── */
        #inline-slide-bullets li { display:flex; align-items:flex-start; gap:10px; color:#4A5568; font-size:13px; line-height:1.6; }
        #inline-slide-bullets li::before { content:''; flex-shrink:0; margin-top:7px; width:5px; height:5px; border-radius:50%; background:#0F1D33; }
        body.dark #inline-slide-title { color:white; }
        body.dark #inline-slide-bullets li { color:rgba(255,255,255,0.7); }
        body.dark #inline-slide-bullets li::before { background:#AABFC2; }

        /* ── Dark mode ── */
        body.dark { background: #101820; color: #E4E6EC; }
        body.dark .sidebar { background: #070E16; border-right: 1px solid #1B2A4A; }
        body.dark .sidebar-section-label { color: rgba(255,255,255,0.2); }
        body.dark .sidebar-item { color: rgba(255,255,255,0.45); }
        body.dark .sidebar-item:hover, body.dark .sidebar-item.active { background: #0F1D33; color: white; }
        body.dark .sidebar-divider { background: #1B2A4A; }
        body.dark .sidebar-history-item:hover { background: #0F1D33; }
        body.dark .sidebar-history-item .h-title { color: rgba(255,255,255,0.7); }
        body.dark .sidebar-history-item .h-time { color: rgba(255,255,255,0.25); }
        body.dark .sidebar-clear-btn { color: rgba(255,255,255,0.2); }
        body.dark .main-content { background: #101820; }
        body.dark .page-header { background: #070E16; border-bottom: 1px solid #1B2A4A; }
        body.dark .tab-bar-wrap { background: #101820; }
        body.dark .tab-bar { background: #1B2A4A; border-color: #354A6B; }
        body.dark .tab-btn { color: rgba(255,255,255,0.45); }
        body.dark .tab-btn:hover { background: #0F1D33; color: white; }
        body.dark .tab-btn.active { background: #EFF1F5; color: #0F1D33; }
        body.dark .page-body { background: #101820; }
        body.dark .card { background: #1B2A4A; border-color: #354A6B; }
        body.dark .card-header { background: #070E16; }
        body.dark .upload-area { background: #0F1D33; border-color: #354A6B; }
        body.dark .upload-area:hover { background: #1B2A4A; border-color: #AABFC2; }
        body.dark .upload-area .label-text { color: rgba(255,255,255,0.6); }
        body.dark .upload-area .hint { color: rgba(255,255,255,0.25); }
        body.dark .or-divider hr { border-top-color: #354A6B; }
        body.dark .or-divider span { color: rgba(255,255,255,0.25); }
        body.dark .github-import { background: #0F1D33; border-color: #354A6B; }
        body.dark .github-import:focus-within { background: #1B2A4A; }
        body.dark .github-import-label span { color: #AABFC2; }
        body.dark .github-input-row { background: #070E16; border-color: #354A6B; }
        body.dark .github-input { color: white; }
        body.dark .github-input::placeholder { color: rgba(255,255,255,0.2); }
        body.dark .btn-generate { background: #354A6B; }
        body.dark .btn-generate:hover:not(:disabled) { background: #AABFC2; color: #0F1D33; }
        body.dark .progress-bar { background: #1B2A4A; }
        body.dark .status { color: rgba(255,255,255,0.45); }
        body.dark .download-box { background: #1B2A4A; border-color: #354A6B; }
        body.dark .dl-icon { background: #0F1D33; border-color: #354A6B; }
        body.dark .dl-info-name { color: white; }
        body.dark .btn-preview-small { background: #0F1D33; border-color: #354A6B; color: #AABFC2; }
        body.dark .chat-wrap { background: #1B2A4A; border-color: #354A6B; }
        body.dark #chat-messages { background: #0F1D33; }
        body.dark #chat-input-bar { background: #1B2A4A; border-top-color: #354A6B; }
        body.dark .chat-input-inner { background: #0F1D33; }
        body.dark .chat-input-inner:focus-within { background: #1B2A4A; border-color: #F97316; }
        body.dark #chat-input { color: white; }
        body.dark #chat-input::placeholder { color: rgba(255,255,255,0.25); }
        body.dark .bubble-ai { background: #1B2A4A; border-color: #354A6B; color: #E4E6EC; }
        body.dark .bubble-ai-success { background: #1B2A4A; border-color: #166534; }
        body.dark .bubble-typing { background: #1B2A4A; border-color: #354A6B; }
        body.dark .chat-empty-title { color: #E4E6EC; }
        body.dark .chat-empty-sub { color: rgba(255,255,255,0.35); }
        body.dark .chat-suggestion-chip { background: #1B2A4A; border-color: #354A6B; color: #A0ABBD; }
        body.dark .chat-suggestion-chip:hover { background: #F97316; color: white; border-color: #F97316; }
        body.dark .modal { background: #1B2A4A; border-color: #354A6B; }
        body.dark .lang-btn { background: #0F1D33; border-color: #354A6B; color: #E4E6EC; }
        body.dark .lang-btn:hover { background: #354A6B; }
        body.dark .modal-cancel { color: rgba(255,255,255,0.25); }
        body.dark .score-modal { background: #1B2A4A; border-color: #354A6B; }
        body.dark .sp-no { background: #0F1D33; border-color: #354A6B; color: #AABFC2; }
        body.dark .preview-modal { background: #1B2A4A; border-color: #354A6B; }
        body.dark .preview-slide-wrap { background: #111; }
        body.dark .slide-card { background: #F8F9FF; }
        body.dark .preview-footer { background: #0F1D33; border-top-color: #354A6B; }
        body.dark .preview-nav-btn { background: #1B2A4A; border-color: #354A6B; color: white; }
        body.dark .btn-edit-preview { background: #1B2A4A; border-color: #354A6B; color: #AABFC2; }
        body.dark ::-webkit-scrollbar-track { background: #101820; }
        body.dark ::-webkit-scrollbar-thumb { background: #354A6B; }
    </style>
</head>
<body>


<!-- Modal public cible / langue -->
<div class="modal-overlay" id="modal-overlay">
    <div class="modal" id="modal-step-1">
        <div class="modal-head">
            <h2 data-i18n="modal1_title">👥 Public cible</h2>
            <p data-i18n="modal1_sub">À qui est destinée cette présentation ?</p>
        </div>
        <div class="modal-body">
            <button class="lang-btn" onclick="setAudience('developer')" data-i18n="aud_dev">💻 &nbsp;Développeurs</button>
            <button class="lang-btn" onclick="setAudience('manager')" data-i18n="aud_mgr">📊 &nbsp;Managers</button>
            <button class="lang-btn" onclick="setAudience('investor')" data-i18n="aud_inv">💼 &nbsp;Clients / Investisseurs</button>
        </div>
        <button class="modal-cancel" onclick="closeModal()" data-i18n="cancel">Annuler</button>
    </div>
    <div class="modal" id="modal-step-2" style="display:none">
        <div class="modal-head">
            <h2 data-i18n="modal2_title">🌐 Langue</h2>
            <p data-i18n="modal2_sub">Dans quelle langue générer la présentation ?</p>
        </div>
        <div class="modal-body">
            <button class="lang-btn" onclick="startGenerate('auto')" data-i18n="lang_auto">📄 &nbsp;Même langue que le README</button>
            <button class="lang-btn" onclick="startGenerate('both')" data-i18n="lang_both">🌍 &nbsp;Les deux (FR + EN)</button>
        </div>
        <button class="modal-cancel" onclick="closeModal()" data-i18n="cancel">Annuler</button>
    </div>
</div>

<!-- Score README modal -->
<div class="score-overlay" id="score-overlay" onclick="if(event.target===this)dismissScorePrompt()">
    <div class="score-modal">
        <div class="score-modal-header">
            <span class="score-modal-title" data-i18n="score_title">📊 Qualité du README</span>
            <button class="close-btn" onclick="dismissScorePrompt()">✕</button>
        </div>
        <div id="score-question" style="padding:32px 24px;text-align:center;">
            <div style="font-size:44px;margin-bottom:14px;">📋</div>
            <p data-i18n="score_q" style="color:#0F1D33;font-size:15px;font-weight:700;margin-bottom:6px;">Analyser la qualité de votre README ?</p>
            <p data-i18n="score_q_sub" style="color:#A0ABBD;font-size:12px;margin-bottom:28px;">L'IA évalue la clarté, complétude et structure.</p>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button class="sp-yes" onclick="acceptScorePrompt()" data-i18n="score_yes">Analyser</button>
                <button class="sp-no" onclick="dismissScorePrompt()" data-i18n="score_no">Passer</button>
            </div>
        </div>
        <div id="score-card" style="display:none;padding:20px 24px 24px;">
            <div style="display:flex;align-items:flex-start;gap:14px;">
                <div class="score-circle sc-loading" id="score-circle">...</div>
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
                        <span id="score-label" style="font-weight:700;font-size:13px;color:#0F1D33;">Analyse en cours...</span>
                        <span id="score-badge"></span>
                    </div>
                    <div id="score-body" style="display:flex;flex-direction:column;gap:5px;"></div>
                </div>
            </div>
            <div id="score-edit-btn-wrap" style="display:none;margin-top:16px;padding-top:14px;border-top:1px solid #D5D8DE;">
                <button onclick="dismissScorePrompt()" style="width:100%;padding:10px;background:#0F1D33;color:white;border:none;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:background 0.15s;" onmouseover="this.style.background='#1B2A4A'" onmouseout="this.style.background='#0F1D33'">OK</button>
            </div>
        </div>
    </div>
</div>

<!-- Preview modal -->
<div class="preview-overlay" id="preview-overlay" onclick="if(event.target===this)closePreview()">
    <div class="preview-modal">
        <div class="preview-header">
            <span class="preview-header-title" id="preview-pres-title">Aperçu</span>
            <button class="close-btn" onclick="closePreview()">✕</button>
        </div>
        <div class="preview-slide-wrap" id="preview-slide-wrap">
            <div class="slide-card">
                <div class="slide-card-header">
                    <div class="slide-card-num" id="slide-card-num">SLIDE 1</div>
                    <div class="preview-slide-title" id="preview-slide-title"></div>
                </div>
                <div class="slide-card-body">
                    <ul class="preview-slide-bullets" id="preview-slide-bullets"></ul>
                </div>
            </div>
        </div>
        <div class="preview-footer">
            <div class="preview-nav">
                <button class="preview-nav-btn" id="prev-slide-btn" onclick="prevSlide()">&#8592;</button>
                <span class="preview-counter" id="slide-counter">1 / 1</span>
                <button class="preview-nav-btn" id="next-slide-btn" onclick="nextSlide()">&#8594;</button>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
                <button class="btn-edit-preview" onclick="goToChat()" data-i18n="preview_edit">✏️ Modifier</button>
                <a class="btn-dl-preview" id="preview-dl-btn" href="#" download data-i18n="preview_dl">⬇ Télécharger</a>
            </div>
        </div>
    </div>
</div>

<!-- App layout -->
<div class="app-layout">

    <!-- Sidebar -->
    <aside class="sidebar">
        <div class="sidebar-logo">
            <svg viewBox="0 0 32 32" fill="none" width="24" height="24">
                <rect x="2"  y="14" width="28" height="4" rx="1" fill="#AABFC2" opacity="0.6"/>
                <rect x="6"  y="8"  width="20" height="4" rx="1" fill="#AABFC2" opacity="0.8"/>
                <rect x="10" y="2"  width="12" height="4" rx="1" fill="#AABFC2"/>
                <rect x="4"  y="20" width="24" height="4" rx="1" fill="#AABFC2" opacity="0.4"/>
                <rect x="8"  y="26" width="16" height="4" rx="1" fill="#AABFC2" opacity="0.2"/>
            </svg>
            <span class="sidebar-logo-text">OmnIA</span>
        </div>

        <div style="display:flex;gap:8px;padding:10px 16px;">
            <div class="stat-box" style="flex:1;">
                <div class="stat-box-num" id="stat-generated">0</div>
                <div class="stat-box-label" data-i18n="stat_generated">Générées</div>
            </div>
            <div class="stat-box" style="flex:1;">
                <div class="stat-box-num" id="stat-history">0</div>
                <div class="stat-box-label" data-i18n="stat_history">Historique</div>
            </div>
        </div>
        <div class="sidebar-divider" style="margin-top:0;"></div>

        <div class="sidebar-section-label" data-i18n="nav_label">Navigation</div>
        <button class="sidebar-item active">
            <span>📄</span> README → PowerPoint
        </button>

        <div class="sidebar-divider"></div>
        <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 16px 6px;">
            <span class="sidebar-section-label" style="padding:0;" data-i18n="history_title">Historique</span>
            <button id="history-clear-btn" onclick="clearHistory()" title="Effacer l'historique" style="display:none;background:none;border:none;cursor:pointer;color:rgba(255,255,255,0.3);font-size:13px;padding:2px 5px;border-radius:4px;line-height:1;transition:color 0.15s;" onmouseover="this.style.color='#E53E3E'" onmouseout="this.style.color='rgba(255,255,255,0.3)'">&#128465;</button>
        </div>
        <div id="history-list"></div>
    </aside>

    <!-- Main -->
    <div class="main-content">

        <!-- Header -->
        <div class="page-header">
            <div class="page-header-inner">
                <div>
                    <div class="page-header-title" data-i18n="main_title">README vers <span>PowerPoint</span></div>
                    <div class="page-header-sub" data-i18n="subtitle">Uploadez un README.md et obtenez une présentation professionnelle.</div>
                </div>
                <div class="header-controls" style="align-self:flex-end;padding-bottom:4px;">
                    <label class="theme-toggle" onclick="toggleTheme()">
                        <span class="theme-toggle-icon" id="theme-icon">☀️</span>
                        <div class="theme-switch" id="theme-btn"></div>
                        <span class="theme-toggle-icon">🌙</span>
                    </label>
                    <div class="lang-pill">
                        <button class="lang-pill-opt active" id="lang-fr" onclick="setLang('fr')">FR</button>
                        <button class="lang-pill-opt" id="lang-en" onclick="setLang('en')">EN</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab bar -->
        <div class="tab-bar-wrap">
            <div class="tab-bar">
                <button class="tab-btn active" id="tab-upload" data-i18n="tab_source">📁 Source</button>
                <button class="tab-btn" id="tab-result" data-i18n="tab_result">📊 Résultat</button>
                <button class="tab-btn" id="tab-chat" data-i18n="tab_chat">✨ Personnaliser</button>
            </div>
        </div>

        <!-- Body -->
        <div class="page-body">

            <!-- ── Tab: Source ── -->
            <div id="panel-upload">

                <!-- Upload README -->
                <div class="card">
                    <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
                        <span class="card-header-title" data-i18n="card_readme">📄 Fichier README</span>
                        <button onclick="resetForm()" title="Réinitialiser le formulaire" style="background:none;border:1px solid rgba(255,255,255,0.2);border-radius:6px;color:rgba(255,255,255,0.7);cursor:pointer;padding:4px 10px;font-size:12px;display:flex;align-items:center;gap:5px;font-family:inherit;" onmouseover="this.style.color='white';this.style.borderColor='rgba(255,255,255,0.5)'" onmouseout="this.style.color='rgba(255,255,255,0.7)';this.style.borderColor='rgba(255,255,255,0.2)'">&#8635; Réinitialiser</button>
                    </div>
                    <div class="card-body">
                        <div id="file-upload-zone" class="upload-area" onclick="document.getElementById('file').click()">
                            <span class="upload-icon">📄</span>
                            <div class="label-text" data-i18n="upload_label">Glissez votre fichier ou <span>cliquez pour uploader</span></div>
                            <div class="hint" data-i18n="upload_hint">Formats acceptés : .md · .txt</div>
                            <input type="file" id="file" accept=".md,.txt" onchange="onFileSelected(this)">
                            <div id="filename-badge" style="display:none;margin-top:10px;align-items:center;gap:6px;">
                                <span id="filename-text"></span>
                                <button onclick="clearFile(event)" title="Effacer" style="background:none;border:none;cursor:pointer;color:#A0ABBD;font-size:14px;padding:0 2px;line-height:1;" onmouseover="this.style.color='#E53E3E'" onmouseout="this.style.color='#A0ABBD'">&#10005;</button>
                            </div>
                        </div>

                        <div class="or-divider"><hr><span>OU</span><hr></div>

                        <!-- GitHub import -->
                        <div id="github-import-zone" class="github-import">
                            <div class="github-import-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="#354A6B"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                                <span data-i18n="gh_label">Importer depuis GitHub</span>
                                <span class="github-badge" id="github-badge" style="display:none;align-items:center;gap:4px;"><span id="github-badge-text"></span><button onclick="clearGitHub(event)" style="background:none;border:none;cursor:pointer;color:inherit;font-size:11px;padding:0 1px;line-height:1;">&#10005;</button></span>
                            </div>
                            <div class="github-input-row">
                                <span class="github-prefix">github.com/</span>
                                <input id="github-url" class="github-input" type="text" placeholder="user/repo" onkeydown="if(event.key==='Enter') fetchGitHub()" oninput="onGitHubInput()">
                                <button class="github-fetch-btn" id="github-fetch-btn" onclick="fetchGitHub()" data-i18n="gh_btn">Importer</button>
                            </div>
                            <div class="github-error" id="github-error"></div>
                        </div>
                    </div>
                </div>

                <!-- Logo -->
                <div class="card">
                    <div class="card-header"><span class="card-header-title" data-i18n="card_logo">🎨 Logo entreprise (optionnel)</span></div>
                    <div class="card-body">
                        <div class="upload-area" onclick="document.getElementById('logo').click()" style="padding:18px;margin-bottom:0;">
                            <span class="upload-icon" style="font-size:24px;">🎨</span>
                            <div class="label-text" data-i18n="logo_label">Logo de votre entreprise <span>(optionnel)</span></div>
                            <div class="hint">PNG · JPG · Couleurs extraites automatiquement</div>
                            <input type="file" id="logo" accept=".png,.jpg,.jpeg" onchange="showLogo(this)">
                            <div id="logo-badge" style="display:none;margin-top:10px;align-items:center;gap:6px;">
                                <span id="logo-badge-text"></span>
                                <button onclick="clearLogo(event)" title="Effacer" style="background:none;border:none;cursor:pointer;color:#A0ABBD;font-size:14px;padding:0 2px;line-height:1;" onmouseover="this.style.color='#E53E3E'" onmouseout="this.style.color='#A0ABBD'">&#10005;</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Generate button -->
                <button class="btn-generate" id="btn" onclick="openModal()" data-i18n="generate_btn">Générer le PowerPoint</button>
                <div class="progress-bar" id="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
                <div class="status" id="status"></div>
            </div>

            <!-- ── Tab: Résultat ── -->
            <div id="panel-result" style="display:none;">

                <!-- Empty state -->
                <div id="result-empty" style="text-align:center;padding:60px 20px;">
                    <div style="font-size:48px;margin-bottom:16px;">📊</div>
                    <div style="font-size:15px;font-weight:700;color:#0F1D33;margin-bottom:6px;">Aucune présentation générée</div>
                    <div style="font-size:13px;color:#A0ABBD;margin-bottom:24px;">Allez dans l'onglet Source pour uploader un README et générer.</div>
                    <button onclick="showTab('upload')" style="padding:10px 22px;background:#0F1D33;color:white;border:none;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;">📁 Aller à Source</button>
                </div>

                <!-- Liste dynamique des présentations -->
                <div id="result-sort-bar" style="display:none;align-items:center;gap:10px;margin-bottom:4px;">
                    <span data-i18n="sort_label" style="font-size:12px;color:#A0ABBD;font-weight:600;">Trier par date :</span>
                    <button id="sort-desc-btn" onclick="sortResults('desc')" data-i18n="sort_desc" style="padding:5px 12px;border-radius:6px;border:1px solid #D5D8DE;background:#0F1D33;color:white;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">&#8595; Plus r&eacute;cent</button>
                    <button id="sort-asc-btn"  onclick="sortResults('asc')"  data-i18n="sort_asc"  style="padding:5px 12px;border-radius:6px;border:1px solid #D5D8DE;background:#EFF1F5;color:#0F1D33;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">&#8593; Plus ancien</button>
                </div>
                <div id="result-list" style="display:none;flex-direction:column;gap:20px;"></div>

                <!-- Lien download caché -->
                <a id="download-link" href="#" download style="display:none;"></a>
            </div>

            <!-- ── Tab: Chat ── -->
            <div id="panel-chat" style="display:none;">
                <div class="chat-wrap">
                    <!-- topbar -->
                    <div class="chat-topbar">
                        <div class="chat-topbar-icon">&#10024;</div>
                        <div class="chat-topbar-info">
                            <div class="chat-topbar-title" data-i18n="card_chat">Personnaliser avec l'IA</div>
                            <div class="chat-topbar-sub" data-i18n="chat_sub">Modifiez votre pr&#233;sentation en langage naturel</div>
                        </div>
                        <div class="chat-online-dot"></div>
                    </div>
                    <!-- messages -->
                    <div id="chat-messages">
                        <div class="chat-empty-state" id="chat-empty">
                            <div class="chat-empty-icon">&#128161;</div>
                            <div class="chat-empty-title" data-i18n="chat_empty_title">Comment puis-je vous aider&#160;?</div>
                            <div class="chat-empty-sub" data-i18n="chat_empty_sub">D&#233;crivez les modifications souhait&#233;es et l'IA mettra &#224; jour votre pr&#233;sentation.</div>
                        </div>
                    </div>
                    <!-- input -->
                    <div id="chat-input-bar">
                        <div class="chat-input-inner">
                            <input id="chat-input" type="text" data-i18n-placeholder="chat_placeholder" placeholder="D&#233;crivez les modifications..." onkeydown="if(event.key==='Enter') sendChat()">
                            <button class="chat-send-btn" onclick="sendChat()" title="Envoyer">&#10148;</button>
                        </div>
                    </div>
                </div>
            </div>

        </div><!-- /page-body -->
    </div><!-- /main-content -->
</div><!-- /app-layout -->


<script>
    let selectedAudience = 'developer';
    let currentSessionId = null;
    let currentUILang = 'fr';
    let readmeContent = null;

    const TRANSLATIONS = {
        fr: {
            main_title:       "README vers <span>PowerPoint</span>",
            subtitle:         "Uploadez un README.md et obtenez une présentation professionnelle.",
            upload_label:     "Glissez votre fichier ou <span>cliquez pour uploader</span>",
            upload_hint:      "Formats acceptés : .md · .txt",
            logo_label:       "Logo de votre entreprise <span>(optionnel)</span>",
            generate_btn:     "Générer le PowerPoint",
            modal1_title:     "👥 Public cible",
            modal1_sub:       "À qui est destinée cette présentation ?",
            aud_dev:          "💻 &nbsp;Développeurs",
            aud_mgr:          "📊 &nbsp;Managers",
            aud_inv:          "💼 &nbsp;Clients / Investisseurs",
            cancel:           "Annuler",
            modal2_title:     "🌐 Langue",
            modal2_sub:       "Dans quelle langue générer la présentation ?",
            lang_auto:        "📄 &nbsp;Même langue que le README",
            lang_both:        "🌍 &nbsp;Les deux (FR + EN)",
            dl_sub:           "Générée avec succès · Prête à télécharger",
            history_title:    "Historique",
            history_clear:    "Effacer l'historique",
            chat_send:        "Envoyer",
            chat_placeholder: "Décrivez les modifications...",
            nav_label:        "Navigation",
            tab_source:       "📁 Source",
            tab_result:       "📊 Résultat",
            tab_chat:         "✨ Personnaliser",
            stat_generated:   "Générées",
            stat_history:     "Historique",
            card_readme:      "📄 Fichier README",
            card_logo:        "🎨 Logo entreprise (optionnel)",
            card_result:      "✅ Présentation générée",
            card_chat:        "✨ Personnaliser avec l'IA",
            gh_label:         "Importer depuis GitHub",
            gh_btn:           "Importer",
            gh_prefix:        "github.com/",
            gh_placeholder:   "user/repo",
            score_title:      "📊 Qualité du README",
            score_q:          "Analyser la qualité de votre README ?",
            score_q_sub:      "L'IA évalue la clarté, complétude et structure.",
            score_yes:        "Analyser",
            score_no:         "Passer",
            score_loading:    "Analyse du README...",
            score_edit_btn:   "✏️ Améliorer avec le chatbot",
            preview_edit:     "✏️ Modifier",
            preview_dl:       "⬇ Télécharger",
            dl_btn:           "⬇ Télécharger",
            dl_btn_zip:       "⬇ Télécharger ZIP",
            preview_label:    "Aperçu",
            sort_label:       "Trier par date :",
            sort_desc:        "↓ Plus récent",
            sort_asc:         "↑ Plus ancien",
            card_preview_btn: "👁 Aperçu",
            card_dl_btn:      "⬇ Télécharger",
            chat_welcome:      "<strong>✨ Présentation générée !</strong><br>Décrivez ce que vous souhaitez modifier — couleurs, titres, slides, polices...",
            chat_done:         "Modifications terminées",
            chat_see:          "⬇ Voir le résultat",
            chat_sub:          "Modifiez votre présentation en langage naturel",
            chat_empty_title:  "Comment puis-je vous aider ?",
            chat_empty_sub:    "Décrivez les modifications souhaitées et l'IA mettra à jour votre présentation.",
            chip_colors:       "Changer les couleurs",
            chip_font:         "Modifier la police",
            chip_bullets:      "Réduire les bullets",
            chip_tone:         "Ton plus formel",
            theme_light:       "☀️ Light",
            theme_dark:        "🌙 Dark",
            conn_error:        "Erreur de connexion",
            gen_status:        "Analyse du README en cours...",
            gen_status_both:   "Génération FR + EN en cours...",
        },
        en: {
            main_title:       "README to <span>PowerPoint</span>",
            subtitle:         "Upload a README.md and get a professional presentation.",
            upload_label:     "Drag your file or <span>click to upload</span>",
            upload_hint:      "Accepted formats: .md · .txt",
            logo_label:       "Your company logo <span>(optional)</span>",
            generate_btn:     "Generate PowerPoint",
            modal1_title:     "👥 Target audience",
            modal1_sub:       "Who is this presentation for?",
            aud_dev:          "💻 &nbsp;Developers",
            aud_mgr:          "📊 &nbsp;Managers",
            aud_inv:          "💼 &nbsp;Clients / Investors",
            cancel:           "Cancel",
            modal2_title:     "🌐 Language",
            modal2_sub:       "In which language to generate the presentation?",
            lang_auto:        "📄 &nbsp;Same language as README",
            lang_both:        "🌍 &nbsp;Both (FR + EN)",
            dl_sub:           "Generated successfully · Ready to download",
            history_title:    "History",
            history_clear:    "Clear history",
            chat_send:        "Send",
            chat_placeholder: "Describe the changes...",
            nav_label:        "Navigation",
            tab_source:       "📁 Source",
            tab_result:       "📊 Result",
            tab_chat:         "✨ Customize",
            stat_generated:   "Generated",
            stat_history:     "History",
            card_readme:      "📄 README File",
            card_logo:        "🎨 Company logo (optional)",
            card_result:      "✅ Presentation generated",
            card_chat:        "✨ Customize with AI",
            gh_label:         "Import from GitHub",
            gh_btn:           "Import",
            gh_prefix:        "github.com/",
            gh_placeholder:   "user/repo",
            score_title:      "📊 README Quality",
            score_q:          "Analyze your README quality?",
            score_q_sub:      "AI evaluates clarity, completeness and structure.",
            score_yes:        "Analyze",
            score_no:         "Skip",
            score_loading:    "Analyzing README...",
            score_edit_btn:   "✏️ Improve with chatbot",
            preview_edit:     "✏️ Edit",
            preview_dl:       "⬇ Download",
            dl_btn:           "⬇ Download",
            dl_btn_zip:       "⬇ Download ZIP",
            preview_label:    "Preview",
            sort_label:       "Sort by date:",
            sort_desc:        "↓ Most recent",
            sort_asc:         "↑ Oldest",
            card_preview_btn: "👁 Preview",
            card_dl_btn:      "⬇ Download",
            chat_welcome:      "<strong>✨ Presentation generated!</strong><br>Describe what you want to change — colors, titles, slides, fonts...",
            chat_done:         "Changes applied",
            chat_see:          "⬇ View result",
            chat_sub:          "Edit your presentation in plain language",
            chat_empty_title:  "How can I help you?",
            chat_empty_sub:    "Describe the changes you want and the AI will update your presentation.",
            chip_colors:       "Change colors",
            chip_font:         "Edit font",
            chip_bullets:      "Fewer bullet points",
            chip_tone:         "More formal tone",
            theme_light:       "☀️ Light",
            theme_dark:        "🌙 Dark",
            conn_error:        "Connection error",
            gen_status:        "Analyzing README...",
            gen_status_both:   "Generating FR + EN...",
        }
    };

    function toggleTheme() {
        document.body.classList.toggle('dark');
    }

    function setLang(lang) {
        currentUILang = lang;
        document.getElementById('lang-fr').classList.toggle('active', lang === 'fr');
        document.getElementById('lang-en').classList.toggle('active', lang === 'en');
        var t = TRANSLATIONS[currentUILang];
        document.querySelectorAll('[data-i18n]').forEach(function(el) {
            var key = el.getAttribute('data-i18n');
            if (t[key] !== undefined) el.innerHTML = t[key];
        });
        var chatInput = document.getElementById('chat-input');
        if (chatInput) chatInput.placeholder = t.chat_placeholder;
        var ghInput = document.getElementById('github-url');
        if (ghInput) ghInput.placeholder = t.gh_placeholder;
        // Mettre à jour le download filename sur les liens des cartes résultat
        document.querySelectorAll('#result-list a[data-i18n="card_dl_btn"]').forEach(function(a) {
            var href = a.getAttribute('href') || '';
            var sid = href.replace('/download/', '');
            var hist = presentationHistory.find(function(h){ return h.sessionId === sid; });
            if (hist) a.setAttribute('download', hist.isZip ? 'presentations_FR_EN.zip' : 'presentation.pptx');
        });
    }

    function toggleLang() { setLang(currentUILang === 'fr' ? 'en' : 'fr'); }

    /* ── Tab switching ── */
    function showTab(name) {
        ['upload','result','chat'].forEach(function(t) {
            document.getElementById('panel-' + t).style.display = (t === name) ? 'block' : 'none';
            var btn = document.getElementById('tab-' + t);
            if (btn) btn.classList.toggle('active', t === name);
        });
        if (name === 'result') {
            var list = document.getElementById('result-list');
            var empty = document.getElementById('result-empty');
            if (list && empty) {
                var hasCards = list.children.length > 0;
                empty.style.display = hasCards ? 'none' : 'block';
                list.style.display = hasCards ? 'flex' : 'none';
            }
        }
    }
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('tab-upload').addEventListener('click', function(){ showTab('upload'); });
        var tr = document.getElementById('tab-result');
        if (tr) tr.addEventListener('click', function(){ showTab('result'); });
        var tc = document.getElementById('tab-chat');
        if (tc) tc.addEventListener('click', function(){ showTab('chat'); });
        restoreHistory();
    });

    async function restoreHistory() {
        try {
            var res = await fetch('/sessions');
            var sessions = await res.json();
            if (!sessions.length) return;
            for (var i = sessions.length - 1; i >= 0; i--) {
                var s = sessions[i];
                var dt = s.created_at ? new Date(s.created_at) : new Date();
                var dateLabel = dt.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric'})
                    + ' ' + dt.getHours().toString().padStart(2,'0') + ':' + dt.getMinutes().toString().padStart(2,'0');
                presentationHistory.push({
                    sessionId: s.session_id,
                    title: s.title || 'Présentation',
                    isZip: s.is_zip,
                    time: dateLabel,
                    ts: dt.getTime(),
                });
                await addResultCard(s.session_id, s.title, s.is_zip);
            }
            // Trier par plus récent
            presentationHistory.sort(function(a,b){ return b.ts - a.ts; });
            renderHistory();
            var genCount = document.getElementById('stat-generated');
            if (genCount) genCount.textContent = sessions.length;
        } catch(e) { /* silencieux */ }
    }

    async function fetchGitHub() {
        var raw = document.getElementById('github-url').value.trim();
        if (!raw) return;
        var btn = document.getElementById('github-fetch-btn');
        var badge = document.getElementById('github-badge');
        var errDiv = document.getElementById('github-error');
        var url = raw.startsWith('http') ? raw : 'https://github.com/' + raw;
        btn.disabled = true; btn.textContent = '...';
        errDiv.style.display = 'none'; badge.style.display = 'none';
        try {
            var res = await fetch('/fetch-readme', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            var data = await res.json();
            if (data.error) {
                errDiv.textContent = data.error; errDiv.style.display = 'block';
                readmeContent = null;
            } else {
                readmeContent = data.content;
                document.getElementById('github-badge-text').textContent = '✓ ' + data.repo;
                badge.style.display = 'inline-flex';
                document.getElementById('file-upload-zone').classList.add('source-locked');
                showScorePrompt(readmeContent);
            }
        } catch(e) {
            errDiv.textContent = 'Erreur de connexion'; errDiv.style.display = 'block';
        } finally {
            btn.disabled = false; btn.textContent = 'Importer';
        }
    }

    function openModal() {
        const file = document.getElementById('file').files[0];
        if (!file && !readmeContent) { alert('Veuillez uploader un fichier README.md ou importer depuis GitHub'); return; }
        document.getElementById('modal-step-1').style.display = 'block';
        document.getElementById('modal-step-2').style.display = 'none';
        document.getElementById('modal-overlay').classList.add('show');
    }

    function closeModal() {
        document.getElementById('modal-overlay').classList.remove('show');
    }

    function setAudience(audience) {
        selectedAudience = audience;
        document.getElementById('modal-step-1').style.display = 'none';
        document.getElementById('modal-step-2').style.display = 'block';
    }

    function startGenerate(lang) {
        closeModal();
        generate(lang);
    }

    function onFileSelected(input) {
        if (!input.files[0]) return;
        document.getElementById('filename-text').textContent = '📎 ' + input.files[0].name;
        document.getElementById('filename-badge').style.display = 'inline-flex';
        document.getElementById('github-import-zone').classList.add('source-locked');
        var reader = new FileReader();
        reader.onload = function(e) { showScorePrompt(e.target.result); };
        reader.readAsText(input.files[0]);
    }

    function clearFile(e) {
        e.stopPropagation();
        document.getElementById('file').value = '';
        document.getElementById('filename-badge').style.display = 'none';
        document.getElementById('github-import-zone').classList.remove('source-locked');
        document.getElementById('score-overlay').classList.remove('show');
        pendingReadmeContent = null;
    }

    function clearGitHub(e) {
        e.stopPropagation();
        readmeContent = null;
        document.getElementById('github-url').value = '';
        document.getElementById('github-badge').style.display = 'none';
        document.getElementById('github-error').style.display = 'none';
        document.getElementById('file-upload-zone').classList.remove('source-locked');
        document.getElementById('score-overlay').classList.remove('show');
        pendingReadmeContent = null;
    }

    function resetForm() {
        // Fichier README
        document.getElementById('file').value = '';
        document.getElementById('filename-badge').style.display = 'none';
        document.getElementById('filename-text').textContent = '';
        // GitHub
        readmeContent = null;
        document.getElementById('github-url').value = '';
        document.getElementById('github-badge').style.display = 'none';
        document.getElementById('github-badge-text').textContent = '';
        document.getElementById('github-error').style.display = 'none';
        // Logo
        document.getElementById('logo').value = '';
        document.getElementById('logo-badge').style.display = 'none';
        document.getElementById('logo-badge-text').textContent = '';
        // Déverrouiller les zones
        document.getElementById('file-upload-zone').classList.remove('source-locked');
        document.getElementById('github-import-zone').classList.remove('source-locked');
        // Fermer modals
        document.getElementById('score-overlay').classList.remove('show');
        pendingReadmeContent = null;
        // Reset status
        var status = document.getElementById('status');
        if (status) status.textContent = '';
    }

    function onGitHubInput() {
        var val = document.getElementById('github-url').value.trim();
        var fileZone = document.getElementById('file-upload-zone');
        if (val.length > 0) {
            fileZone.classList.add('source-locked');
        } else {
            fileZone.classList.remove('source-locked');
        }
    }

    function showFilename(input) {
        const badge = document.getElementById('filename-badge');
        if (input.files[0]) {
            badge.textContent = '📎 ' + input.files[0].name;
            badge.style.display = 'inline-block';
        }
    }

    function showLogo(input) {
        const badge = document.getElementById('logo-badge');
        const text  = document.getElementById('logo-badge-text');
        if (input.files[0]) {
            text.textContent = '🎨 ' + input.files[0].name;
            badge.style.display = 'inline-flex';
        }
    }

    function clearLogo(e) {
        e.stopPropagation();
        document.getElementById('logo').value = '';
        document.getElementById('logo-badge').style.display = 'none';
        document.getElementById('logo-badge-text').textContent = '';
    }

    function setupDropZone(zone, input, extensions, onFileSet) {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault(); e.stopPropagation();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault(); e.stopPropagation();
            if (!zone.contains(e.relatedTarget)) zone.classList.remove('drag-over');
        });
        zone.addEventListener('drop', function(e) {
            e.preventDefault(); e.stopPropagation();
            zone.classList.remove('drag-over');
            var file = e.dataTransfer.files[0];
            if (!file) return;
            var ext = '.' + file.name.split('.').pop().toLowerCase();
            if (!extensions.includes(ext)) {
                alert('Format non supporté. Acceptés : ' + extensions.join(', '));
                return;
            }
            try {
                var dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                onFileSet(input);
            } catch(err) { console.error('Drop error:', err); }
        });
    }

    function initDragDrop() {
        var fileInput = document.getElementById('file');
        var logoInput = document.getElementById('logo');
        setupDropZone(fileInput.closest('.upload-area'), fileInput, ['.md', '.txt'], onFileSelected);
        setupDropZone(logoInput.closest('.upload-area'), logoInput, ['.png', '.jpg', '.jpeg'], showLogo);
    }
    document.addEventListener('DOMContentLoaded', initDragDrop);

    /* ── Historique ── */
    var presentationHistory = [];

    function addToHistory(sessionId, title, isZip) {
        var now = new Date();
        var date = now.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric'})
                 + ' ' + now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        presentationHistory.unshift({ sessionId: sessionId, title: title || 'Présentation', isZip: isZip, time: date, ts: now.getTime() });
        if (presentationHistory.length > 8) presentationHistory.pop();
        renderHistory();
    }

    function toggleChatMessages() {
        var msgs = document.getElementById('chat-messages');
        var bar  = document.getElementById('chat-input-bar');
        var btn  = document.getElementById('chat-toggle-btn');
        var collapsed = msgs.style.display === 'none';
        msgs.style.display = collapsed ? 'flex' : 'none';
        bar.style.display  = collapsed ? 'flex' : 'none';
        btn.classList.toggle('collapsed', !collapsed);
    }

    function renderHistory() {
        var list = document.getElementById('history-list');
        var clearBtn = document.getElementById('history-clear-btn');
        list.innerHTML = '';
        if (presentationHistory.length === 0) {
            if (clearBtn) clearBtn.style.display = 'none';
            var count = document.getElementById('stat-history');
            if (count) count.textContent = '0';
            return;
        }
        if (clearBtn) clearBtn.style.display = 'block';
        var count = document.getElementById('stat-history');
        if (count) count.textContent = presentationHistory.length;
        presentationHistory.forEach(function(item, idx) {
            var fname = item.isZip ? 'presentations_FR_EN.zip' : 'presentation.pptx';
            var shortTitle = item.title.length > 22 ? item.title.substring(0, 22) + '...' : item.title;
            var div = document.createElement('div');
            div.className = 'sidebar-history-item';
            div.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:6px;cursor:pointer;transition:background 0.15s;';
            div.onmouseover = function(){ this.style.background='rgba(255,255,255,0.06)'; };
            div.onmouseout  = function(){ this.style.background=''; };
            div.innerHTML = '<div style="flex:1;min-width:0;">'
                + '<div style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.85);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="' + item.title + '">' + shortTitle + '</div>'
                + '<div style="font-size:10px;color:rgba(255,255,255,0.35);margin-top:2px;">' + item.time + ' &middot; ' + fname + '</div>'
                + '</div>'
                + '<a href="/download/' + item.sessionId + '" download="' + fname + '" onclick="event.stopPropagation()" title="Telecharger" class="hist-dl-btn">&#11015;</a>'
                + '<button onclick="removeFromHistory(' + idx + ')" title="Supprimer" class="hist-del-btn">&#10005;</button>';
            list.appendChild(div);
        });
    }

    function removeFromHistory(idx) {
        var sid = presentationHistory[idx].sessionId;
        presentationHistory.splice(idx, 1);
        renderHistory();
        var card = document.getElementById('rc-' + sid);
        if (card) card.remove();
        _checkResultEmpty();
        fetch('/sessions/' + sid, {method: 'DELETE'}).catch(function(){});
    }

    function removeResult(btn) {
        var sid = btn.getAttribute('data-sid');
        var card = document.getElementById('rc-' + sid);
        if (card) card.remove();
        _checkResultEmpty();
        presentationHistory = presentationHistory.filter(function(h){ return h.sessionId !== sid; });
        renderHistory();
        fetch('/sessions/' + sid, {method: 'DELETE'}).catch(function(){});
    }

    function sortResults(order) {
        var list = document.getElementById('result-list');
        if (!list) return;
        var cards = Array.from(list.children);
        cards.sort(function(a, b) {
            var ta = parseInt(a.dataset.ts || '0');
            var tb = parseInt(b.dataset.ts || '0');
            return order === 'asc' ? ta - tb : tb - ta;
        });
        cards.forEach(function(c){ list.appendChild(c); });
        // Mettre à jour le style des boutons actifs
        document.getElementById('sort-desc-btn').style.background = order === 'desc' ? '#0F1D33' : '#EFF1F5';
        document.getElementById('sort-desc-btn').style.color      = order === 'desc' ? 'white'   : '#0F1D33';
        document.getElementById('sort-asc-btn').style.background  = order === 'asc'  ? '#0F1D33' : '#EFF1F5';
        document.getElementById('sort-asc-btn').style.color       = order === 'asc'  ? 'white'   : '#0F1D33';
    }

    function _checkResultEmpty() {
        var list    = document.getElementById('result-list');
        var empty   = document.getElementById('result-empty');
        var sortBar = document.getElementById('result-sort-bar');
        if (!list || !empty) return;
        var hasCards = list.children.length > 0;
        list.style.display    = hasCards ? 'flex'   : 'none';
        empty.style.display   = hasCards ? 'none'   : 'block';
        if (sortBar) sortBar.style.display = hasCards ? 'flex' : 'none';
    }

    function clearHistory() {
        presentationHistory = [];
        renderHistory();
    }

    async function addResultCard(sessionId, title, isZip) {
        var list = document.getElementById('result-list');
        var empty = document.getElementById('result-empty');
        if (!list) return;
        empty.style.display = 'none';
        list.style.display = 'flex';

        var fname = isZip ? 'presentations_FR_EN.zip' : 'presentation.pptx';
        var icon = isZip ? '🗜️' : '📊';
        var cardId = 'rc-' + sessionId;
        var slideAreaId = 'slides-' + sessionId;

        var card = document.createElement('div');
        card.id = cardId;
        card.dataset.ts = Date.now();
        card.style.cssText = 'background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(15,29,51,0.10);border:1px solid #E2E5EC;transition:box-shadow 0.2s;';
        card.onmouseover = function(){ this.style.boxShadow='0 8px 28px rgba(15,29,51,0.16)'; };
        card.onmouseout  = function(){ this.style.boxShadow='0 4px 16px rgba(15,29,51,0.10)'; };

        var now2 = new Date();
        var dateLabel = now2.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric'})
                      + ' ' + now2.getHours().toString().padStart(2,'0') + ':' + now2.getMinutes().toString().padStart(2,'0');
        var num = list.children.length + 1;
        var t = TRANSLATIONS[currentUILang];
        card.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:2px solid #F97316;">'
            + '<div style="display:flex;align-items:center;gap:12px;">'
            + '<div style="width:38px;height:38px;background:#EFF1F5;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">' + icon + '</div>'
            + '<div>'
            + '<div style="font-size:13px;font-weight:700;color:#0F1D33;line-height:1.3;">' + (title || 'Présentation') + '</div>'
            + '<div style="font-size:11px;color:#A0ABBD;margin-top:2px;">' + dateLabel + ' &middot; ' + fname + '</div>'
            + '</div>'
            + '</div>'
            + '<div style="display:flex;gap:8px;align-items:center;">'
            + '<button onclick="openPreviewFor(this)" data-sid="' + sessionId + '" data-i18n="card_preview_btn" style="padding:8px 16px;background:#EFF1F5;color:#0F1D33;border:1px solid #D5D8DE;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:5px;">' + t.card_preview_btn + '</button>'
            + '<a href="/download/' + sessionId + '" download="' + fname + '" data-i18n="card_dl_btn" style="padding:8px 16px;background:#0F1D33;color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:5px;">' + t.card_dl_btn + '</a>'
            + '<button onclick="removeResult(this)" data-sid="' + sessionId + '" title="Supprimer" class="result-del-btn">&#128465;</button>'
            + '</div>'
            + '</div>';

        list.insertBefore(card, list.firstChild);
        _checkResultEmpty();
    }

    async function openPreviewFor(btn) {
        var sessionId = btn.getAttribute('data-sid');
        try {
            var res = await fetch('/preview/' + sessionId);
            var data = await res.json();
            if (data.error) { alert(data.error); return; }
            var contentSlides = (data.slides_plan && data.slides_plan.slides) ? data.slides_plan.slides : [];
            var presTitle = (data.slides_plan && data.slides_plan.title) ? data.slides_plan.title : 'Aperçu';
            // Build full slides array: cover first, then content slides
            previewSlides = [{type:'cover', title: presTitle}].concat(
                contentSlides.map(function(s){ return {type:'content', title:s.title, bullets:s.bullets}; })
            );
            if (!previewSlides.length) { alert('Aucune slide à afficher.'); return; }
            window._previewSessionId = sessionId;
            window._previewHasLogo  = data.has_logo || false;
            document.getElementById('preview-pres-title').textContent = presTitle;
            document.getElementById('preview-dl-btn').href = '/download/' + sessionId;
            var colors = data.colors || {};
            _setPreviewColors(
                colors.primary    || '#1E3A5F',
                colors.accent     || '#F97316',
                colors.bg         || '#F8F9FF',
                colors.text       || '#333344',
                colors.title_text || '#FFFFFF'
            );
            previewCurrentIndex = 0;
            renderPreviewSlide();
            document.getElementById('preview-overlay').classList.add('show');
        } catch(e) {
            alert("Erreur lors du chargement de l'aperçu");
        }
    }

    function _escHtml(s) {
        return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function _setPreviewColors(primary, accent, bgColor, textColor, titleColor) {
        window._previewPrimary    = primary    || '#1E3A5F';
        window._previewAccent     = accent     || '#F97316';
        window._previewBg         = bgColor    || '#F8F9FF';
        window._previewText       = textColor  || '#333344';
        window._previewTitleColor = titleColor || '#FFFFFF';
        // Update download button color
        var dlBtn = document.getElementById('preview-dl-btn');
        if (dlBtn) dlBtn.style.background = window._previewPrimary;
        var hdr = document.querySelector('#preview-overlay .preview-header');
        if (hdr) hdr.style.background = window._previewPrimary;
    }

    function applyPreviewColors(primary, accent, bgColor, textColor, titleColor) {
        _setPreviewColors(primary, accent, bgColor, textColor, titleColor);
        renderPreviewSlide();
    }

    function renderSlideCards() { /* obsolete */ }

    async function generate(lang) {
        const file = document.getElementById('file').files[0];

        const btn = document.getElementById('btn');
        const status = document.getElementById('status');
        const progressBar = document.getElementById('progress-bar');
        const progressFill = document.getElementById('progress-fill');

        btn.disabled = true;
        progressBar.style.display = 'block';
        progressFill.style.animation = 'none';
        progressFill.offsetHeight;
        progressFill.style.animation = 'progress 2.5s ease-in-out forwards';

        const isDouble = lang === 'both';
        var t = TRANSLATIONS[currentUILang];
        status.textContent = isDouble ? t.gen_status_both : t.gen_status;

        const form = new FormData();
        if (readmeContent) {
            const blob = new Blob([readmeContent], {type: 'text/plain'});
            form.append('file', blob, 'README.md');
        } else {
            form.append('file', file);
        }
        form.append('lang', lang);
        form.append('audience', selectedAudience);
        const logo = document.getElementById('logo').files[0];
        if (logo) form.append('logo', logo);

        try {
            const res = await fetch('/generate', { method: 'POST', body: form });
            if (!res.ok) {
                var errData = await res.json().catch(function(){ return {}; });
                throw new Error(errData.error || 'Erreur serveur');
            }

            const data = await res.json();
            currentSessionId = data.session_id;

            progressFill.style.animation = 'none';
            progressFill.style.width = '100%';
            progressFill.style.transition = 'width 0.3s ease';

            addToHistory(data.session_id, data.title, data.is_zip);
            await addResultCard(data.session_id, data.title, data.is_zip);
            var genCount = document.getElementById('stat-generated');
            if (genCount) genCount.textContent = parseInt(genCount.textContent || '0') + 1;


            setTimeout(async () => {
                progressBar.style.display = 'none';
                status.textContent = '';

                // Switch to result tab
                showTab('result');

                // Prepare chat welcome message
                var msgs = document.getElementById('chat-messages');
                if (msgs) {
                    msgs.innerHTML = '';
                    var wRow = document.createElement('div');
                    wRow.className = 'bubble-row';
                    var wAv = document.createElement('div');
                    wAv.className = 'bubble-avatar ai-av';
                    wAv.textContent = '✨';
                    var welcome = document.createElement('div');
                    welcome.className = 'bubble-ai';
                    welcome.innerHTML = t.chat_welcome;
                    wRow.appendChild(wAv); wRow.appendChild(welcome);
                    msgs.appendChild(wRow);
                }
            }, 400);

        } catch (e) {
            progressBar.style.display = 'none';
            status.textContent = '❌ Erreur : ' + e.message;
        } finally {
            btn.disabled = false;
        }
    }

    function quickSend(text) {
        document.getElementById('chat-input').value = text;
        sendChat();
    }

    function useChip(btn) {
        var input = document.getElementById('chat-input');
        input.value = btn.textContent;
        input.focus();
    }

    function _hideChatEmpty() {
        var el = document.getElementById('chat-empty');
        if (el) el.style.display = 'none';
    }

    function makeBubble(text, isUser) {
        _hideChatEmpty();
        var row = document.createElement('div');
        row.className = 'bubble-row' + (isUser ? ' user-row' : '');
        var av = document.createElement('div');
        av.className = 'bubble-avatar ' + (isUser ? 'user-av' : 'ai-av');
        av.textContent = isUser ? '👤' : '✨';
        var d = document.createElement('div');
        d.className = isUser ? 'bubble-user' : 'bubble-ai';
        if (isUser) d.textContent = text;
        else d.innerHTML = text;
        row.appendChild(av);
        row.appendChild(d);
        return row;
    }

    async function sendChat() {
        var input = document.getElementById('chat-input');
        var instruction = input.value.trim();
        if (!instruction || !currentSessionId) return;

        var messages = document.getElementById('chat-messages');
        messages.appendChild(makeBubble(instruction, true));
        input.value = '';
        messages.scrollTop = messages.scrollHeight;

        _hideChatEmpty();
        var typingRow = document.createElement('div');
        typingRow.id = 'typing';
        typingRow.className = 'bubble-row';
        var typingAv = document.createElement('div');
        typingAv.className = 'bubble-avatar ai-av';
        typingAv.textContent = '✨';
        var typing = document.createElement('div');
        typing.className = 'bubble-typing';
        typing.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
        typingRow.appendChild(typingAv);
        typingRow.appendChild(typing);
        messages.appendChild(typingRow);
        messages.scrollTop = messages.scrollHeight;

        try {
            var res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: currentSessionId, instruction: instruction })
            });
            var data = await res.json();
            var t = document.getElementById('typing');
            if (t) t.remove();

            if (data.error) {
                var errRow = document.createElement('div');
                errRow.className = 'bubble-row';
                var errAv = document.createElement('div');
                errAv.className = 'bubble-avatar ai-av';
                errAv.textContent = '✨';
                var errBubble = document.createElement('div');
                errBubble.className = 'bubble-error';
                errBubble.innerHTML = '<span style="opacity:0.6;margin-right:6px;">⚠</span>' + data.error;
                errRow.appendChild(errAv); errRow.appendChild(errBubble);
                messages.appendChild(errRow);
                messages.scrollTop = messages.scrollHeight;
            } else if (data.session_id) {
                currentSessionId = data.session_id;
                var dlHref = '/download/' + data.session_id;
                document.getElementById('download-link').href = dlHref;
                addToHistory(data.session_id, data.title, false);
                addResultCard(data.session_id, data.title, false);

                var succRow = document.createElement('div');
                succRow.className = 'bubble-row';
                var succAv = document.createElement('div');
                succAv.className = 'bubble-avatar ai-av';
                succAv.textContent = '✨';
                var bubble = document.createElement('div');
                bubble.className = 'bubble-ai-success';
                var tChat = TRANSLATIONS[currentUILang];
                var html = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                    + '<span style="width:20px;height:20px;background:#0B7A3E;border-radius:5px;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:900;flex-shrink:0;color:white;">✓</span>'
                    + '<span style="color:#0F1D33;font-weight:700;font-size:13px;">' + tChat.chat_done + '</span>'
                    + '</div>'
                    + '<a href="' + dlHref + '" download style="display:inline-flex;align-items:center;gap:6px;padding:8px 16px;background:#0F1D33;color:white;border-radius:6px;font-size:12px;font-weight:700;text-decoration:none;">' + tChat.chat_see + '</a>';
                bubble.innerHTML = html;
                succRow.appendChild(succAv); succRow.appendChild(bubble);
                messages.appendChild(succRow);
                messages.scrollTop = messages.scrollHeight;
            }
        } catch (e) {
            var t2 = document.getElementById('typing');
            if (t2) t2.remove();
            messages.appendChild(makeBubble(TRANSLATIONS[currentUILang].conn_error, false));
        }
    }

    /* ── Aperçu inline ── */
    var inlineSlides = [];
    var inlineIndex = 0;

    async function loadInlinePreview() { /* obsolete */ }
    function renderInlineSlide() { /* obsolete */ }
    function inlinePrevSlide() { /* obsolete */ }
    function inlineNextSlide() { /* obsolete */ }

    /* ── Aperçu modal ── */
    var previewSlides = [];
    var previewCurrentIndex = 0;

    async function openPreview() {
        if (!currentSessionId) { alert("Aucune présentation disponible. Veuillez d'abord générer une présentation."); return; }
        try {
            var res = await fetch('/preview/' + currentSessionId);
            var data = await res.json();
            if (data.error) { alert(data.error); return; }
            var contentSlides = (data.slides_plan && data.slides_plan.slides) ? data.slides_plan.slides : [];
            var presTitle = (data.slides_plan && data.slides_plan.title) ? data.slides_plan.title : 'Aperçu';
            previewSlides = [{type:'cover', title: presTitle}].concat(
                contentSlides.map(function(s){ return {type:'content', title:s.title, bullets:s.bullets}; })
            );
            if (!previewSlides.length) { alert('Aucune slide à afficher.'); return; }
            window._previewSessionId = currentSessionId;
            window._previewHasLogo  = data.has_logo || false;
            document.getElementById('preview-pres-title').textContent = presTitle;
            document.getElementById('preview-dl-btn').href = '/download/' + currentSessionId;
            var colors = data.colors || {};
            _setPreviewColors(
                colors.primary    || '#1E3A5F',
                colors.accent     || '#F97316',
                colors.bg         || '#F8F9FF',
                colors.text       || '#333344',
                colors.title_text || '#FFFFFF'
            );
            previewCurrentIndex = 0;
            renderPreviewSlide();
            document.getElementById('preview-overlay').classList.add('show');
        } catch(e) {
            alert("Erreur lors du chargement de l'aperçu : " + (e.message || e));
        }
    }

    function closePreview() {
        document.getElementById('preview-overlay').classList.remove('show');
    }

    function renderPreviewSlide() {
        if (!previewSlides.length) return;
        var wrap = document.getElementById('preview-slide-wrap');
        wrap.classList.remove('slide-animate');
        void wrap.offsetWidth;
        wrap.classList.add('slide-animate');

        var slide   = previewSlides[previewCurrentIndex];
        var primary = window._previewPrimary    || '#1E3A5F';
        var accent  = window._previewAccent     || '#F97316';
        var bg      = window._previewBg         || '#F8F9FF';
        var txt     = window._previewText       || '#333344';
        var ttl     = window._previewTitleColor || '#FFFFFF';
        var total   = previewSlides.length;
        var idx     = previewCurrentIndex;

        var html = '';
        if (slide.type === 'cover') {
            var today = new Date().toLocaleDateString('fr-FR', {day:'numeric', month:'long', year:'numeric'});
            var logoHtml = (window._previewHasLogo && window._previewSessionId)
                ? '<img src="/logo/' + window._previewSessionId + '" style="position:absolute;top:12px;right:14px;max-width:90px;max-height:55px;object-fit:contain;z-index:3;">'
                : '';
            html = '<div style="width:100%;aspect-ratio:10/7.5;background:' + primary + ';position:relative;border-radius:3px;box-shadow:0 12px 40px rgba(0,0,0,0.5);overflow:hidden;display:flex;flex-direction:column;">'
                + '<div style="position:absolute;left:0;top:0;width:7px;height:100%;background:' + accent + ';z-index:2;"></div>'
                + logoHtml
                + '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px 60px 20px 60px;text-align:center;">'
                + '<div style="font-size:clamp(16px,2.6vw,30px);font-weight:700;color:white;line-height:1.25;">' + _escHtml(slide.title) + '</div>'
                + '<div style="width:60%;height:3px;background:' + accent + ';margin:14px auto;border-radius:2px;"></div>'
                + '<div style="font-size:clamp(10px,1.1vw,13px);color:rgba(200,215,255,0.65);">' + today + '</div>'
                + '</div>'
                + '</div>';
        } else {
            var bulletsHtml = (slide.bullets || []).map(function(b) {
                return '<li style="display:flex;align-items:flex-start;gap:9px;color:' + txt + ';font-size:clamp(10px,1.3vw,14px);line-height:1.5;">'
                    + '<span style="flex-shrink:0;color:' + accent + ';font-size:8px;margin-top:4px;">&#9654;</span>'
                    + '<span>' + _escHtml(b) + '</span>'
                    + '</li>';
            }).join('');
            html = '<div style="width:100%;aspect-ratio:10/7.5;background:' + bg + ';position:relative;border-radius:3px;box-shadow:0 12px 40px rgba(0,0,0,0.5);overflow:hidden;display:flex;flex-direction:column;">'
                + '<div style="position:absolute;left:0;top:0;width:7px;height:100%;background:' + accent + ';z-index:2;"></div>'
                + '<div style="background:' + primary + ';padding:14px 20px 14px 22px;flex-shrink:0;position:relative;">'
                + '<div style="position:absolute;bottom:0;left:0;width:100%;height:3px;background:' + accent + ';"></div>'
                + '<div style="font-size:9px;font-weight:700;color:rgba(204,221,255,0.6);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">SLIDE ' + (idx + 1) + '</div>'
                + '<div style="font-size:clamp(13px,2vw,22px);font-weight:700;color:' + ttl + ';line-height:1.2;">' + _escHtml(slide.title || '') + '</div>'
                + '</div>'
                + '<div style="flex:1;padding:14px 20px 14px 22px;overflow:hidden;display:flex;flex-direction:column;justify-content:center;border-left:4px solid ' + accent + ';">'
                + '<ul style="list-style:none;display:flex;flex-direction:column;gap:8px;">' + bulletsHtml + '</ul>'
                + '</div>'
                + '</div>';
        }
        wrap.innerHTML = html;

        document.getElementById('slide-counter').textContent = (idx + 1) + ' / ' + total;
        document.getElementById('prev-slide-btn').disabled = idx === 0;
        document.getElementById('next-slide-btn').disabled = idx === total - 1;
    }

    function prevSlide() {
        if (previewCurrentIndex > 0) { previewCurrentIndex--; renderPreviewSlide(); }
    }

    function nextSlide() {
        if (previewCurrentIndex < previewSlides.length - 1) { previewCurrentIndex++; renderPreviewSlide(); }
    }

    var pendingReadmeContent = null;

    function showScorePrompt(content) {
        pendingReadmeContent = content;
        document.getElementById('score-question').style.display = 'block';
        document.getElementById('score-card').style.display = 'none';
        document.getElementById('score-overlay').classList.add('show');
    }

    function acceptScorePrompt() {
        document.getElementById('score-question').style.display = 'none';
        var card = document.getElementById('score-card');
        var circle = document.getElementById('score-circle');
        var lbl    = document.getElementById('score-label');
        var badge  = document.getElementById('score-badge');
        var body   = document.getElementById('score-body');
        card.style.display = 'block';
        circle.className = 'score-circle sc-loading';
        circle.textContent = '...';
        lbl.textContent = TRANSLATIONS[currentUILang].score_loading;
        lbl.style.color = '#A0ABBD';
        badge.textContent = '';
        body.innerHTML = '';
        if (pendingReadmeContent) analyzeReadme(pendingReadmeContent);
    }

    function dismissScorePrompt() {
        document.getElementById('score-overlay').classList.remove('show');
        pendingReadmeContent = null;
    }

    async function analyzeReadme(content) {
        var circle = document.getElementById('score-circle');
        var lbl    = document.getElementById('score-label');
        var badge  = document.getElementById('score-badge');
        var scoreBody = document.getElementById('score-body');

        try {
            var res = await fetch('/analyze-readme', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: content})
            });
            var data = await res.json();
            if (data.error) {
                lbl.textContent = 'Erreur : ' + data.error;
                lbl.style.color = 'rgba(239,68,68,0.8)';
                circle.textContent = '!';
                circle.className = 'score-circle sc-faible';
                return;
            }

            var score = parseInt(data.score) || 0;
            var cls   = score >= 8 ? 'sc-excellent' : score >= 6 ? 'sc-bon' : score >= 4 ? 'sc-moyen' : 'sc-faible';
            var color = score >= 8 ? '#0B7A3E' : score >= 6 ? '#B45309' : score >= 4 ? '#B45309' : '#B91C1C';
            var bg    = score >= 8 ? '#E6F4EE' : score >= 6 ? '#FEF3C7' : score >= 4 ? '#FEF3C7' : '#FEE2E2';
            var bd    = score >= 8 ? 'rgba(11,122,62,0.3)' : score >= 6 ? 'rgba(180,83,9,0.3)' : score >= 4 ? 'rgba(180,83,9,0.25)' : 'rgba(185,28,28,0.3)';

            circle.className = 'score-circle ' + cls;
            circle.textContent = score + '/10';
            lbl.textContent = 'Qualité du README';
            lbl.style.color = '#0F1D33';
            badge.textContent = data.label || '';
            badge.style.cssText = 'font-size:11px;padding:3px 10px;border-radius:4px;font-weight:700;background:' + bg + ';color:' + color + ';border:1px solid ' + bd + ';';

            (data.strengths || []).forEach(function(s) {
                var row = document.createElement('div');
                row.style.cssText = 'display:flex;align-items:flex-start;gap:8px;font-size:12px;color:#0B7A3E;line-height:1.5;';
                var icon = document.createElement('span'); icon.textContent = '✓'; icon.style.flexShrink = '0';
                var txt  = document.createElement('span'); txt.textContent = s;
                row.appendChild(icon); row.appendChild(txt); scoreBody.appendChild(row);
            });

            if ((data.suggestions || []).length) {
                var sep = document.createElement('div');
                sep.style.cssText = 'height:1px;background:#D5D8DE;margin:8px 0 6px;';
                scoreBody.appendChild(sep);
                var hint = document.createElement('div');
                hint.textContent = 'Suggestions :';
                hint.style.cssText = 'font-size:10px;font-weight:700;color:#A0ABBD;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;';
                scoreBody.appendChild(hint);
                (data.suggestions || []).forEach(function(s) {
                    var row = document.createElement('div');
                    row.style.cssText = 'display:flex;align-items:flex-start;gap:8px;font-size:12px;color:#4A5568;line-height:1.5;';
                    var icon = document.createElement('span'); icon.textContent = '→'; icon.style.cssText = 'color:#1D4ED8;flex-shrink:0;';
                    var txt  = document.createElement('span'); txt.textContent = s;
                    row.appendChild(icon); row.appendChild(txt); scoreBody.appendChild(row);
                });
            }
            var editWrap = document.getElementById('score-edit-btn-wrap');
            if (editWrap) editWrap.style.display = 'block';
        } catch(e) {
            lbl.textContent = TRANSLATIONS[currentUILang].conn_error;
            lbl.style.color = '#B91C1C';
            circle.textContent = '!';
            circle.className = 'score-circle sc-faible';
        }
    }

    function goToChatFromScore() {
        dismissScorePrompt();
        if (currentSessionId) {
            showTab('chat');
            setTimeout(function() {
                var input = document.getElementById('chat-input');
                if (input) input.focus();
            }, 200);
        } else {
            showTab('upload');
            document.getElementById('btn').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function goToChat() {
        closePreview();
        showTab('chat');
        setTimeout(function() {
            var input = document.getElementById('chat-input');
            if (input) input.focus();
        }, 200);
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/sessions")
def list_sessions():
    """Retourne les métadonnées de toutes les sessions actives pour restaurer l'historique."""
    result = []
    for sid, s in sessions.items():
        result.append({
            "session_id":  sid,
            "title":       s.get("slides_plan", {}).get("title") or s.get("title", "Présentation"),
            "is_zip":      s.get("is_zip", False),
            "created_at":  s.get("created_at", ""),
        })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return JSONResponse(result)


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id in sessions:
        sessions.pop(session_id)
        save_sessions()
    return JSONResponse({"ok": True})


@app.post("/fetch-readme")
async def fetch_readme(body: dict):
    import re
    import httpx

    url = body.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "URL manquante"}, status_code=400)

    match = re.match(r'https?://github\.com/([^/]+)/([^/?#]+)', url)
    if not match:
        return JSONResponse(
            {"error": "URL GitHub invalide. Format attendu : https://github.com/user/repo"},
            status_code=400
        )

    owner, repo = match.group(1), match.group(2).rstrip("/")

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for branch in ["main", "master"]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            try:
                r = await client.get(raw_url)
                if r.status_code == 200 and r.text.strip():
                    return JSONResponse({"content": r.text, "repo": f"{owner}/{repo}", "branch": branch})
            except Exception:
                continue

    return JSONResponse(
        {"error": f"README introuvable dans {owner}/{repo} (branches main et master essayées)"},
        status_code=404
    )

@app.post("/generate")
async def generate(file: UploadFile = File(...), lang: str = Form("auto"), audience: str = Form("developer"), logo: UploadFile = File(None)):
    try:
        content = await file.read()
        readme_content = content.decode("utf-8", errors="replace")
    except Exception as e:
        return JSONResponse({"error": f"Erreur lecture fichier : {str(e)}"}, status_code=400)

    logo_path = None
    if logo and logo.filename:
        logo_bytes = await logo.read()
        # Vérifier le vrai format via Pillow
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(logo_bytes))
            fmt = img.format  # PNG, JPEG, BMP, GIF, TIFF...
            supported = {"PNG", "JPEG", "BMP", "GIF", "TIFF"}
            if fmt not in supported:
                return JSONResponse(
                    {"error": f"Format image non supporté ({fmt}). Utilisez PNG ou JPG."},
                    status_code=400
                )
            # Convertir en PNG pour éviter tout problème de compatibilité
            os.makedirs("output", exist_ok=True)
            logo_path = f"output/logo_{uuid.uuid4().hex[:8]}.png"
            img.save(logo_path, "PNG")
        except Exception as e:
            return JSONResponse(
                {"error": f"Image invalide ou format non supporté. Utilisez PNG ou JPG."},
                status_code=400
            )

    try:
        graph = build_graph()
        session_id = str(uuid.uuid4())

        if lang == "both":
            result_fr = graph.invoke({"readme_content": readme_content, "lang": "fr", "audience": audience, "logo_path": logo_path})
            result_en = graph.invoke({"readme_content": readme_content, "lang": "en", "audience": audience, "logo_path": logo_path})
            os.makedirs("output", exist_ok=True)
            zip_path = f"output/presentation_FR_EN_{session_id[:8]}.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.write(result_fr["output_path"], "presentation_FR.pptx")
                zf.write(result_en["output_path"], "presentation_EN.pptx")
            sessions[session_id] = {
                "slides_plan": result_fr["slides_plan"],
                "readme_content": readme_content,
                "lang": "fr", "audience": audience,
                "logo_path": logo_path, "design_params": {},
                "output_path": zip_path, "is_zip": True,
                "effective_colors": result_fr.get("effective_colors", {}),
                "created_at": datetime.now().isoformat(),
            }
        else:
            result = graph.invoke({"readme_content": readme_content, "lang": lang, "audience": audience, "logo_path": logo_path})
            sessions[session_id] = {
                "slides_plan": result["slides_plan"],
                "readme_content": readme_content,
                "lang": lang, "audience": audience,
                "logo_path": logo_path, "design_params": {},
                "output_path": result["output_path"], "is_zip": False,
                "effective_colors": result.get("effective_colors", {}),
                "created_at": datetime.now().isoformat(),
            }

        save_sessions()
        title = sessions[session_id].get("slides_plan", {}).get("title", "Présentation")
        return JSONResponse({"session_id": session_id, "is_zip": sessions[session_id]["is_zip"], "title": title})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Erreur génération : {str(e)}"}, status_code=500)


@app.get("/download/{session_id}")
def download(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session introuvable"}, status_code=404)
    if session.get("is_zip"):
        return FileResponse(
            session["output_path"],
            media_type="application/zip",
            filename="presentations_FR_EN.zip"
        )
    return FileResponse(
        session["output_path"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="presentation.pptx"
    )


@app.post("/analyze-readme")
async def analyze_readme_quality(body: dict):
    import json as _json, re as _re
    from agents.utils import groq_client, USE_LLM

    content = body.get("content", "").strip()
    if not content:
        return JSONResponse({"error": "Contenu vide"}, status_code=400)

    if not USE_LLM or groq_client is None:
        return JSONResponse({
            "score": 5, "label": "Moyen",
            "strengths": ["Contenu présent"],
            "suggestions": ["Ajoutez une description claire", "Ajoutez des instructions d'installation", "Ajoutez des exemples"]
        })

    try:
        prompt = f"""Analyze this README quality. Return ONLY this JSON (no extra text):
{{
  "score": <integer 0-10>,
  "label": "<Excellent|Bon|Moyen|Faible>",
  "strengths": ["<point fort 1>", "<point fort 2>"],
  "suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"]
}}
Rules: score 8-10=Excellent, 6-7=Bon, 4-5=Moyen, 0-3=Faible. Use same language as README.

README:
{content[:3000]}"""

        models = ["anthropic/claude-haiku-4-5", "google/gemini-2.5-flash"]
        for model in models:
            try:
                resp = groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a README quality expert. Reply ONLY with valid JSON."},
                        {"role": "user",   "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.2
                )
                raw = resp.choices[0].message.content
                m = _re.search(r'\{.*\}', raw, _re.DOTALL)
                if not m:
                    raise ValueError("No JSON in response")
                return JSONResponse(_json.loads(m.group(0)))
            except Exception as e:
                if "rate" in str(e).lower() or "429" in str(e):
                    continue
                raise
        return JSONResponse({"error": "Rate limit atteint, réessayez dans quelques minutes."}, status_code=429)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/preview/{session_id}")
def preview_slides(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session introuvable"}, status_code=404)
    logo_path = session.get("logo_path")
    has_logo = bool(logo_path and os.path.exists(logo_path))
    return JSONResponse({
        "slides_plan": session.get("slides_plan", {}),
        "is_zip": session.get("is_zip", False),
        "colors": session.get("effective_colors", {}),
        "has_logo": has_logo,
    })


@app.get("/logo/{session_id}")
def get_logo(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session introuvable"}, status_code=404)
    logo_path = session.get("logo_path")
    if not logo_path or not os.path.exists(logo_path):
        return JSONResponse({"error": "Pas de logo"}, status_code=404)
    return FileResponse(logo_path, media_type="image/png")


@app.post("/chat")
async def chat(body: dict):
    session_id = body.get("session_id")
    instruction = body.get("instruction", "")

    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session introuvable"}, status_code=404)

    state = {**session, "instruction": instruction}
    new_state = chat_agent(state)

    actions = new_state.get("chat_actions", [])
    chat_error = new_state.get("chat_error", "")

    # Si aucun outil n'a été appelé, ne pas régénérer le PPTX
    if not actions:
        if chat_error:
            return JSONResponse({"error": f"Erreur IA : {chat_error}"}, status_code=500)
        return JSONResponse({"error": "Je n'ai pas compris la modification. Soyez plus précis (ex: 'change la couleur du fond en bleu', 'mets le titre de la slide 2 en majuscules')."}, status_code=400)

    new_state = branding_agent(new_state)
    new_state = pptx_agent(new_state)

    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        "slides_plan":     new_state["slides_plan"],
        "readme_content":  session.get("readme_content", ""),
        "lang":            session["lang"],
        "audience":        session["audience"],
        "logo_path":       session["logo_path"],
        "design_params":   new_state.get("design_params", {}),
        "pptx_code":       new_state.get("pptx_code"),
        "output_path":     new_state["output_path"],
        "is_zip":          False,
        "effective_colors": new_state.get("effective_colors", {}),
        "created_at":      datetime.now().isoformat(),
    }
    save_sessions()

    tool_labels = {
        "change_colors": "couleurs modifiées",
        "change_fonts": "police modifiée",
        "change_sizes": "taille modifiée",
        "change_bullet_style": "style de puces modifié",
        "change_title_style": "style du titre modifié",
        "set_theme": "thème appliqué",
        "change_logo_position": "position du logo modifiée",
        "change_cover_title": "titre de couverture modifié",
        "add_slide": "slide ajoutée",
        "delete_slide": "slide supprimée",
        "edit_slide": "slide modifiée",
        "reorder_slides": "slides réordonnées",
    }
    details = " · ".join(tool_labels.get(a, a) for a in actions)

    title = new_state["slides_plan"].get("title", "Présentation")
    return JSONResponse({
        "session_id": new_session_id,
        "message": f"✅ {details}",
        "title": title,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
