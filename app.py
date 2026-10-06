import os
import hmac
import hashlib
import html
import json
import asyncio
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

app = FastAPI(title="Acima do Comum AI Studio")

PASSWORD = os.getenv("ADC_PANEL_PASSWORD", "").strip()
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("ADC_GEMINI_MODEL", "gemini-3.8-flash")

def auth_token():
    return hashlib.sha256(("adc:" + PASSWORD).encode()).hexdigest()

def is_auth(request: Request):
    return bool(PASSWORD) and hmac.compare_digest(request.cookies.get("adc_auth",""), auth_token())

class ResearchPlan(BaseModel):
    angle: str
    audience: str
    claims_to_verify: list[str] = []
    source_targets: list[str] = []
    risks: list[str] = []
    recommended_structure: list[str] = []

class ScriptDraft(BaseModel):
    title: str
    hook: str
    script: str
    estimated_seconds: int = Field(ge=15, le=1800)
    scenes: list[str] = []
    factual_claims: list[str] = []

class CriticScore(BaseModel):
    hook: int = Field(ge=0, le=100)
    retention: int = Field(ge=0, le=100)
    narrative: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    credibility: int = Field(ge=0, le=100)
    critical_issues: list[str] = []
    revision_instructions: list[str] = []

    @property
    def average(self):
        return round((self.hook+self.retention+self.narrative+self.clarity+self.credibility)/5)

class VoicePlan(BaseModel):
    voice_profile: str
    pace: str
    energy: str
    pauses: list[str] = []
    pronunciation_notes: list[str] = []
    anti_robotic_rules: list[str] = []

class Shot(BaseModel):
    index: int
    narration_excerpt: str
    visual: str
    camera_motion: str
    on_screen_text: str = ""
    duration_seconds: float

class Storyboard(BaseModel):
    format: str
    visual_style: str
    shots: list[Shot] = []

class WatcherReport(BaseModel):
    narrative_score: int = Field(ge=0, le=100)
    voice_risk_score: int = Field(ge=0, le=100)
    visual_consistency_score: int = Field(ge=0, le=100)
    factual_risk_score: int = Field(ge=0, le=100)
    critical_failures: list[str] = []
    qa_checklist: list[str] = []
    corrections: list[str] = []

RADAR_SYSTEM = """Você é ADC Radar, pesquisador-chefe do Acima do Comum.
Transforme o brief em plano editorial verificável. Nunca invente dados.
Liste fatos que precisam ser confirmados, fontes ideais, riscos, ângulo e estrutura de retenção.
Se não houver fonte disponível no contexto, trate como algo a verificar, nunca como fato confirmado."""

STORY_SYSTEM = """Você é ADC Story, roteirista profissional do Acima do Comum.
Escreva em português brasileiro natural, cinematográfico e de alta retenção.
Nunca comece com enumeração burocrática nem com 'você sabia?' automático.
Abra com tensão, contraste, surpresa ou curiosidade real.
Cada bloco deve acrescentar informação. Não invente fatos.
Escreva para narração fluida e humana, evitando cadência de TTS."""

CRITIC_SYSTEM = """Você é ADC Critic e deve ser rigoroso e independente.
Avalie hook, retention, narrative, clarity e credibility de 0 a 100.
Reprove abertura fraca, repetição, clickbait enganoso, afirmação sem sustentação,
tom robótico, estrutura mecânica e conclusão frouxa.
Nunca aumente nota só para liberar o fluxo."""

VOICE_SYSTEM = """Você é ADC Voice Director.
Crie direção de voz natural, comum em documentários, curiosidades e narrativas profissionais.
Use ritmo variável, pausas orgânicas, ênfases discretas e pronúncia clara.
Evite fala picotada, pausas artificiais, excesso de dramaticidade e cadência robótica."""

DIRECTOR_SYSTEM = """Você é ADC Director.
Converta o roteiro em storyboard vertical profissional.
Cada cena deve acompanhar a narração, variar visualmente e evitar repetição.
Use movimentos de câmera apenas quando fizerem sentido.
Evite cenas genéricas que não correspondam ao texto."""

