import asyncio
import os
import hmac
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

class ScriptDraft(BaseModel):
    title: str
    hook: str
    script: str
    estimated_seconds: int = Field(ge=15, le=1800)

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

model = os.getenv("ADC_MODEL", "gpt-5")

story = Agent(
    name="ADC Story",
    model=model,
    instructions="""Você é ADC Story, roteirista do Acima do Comum.
Escreva em português brasileiro natural, com alta retenção.
Nunca comece com enumeração burocrática. O gancho deve criar tensão, contraste
ou curiosidade real. Não invente fatos.""",
    output_type=ScriptDraft,
)

critic = Agent(
    name="ADC Critic",
    model=model,
    instructions="""Avalie de 0 a 100 hook, retention, narrative, clarity e credibility.
Se houver fato suspeito ou certeza indevida, reduza credibility.
Liste problemas críticos e instruções objetivas de revisão.""",
    output_type=CriticScore,
)

async def produce(brief: str):
    first = await Runner.run(story, f"BRIEF:\n{brief}\nCrie o roteiro.")
    script = first.final_output
    review = await Runner.run(critic, f"Avalie rigorosamente:\n{script.model_dump_json()}")
    score = review.final_output
    if score.average < 85 or score.hook < 90 or score.credibility < 95 or score.critical_issues:
        revised = await Runner.run(
            story,
            "Reescreva corrigindo integralmente estes problemas:\n"
            + score.model_dump_json()
            + "\nROTEIRO:\n"
            + script.model_dump_json(),
        )
        script = revised.final_output
        review = await Runner.run(critic, f"Reavalie rigorosamente:\n{script.model_dump_json()}")
        score = review.final_output
    return script, score

st.title("🎬 Acima do Comum — AI Studio")
st.caption("ADC Story + ADC Critic • Quality Gate automático")

brief = st.text_area(
    "O que vamos produzir?",
    placeholder="Ex.: vídeo vertical de 60 segundos sobre um mistério histórico brasileiro.",
    height=150,
)

if st.button("Iniciar produção", type="primary", disabled=not brief.strip()):
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY ainda não foi configurada no Render.")
        st.stop()
    with st.status("ADC trabalhando...", expanded=True) as status:
        script, score = asyncio.run(produce(brief.strip()))
        status.update(label="Análise concluída", state="complete")
    st.subheader(script.title)
    st.markdown("### Gancho")
    st.write(script.hook)
    st.markdown("### Roteiro")
    st.write(script.script)
    cols = st.columns(6)
    vals = [score.hook, score.retention, score.narrative, score.clarity, score.credibility, score.average]
    labs = ["Gancho","Retenção","Narrativa","Clareza","Credibilidade","ADC Score"]
    for c,l,v in zip(cols,labs,vals):
        c.metric(l,v)
    if score.critical_issues:
        st.error("Problemas críticos: " + "; ".join(score.critical_issues))
