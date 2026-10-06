import asyncio
import os
import hmac
import json
import streamlit as st
from agents import Agent, Runner
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

model = os.getenv("ADC_MODEL", "gpt-5")

radar = Agent(
    name="ADC Radar",
    model=model,
    instructions="""Você é o pesquisador-chefe do Acima do Comum.
Transforme o brief em plano editorial verificável. Não invente dados.
Separe o que precisa ser confirmado, quais fontes seriam ideais,
riscos factuais, melhor ângulo e estrutura de retenção.""",
    output_type=ResearchPlan,
)

story = Agent(
    name="ADC Story",
    model=model,
    instructions="""Você é ADC Story, roteirista do Acima do Comum.
Escreva em português brasileiro natural, cinematográfico e de alta retenção.
Nunca abra com enumeração burocrática, frases genéricas ou 'você sabia?' automático.
O início precisa gerar tensão, contraste, surpresa ou curiosidade real.
Cada bloco deve entregar informação nova. Não invente fatos.
Adapte o texto para narração fluida, evitando construções que soem robóticas.""",
    output_type=ScriptDraft,
)

critic = Agent(
    name="ADC Critic",
    model=model,
    instructions="""Você é um crítico independente e não pode aprovar por gentileza.
Avalie de 0 a 100 hook, retention, narrative, clarity e credibility.
Reprove abertura fraca, repetição, clickbait enganoso, afirmação não sustentada,
tom robótico, estrutura mecânica ou conclusão frouxa.
Liste problemas críticos e instruções objetivas de revisão.""",
    output_type=CriticScore,
)

voice = Agent(
    name="ADC Voice Director",
    model=model,
    instructions="""Você dirige narração profissional para vídeos de segmento.
Crie direção de voz natural e comum em documentários, curiosidades e histórias:
ritmo variável, pausas orgânicas, ênfases discretas e pronúncia clara.
Evite fala picotada, aceleração artificial, pausas em lugares errados
e cadência de TTS robótico.""",
    output_type=VoicePlan,
)

director = Agent(
    name="ADC Director",
    model=model,
    instructions="""Você é diretor audiovisual do Acima do Comum.
Converta roteiro em storyboard vertical profissional. Cada cena deve corresponder
à narração, variar visualmente e evitar repetição. Prefira imagens factualmente
compatíveis. Use cortes e movimentos com propósito, não efeitos aleatórios.""",
    output_type=Storyboard,
)

watcher = Agent(
    name="ADC Watcher",
    model=model,
    instructions="""Você é o auditor final independente.
Analise roteiro, direção de voz e storyboard e tente encontrar falhas antes
de qualquer renderização cara. Seja rigoroso com travamento potencial de áudio,
frases difíceis de narrar, cenas repetidas, descompasso visual, fatos frágeis,
ritmo ruim, silêncios acidentais e risco de geração artificial evidente.
Qualquer falha crítica deve bloquear a liberação.""",
    output_type=WatcherReport,
)

def gate_passes(score: CriticScore) -> bool:
    return score.average >= 85 and score.hook >= 90 and score.credibility >= 95 and not score.critical_issues

async def run_pipeline(brief: str):
    research = (await Runner.run(radar, f"BRIEF:\n{brief}")).final_output

    draft = (await Runner.run(
        story,
        "BRIEF:\n" + brief + "\nPLANO DE PESQUISA:\n" + research.model_dump_json()
    )).final_output

    review = (await Runner.run(
        critic,
        "Avalie rigorosamente este roteiro:\n" + draft.model_dump_json()
    )).final_output

    revision_count = 0
    while not gate_passes(review) and revision_count < 2:
        revision_count += 1
        draft = (await Runner.run(
            story,
            "Reescreva o roteiro corrigindo integralmente a crítica abaixo. "
            "Não maquie nota; resolva os problemas de verdade.\n"
            + review.model_dump_json()
            + "\nROTEIRO ATUAL:\n"
            + draft.model_dump_json()
            + "\nPLANO:\n"
            + research.model_dump_json()
        )).final_output
        review = (await Runner.run(
            critic,
            "Reavalie do zero, sem considerar notas anteriores:\n" + draft.model_dump_json()
        )).final_output

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

    voice_plan = (await Runner.run(
        voice,
        "Crie direção de voz para este roteiro:\n" + draft.model_dump_json()
    )).final_output

    board = (await Runner.run(
        director,
        "Crie storyboard para este roteiro e direção de voz:\nROTEIRO:\n"
        + draft.model_dump_json()
        + "\nVOZ:\n"
        + voice_plan.model_dump_json()
    )).final_output

    qa = (await Runner.run(
        watcher,
        "Audite este pacote de pré-produção:\nROTEIRO:\n"
        + draft.model_dump_json()
        + "\nVOZ:\n"
        + voice_plan.model_dump_json()
        + "\nSTORYBOARD:\n"
        + board.model_dump_json()
    )).final_output

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
st.caption("V0.4 • Radar → Story → Critic → Voice Director → Director → Watcher")

with st.sidebar:
    st.markdown("### ADC Quality Gate")
    st.write("Roteiro ≥ 85")
    st.write("Gancho ≥ 90")
    st.write("Credibilidade ≥ 95")
    st.write("Watcher sem falha crítica")
    st.divider()
    st.caption("O sistema não envia mídia para renderização se a pré-produção falhar.")

brief = st.text_area(
    "O que vamos produzir?",
    placeholder="Ex.: vídeo vertical de 60 segundos sobre um mistério histórico brasileiro.",
    height=150,
)

if st.button("Iniciar produção", type="primary", disabled=not brief.strip()):
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY ainda não foi configurada no Render.")
        st.stop()

    with st.status("ADC executando pipeline...", expanded=True) as status:
        result = asyncio.run(run_pipeline(brief.strip()))
        status.update(
            label="Pipeline concluído" if not result["blocked"] else "Pipeline bloqueado pelo QA",
            state="complete" if not result["blocked"] else "error",
        )

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
        if result["voice"]:
            st.json(result["voice"].model_dump())
        else:
            st.warning("Não liberado porque o roteiro não passou no Quality Gate.")

    with tabs[3]:
        if result["storyboard"]:
            st.json(result["storyboard"].model_dump())
        else:
            st.warning("Storyboard não gerado porque o roteiro foi bloqueado.")

    with tabs[4]:
        if result["watcher"]:
            st.json(result["watcher"].model_dump())
        else:
            st.warning("Watcher final não executado porque a etapa anterior foi bloqueada.")

    if result["blocked"]:
        st.error("⛔ ADC BLOQUEOU este projeto. Ele precisa de correção antes da geração de mídia.")
    else:
        st.success("✅ Pré-produção aprovada. Pronto para a camada de voz, cenas e renderização.")
