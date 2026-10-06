import asyncio
import os
import hmac
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

st.set_page_config(page_title="Acima do Comum AI Studio", page_icon="🎬", layout="wide")

PASSWORD = os.getenv("ADC_PANEL_PASSWORD", "").strip()
if not PASSWORD:
    st.error("ADC_PANEL_PASSWORD não configurada.")
    st.stop()

if not st.session_state.get("adc_authenticated"):
    st.title("🔒 Acima do Comum — acesso privado")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(pwd, PASSWORD):
            st.session_state["adc_authenticated"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

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

MODEL = os.getenv("ADC_GEMINI_MODEL", "gemini-3.8-flash")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

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

def gate_passes(score: CriticScore) -> bool:
    return score.average >= 85 and score.hook >= 90 and score.credibility >= 95 and not score.critical_issues

async def run_pipeline(brief: str):
    research = await run_agent(RADAR_SYSTEM, f"BRIEF:\n{brief}", ResearchPlan)

    draft = await run_agent(
        STORY_SYSTEM,
        "BRIEF:\n" + brief + "\nPLANO DE PESQUISA:\n" + research.model_dump_json(),
        ScriptDraft,
    )

    review = await run_agent(
        CRITIC_SYSTEM,
        "Avalie rigorosamente este roteiro:\n" + draft.model_dump_json(),
        CriticScore,
    )

    revision_count = 0
    while not gate_passes(review) and revision_count < 2:
        revision_count += 1
        draft = await run_agent(
            STORY_SYSTEM,
            "Reescreva o roteiro corrigindo integralmente esta crítica. "
            "Não maquie nota; resolva os problemas.\nCRÍTICA:\n"
            + review.model_dump_json()
            + "\nROTEIRO ATUAL:\n"
            + draft.model_dump_json()
            + "\nPLANO:\n"
            + research.model_dump_json(),
            ScriptDraft,
        )
        review = await run_agent(
            CRITIC_SYSTEM,
            "Reavalie do zero, ignorando as notas anteriores:\n" + draft.model_dump_json(),
            CriticScore,
        )

    if not gate_passes(review):
        return {
            "research": research,
            "script": draft,
            "critic": review,
            "revision_count": revision_count,
            "blocked": True,
            "voice": None,
            "storyboard": None,
            "watcher": None,
        }

    voice_plan = await run_agent(
        VOICE_SYSTEM,
        "Crie direção de voz para este roteiro:\n" + draft.model_dump_json(),
        VoicePlan,
    )

    board = await run_agent(
        DIRECTOR_SYSTEM,
        "Crie o storyboard para:\nROTEIRO:\n"
        + draft.model_dump_json()
        + "\nVOZ:\n"
        + voice_plan.model_dump_json(),
        Storyboard,
    )

    qa = await run_agent(
        WATCHER_SYSTEM,
        "Audite o pacote de pré-produção:\nROTEIRO:\n"
        + draft.model_dump_json()
        + "\nVOZ:\n"
        + voice_plan.model_dump_json()
        + "\nSTORYBOARD:\n"
        + board.model_dump_json(),
        WatcherReport,
    )

    blocked = bool(qa.critical_failures) or qa.narrative_score < 90 or qa.factual_risk_score > 15

    return {
        "research": research,
        "script": draft,
        "critic": review,
        "revision_count": revision_count,
        "blocked": blocked,
        "voice": voice_plan,
        "storyboard": board,
        "watcher": qa,
    }

st.title("🎬 Acima do Comum — AI Studio")
st.caption("V0.5 • Gemini Free • Radar → Story → Critic → Voice Director → Director → Watcher")

with st.sidebar:
    st.markdown("### Motor")
    st.success("Gemini API")
    st.caption(MODEL)
    st.markdown("### ADC Quality Gate")
    st.write("Roteiro ≥ 85")
    st.write("Gancho ≥ 90")
    st.write("Credibilidade ≥ 95")
    st.write("Watcher sem falha crítica")
    st.divider()
    st.caption("Nada segue para mídia se a pré-produção falhar.")

brief = st.text_area(
    "O que vamos produzir?",
    placeholder="Ex.: vídeo vertical de 60 segundos sobre um mistério histórico brasileiro.",
    height=150,
)

if st.button("Iniciar produção", type="primary", disabled=not brief.strip()):
    if not API_KEY:
        st.error("GEMINI_API_KEY ainda não foi configurada no Render.")
        st.info("A conta gratuita da Gemini API pode ser usada; basta inserir a chave como variável secreta.")
        st.stop()

    try:
        with st.status("ADC executando pipeline...", expanded=True) as status:
            result = asyncio.run(run_pipeline(brief.strip()))
            status.update(
                label="Pipeline concluído" if not result["blocked"] else "Pipeline bloqueado pelo QA",
                state="complete" if not result["blocked"] else "error",
            )
    except Exception as exc:
        st.error("Falha ao executar o pipeline Gemini.")
        st.code(str(exc))
        st.stop()

    research = result["research"]
    script = result["script"]
    score = result["critic"]

    st.subheader(script.title)
    st.markdown("### Gancho")
    st.write(script.hook)

    cols = st.columns(6)
    vals = [score.hook, score.retention, score.narrative, score.clarity, score.credibility, score.average]
    labs = ["Gancho", "Retenção", "Narrativa", "Clareza", "Credibilidade", "ADC Score"]
    for c, lab, val in zip(cols, labs, vals):
        c.metric(lab, val)

    tabs = st.tabs(["Roteiro", "Radar", "Voz", "Storyboard", "Watcher"])
    with tabs[0]:
        st.write(script.script)
        st.caption(f"Revisões automáticas: {result['revision_count']}")
    with tabs[1]:
        st.json(research.model_dump())
    with tabs[2]:
        st.json(result["voice"].model_dump()) if result["voice"] else st.warning("Bloqueado pelo Quality Gate.")
    with tabs[3]:
        st.json(result["storyboard"].model_dump()) if result["storyboard"] else st.warning("Bloqueado pelo Quality Gate.")
    with tabs[4]:
        st.json(result["watcher"].model_dump()) if result["watcher"] else st.warning("Watcher não executado.")

    if result["blocked"]:
        st.error("⛔ ADC BLOQUEOU este projeto. Corrija antes da geração de mídia.")
    else:
        st.success("✅ Pré-produção aprovada. Pronto para voz, cenas e renderização.")