WATCHER_SYSTEM = """Você é ADC Watcher, auditor final independente.
Tente encontrar falhas antes de qualquer renderização.
Seja rigoroso com possíveis travamentos de áudio, frases difíceis de narrar,
cenas repetidas, inconsistência visual, fatos frágeis, ritmo ruim, silêncios
acidentais e aparência artificial excessiva. Falha crítica deve bloquear."""

def ask_structured(system_instruction: str, prompt: str, schema):
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.6,
        ),
    )
    if response.parsed is not None:
        return response.parsed
    return schema.model_validate_json(response.text)

async def run_agent(system_instruction: str, prompt: str, schema):
    return await asyncio.to_thread(ask_structured, system_instruction, prompt, schema)

def gate_passes(score: CriticScore) -> bool:
    return score.average >= 85 and score.hook >= 90 and score.credibility >= 95 and not score.critical_issues

async def run_pipeline(brief: str):
    research = await run_agent(RADAR_SYSTEM, f"BRIEF:\n{brief}", ResearchPlan)
    draft = await run_agent(STORY_SYSTEM, "BRIEF:\n"+brief+"\nPLANO:\n"+research.model_dump_json(), ScriptDraft)
    review = await run_agent(CRITIC_SYSTEM, "Avalie rigorosamente:\n"+draft.model_dump_json(), CriticScore)
    revision_count = 0
    while not gate_passes(review) and revision_count < 2:
        revision_count += 1
        draft = await run_agent(
            STORY_SYSTEM,
            "Reescreva corrigindo esta crítica:\n"+review.model_dump_json()
            +"\nROTEIRO:\n"+draft.model_dump_json()
            +"\nPLANO:\n"+research.model_dump_json(),
            ScriptDraft,
        )
        review = await run_agent(CRITIC_SYSTEM, "Reavalie do zero:\n"+draft.model_dump_json(), CriticScore)
    if not gate_passes(review):
        return {"research":research,"script":draft,"critic":review,"revision_count":revision_count,"blocked":True,"voice":None,"storyboard":None,"watcher":None}
    voice = await run_agent(VOICE_SYSTEM, "ROTEIRO:\n"+draft.model_dump_json(), VoicePlan)
    board = await run_agent(DIRECTOR_SYSTEM, "ROTEIRO:\n"+draft.model_dump_json()+"\nVOZ:\n"+voice.model_dump_json(), Storyboard)
    watcher = await run_agent(WATCHER_SYSTEM, "ROTEIRO:\n"+draft.model_dump_json()+"\nVOZ:\n"+voice.model_dump_json()+"\nSTORYBOARD:\n"+board.model_dump_json(), WatcherReport)
    blocked = bool(watcher.critical_failures) or watcher.narrative_score < 90 or watcher.factual_risk_score > 15
    return {"research":research,"script":draft,"critic":review,"revision_count":revision_count,"blocked":blocked,"voice":voice,"storyboard":board,"watcher":watcher}

CSS = """
body{font-family:Arial,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:24px}
.wrap{max-width:900px;margin:auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:20px;margin:16px 0}
input,textarea{width:100%;box-sizing:border-box;background:#0d1117;color:#fff;border:1px solid #444;border-radius:10px;padding:12px;font-size:16px}
button{background:#7c3aed;color:#fff;border:0;border-radius:10px;padding:12px 18px;font-size:16px;font-weight:bold}
h1,h2,h3{margin-top:0}.muted{color:#8b949e}.ok{color:#3fb950}.bad{color:#f85149}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.metric{background:#0d1117;border-radius:10px;padding:12px}
pre{white-space:pre-wrap;word-wrap:break-word;background:#0d1117;padding:14px;border-radius:10px;overflow:auto}
@media(max-width:700px){.grid{grid-template-columns:1fr 1fr}body{padding:14px}}
"""

def page(body):
    return HTMLResponse(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Acima do Comum AI Studio</title><style>{CSS}</style></head><body><div class="wrap">{body}</div></body></html>""")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not PASSWORD:
        return page('<div class="card"><h2>Configuração incompleta</h2><p>ADC_PANEL_PASSWORD não configurada.</p></div>')
    if not is_auth(request):
        return page("""<div class="card"><h1>🔒 Acima do Comum</h1><p class="muted">Acesso privado</p>
        <form method="post" action="/login"><input type="password" name="password" placeholder="Senha" required><br><br>
        <button type="submit">Entrar</button></form></div>""")
    status = '<span class="ok">Gemini configurado</span>' if API_KEY else '<span class="bad">GEMINI_API_KEY ausente</span>'
    return page(f"""<div class="card"><h1>🎬 Acima do Comum — AI Studio</h1>
    <p class="muted">V0.6 • Radar → Story → Critic → Voice Director → Director → Watcher</p>
    <p>{status}</p></div>
    <div class="card"><form method="post" action="/produce">
    <label>O que vamos produzir?</label><br><br>
    <textarea name="brief" rows="7" placeholder="Ex.: vídeo vertical de 60 segundos sobre um mistério histórico brasileiro." required></textarea><br><br>
    <button type="submit">Iniciar produção</button></form></div>""")

@app.post("/login")
async def login(password: str = Form(...)):
    if PASSWORD and hmac.compare_digest(password, PASSWORD):
        r = RedirectResponse("/", status_code=303)
        r.set_cookie("adc_auth", auth_token(), httponly=True, secure=True, samesite="lax", max_age=60*60*24*30)
        return r
    return page('<div class="card"><h2>Senha incorreta</h2><a href="/">Voltar</a></div>')

@app.post("/produce", response_class=HTMLResponse)
async def produce(request: Request, brief: str = Form(...)):
    if not is_auth(request):
        return RedirectResponse("/", status_code=303)
    if not API_KEY:
        return page('<div class="card"><h2>GEMINI_API_KEY ausente</h2><p>Configure no Render.</p><a href="/">Voltar</a></div>')
    try:
        result = await run_pipeline(brief.strip())
    except Exception as exc:
        return page('<div class="card"><h2>Falha no pipeline</h2><pre>'+html.escape(str(exc))+'</pre><a href="/">Voltar</a></div>')
    s=result["script"]; c=result["critic"]
    metrics = "".join([f'<div class="metric"><b>{k}</b><br>{v}</div>' for k,v in [
        ("Gancho",c.hook),("Retenção",c.retention),("Narrativa",c.narrative),
        ("Clareza",c.clarity),("Credibilidade",c.credibility),("ADC Score",c.average)]])
    def dump(x): return html.escape(json.dumps(x.model_dump(), ensure_ascii=False, indent=2)) if x else "Bloqueado"
    final = '<p class="bad"><b>⛔ BLOQUEADO PELO QA</b></p>' if result["blocked"] else '<p class="ok"><b>✅ PRÉ-PRODUÇÃO APROVADA</b></p>'
    return page(f"""<div class="card"><a href="/">← Novo projeto</a><h1>{html.escape(s.title)}</h1>
    <h3>Gancho</h3><p>{html.escape(s.hook)}</p><div class="grid">{metrics}</div>{final}</div>
    <div class="card"><h2>Roteiro</h2><p>{html.escape(s.script).replace(chr(10),'<br>')}</p><p class="muted">Revisões automáticas: {result["revision_count"]}</p></div>
    <div class="card"><h2>Radar</h2><pre>{dump(result["research"])}</pre></div>
    <div class="card"><h2>Voz</h2><pre>{dump(result["voice"])}</pre></div>
    <div class="card"><h2>Storyboard</h2><pre>{dump(result["storyboard"])}</pre></div>
    <div class="card"><h2>Watcher</h2><pre>{dump(result["watcher"])}</pre></div>""")

@app.get("/health")
async def health():
    return {"ok": True, "provider": "gemini", "key_configured": bool(API_KEY)}
