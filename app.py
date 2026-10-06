import os, hmac, hashlib, html, json, asyncio, uuid, tempfile, shutil, subprocess, re
from pathlib import Path
import requests
import edge_tts
import imageio_ffmpeg
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

app = FastAPI(title="Acima do Comum AI Studio")
PASSWORD = os.getenv("ADC_PANEL_PASSWORD","").strip()
API_KEY = os.getenv("GEMINI_API_KEY","").strip()
MODEL = os.getenv("ADC_GEMINI_MODEL","gemini-2.5-flash-lite")
FALLBACK_MODELS = [MODEL,"gemini-2.5-flash-lite","gemini-2.5-flash"]
VOICE = os.getenv("ADC_TTS_VOICE","pt-BR-AntonioNeural")
SELFTEST_TOKEN = os.getenv("ADC_SELFTEST_TOKEN","").strip()
JOBS = {}
SELFTESTS = {}\nSELFTEST_AUTO = os.getenv("ADC_SELFTEST_AUTO","0") == "1"

def auth_token():
    return hashlib.sha256(("adc:"+PASSWORD).encode()).hexdigest()

def is_auth(request):
    return bool(PASSWORD) and hmac.compare_digest(request.cookies.get("adc_auth",""), auth_token())

class ResearchPlan(BaseModel):
    angle:str; audience:str
    claims_to_verify:list[str]=[]; source_targets:list[str]=[]; risks:list[str]=[]; recommended_structure:list[str]=[]
class ScriptDraft(BaseModel):
    title:str; hook:str; script:str; estimated_seconds:int=Field(ge=15,le=1800)
    scenes:list[str]=[]; factual_claims:list[str]=[]
class CriticScore(BaseModel):
    hook:int=Field(ge=0,le=100); retention:int=Field(ge=0,le=100); narrative:int=Field(ge=0,le=100)
    clarity:int=Field(ge=0,le=100); credibility:int=Field(ge=0,le=100)
    critical_issues:list[str]=[]; revision_instructions:list[str]=[]
    @property
    def average(self): return round((self.hook+self.retention+self.narrative+self.clarity+self.credibility)/5)
class VoicePlan(BaseModel):
    voice_profile:str; pace:str; energy:str; pauses:list[str]=[]; pronunciation_notes:list[str]=[]; anti_robotic_rules:list[str]=[]
class Shot(BaseModel):
    index:int; narration_excerpt:str; visual:str; camera_motion:str; on_screen_text:str=""; duration_seconds:float
class Storyboard(BaseModel):
    format:str; visual_style:str; shots:list[Shot]=[]
class WatcherReport(BaseModel):
    narrative_score:int=Field(ge=0,le=100); voice_risk_score:int=Field(ge=0,le=100)
    visual_consistency_score:int=Field(ge=0,le=100); factual_risk_score:int=Field(ge=0,le=100)
    critical_failures:list[str]=[]; qa_checklist:list[str]=[]; corrections:list[str]=[]
class DraftPackage(BaseModel):
    research:ResearchPlan; script:ScriptDraft; voice:VoicePlan; storyboard:Storyboard
class ReviewPackage(BaseModel):
    critic:CriticScore; watcher:WatcherReport

RADAR_SYSTEM="""Você é ADC Radar. Planeje conteúdo verificável, nunca invente fatos. Liste o que precisa ser confirmado, riscos e estrutura."""
STORY_SYSTEM="""Você é ADC Story. Escreva em português brasileiro natural, cinematográfico e de alta retenção. Nunca abra com enumeração burocrática ou 'você sabia?' automático. Não invente fatos."""
VOICE_SYSTEM="""Você é ADC Voice Director. Planeje narração natural, pausas orgânicas e cadência humana. Evite fala picotada e exagero dramático."""
DIRECTOR_SYSTEM="""Você é ADC Director. Crie storyboard vertical 9:16 com cenas variadas e factualmente compatíveis. Descreva cada visual de forma pesquisável e concreta."""
CRITIC_SYSTEM="""Você é ADC Critic independente. Avalie hook, retenção, narrativa, clareza e credibilidade. Reprove afirmações sem sustentação e abertura fraca."""
WATCHER_SYSTEM="""Você é ADC Watcher independente. Procure falhas críticas de narrativa, fatos, voz e coerência visual. Falha crítica deve bloquear."""

def ask_structured(system_instruction,prompt,schema):
    if not API_KEY: raise RuntimeError("GEMINI_API_KEY ausente")
    last=None
    for model_name in dict.fromkeys(FALLBACK_MODELS):
        try:
            client=genai.Client(api_key=API_KEY,http_options=types.HttpOptions(api_version="v1",timeout=15000))
            r=client.models.generate_content(model=model_name,contents=prompt,config=types.GenerateContentConfig(
                system_instruction=system_instruction,response_mime_type="application/json",response_schema=schema,temperature=0.5))
            return r.parsed if r.parsed is not None else schema.model_validate_json(r.text)
        except Exception as e:
            last=e
    raise RuntimeError(f"Gemini indisponível: {last}")

async def run_agent(sys,prompt,schema):
    return await asyncio.to_thread(ask_structured,sys,prompt,schema)

def gate_passes(c):
    return c.average>=85 and c.hook>=90 and c.credibility>=95 and not c.critical_issues

async def run_pipeline(brief):
    producer=RADAR_SYSTEM+"\n"+STORY_SYSTEM+"\n"+VOICE_SYSTEM+"\n"+DIRECTOR_SYSTEM
    draft=await run_agent(producer,"Execute Radar, Story, Voice e Director. BRIEF:\n"+brief,DraftPackage)
    review=await run_agent(CRITIC_SYSTEM+"\n"+WATCHER_SYSTEM,
        "Audite do zero este pacote e tente encontrar falhas reais:\n"+draft.model_dump_json(),ReviewPackage)
    c,w=review.critic,review.watcher
    blocked=(not gate_passes(c) or bool(w.critical_failures) or w.narrative_score<90 or w.factual_risk_score>15)
    return {"research":draft.research,"script":draft.script,"critic":c,"revision_count":0,
            "blocked":blocked,"voice":draft.voice,"storyboard":draft.storyboard,"watcher":w}

def safe_text(s,n=140):
    return re.sub(r"\s+"," ",s or "").strip()[:n]

def commons_image(query,out_path):
    api="https://commons.wikimedia.org/w/api.php"
    params={"action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":8,
            "prop":"imageinfo","iiprop":"url|mime|extmetadata","format":"json","origin":"*"}
    r=requests.get(api,params=params,timeout=8,headers={"User-Agent":"ADCStudio/0.8"}); r.raise_for_status()
    pages=(r.json().get("query") or {}).get("pages") or {}
    for p in pages.values():
        ii=(p.get("imageinfo") or [{}])[0]; mime=ii.get("mime","")
        meta=ii.get("extmetadata") or {}; lic=(meta.get("LicenseShortName") or {}).get("value","")
        if mime not in ("image/jpeg","image/png","image/webp"): continue
        if not any(x in lic.lower() for x in ["cc","public domain","pd"]): continue
        url=ii.get("url")
        if not url: continue
        raw=requests.get(url,timeout=12,headers={"User-Agent":"ADCStudio/0.8"}); raw.raise_for_status()
        Path(out_path).write_bytes(raw.content)
        return {"title":p.get("title",""),"license":lic,"source":ii.get("descriptionurl",url)}
    return None

def fallback_image(text,out_path):
    im=Image.new("RGB",(720,1280),(13,17,23)); d=ImageDraw.Draw(im)
    words=safe_text(text,220).split(); lines=[]; line=""
    for w in words:
        if len(line)+len(w)>32: lines.append(line); line=w
        else: line=(line+" "+w).strip()
    if line: lines.append(line)
    y=420
    for ln in lines[:8]:
        d.text((60,y),ln,fill=(235,235,235)); y+=48
    im.save(out_path,"JPEG",quality=90)

async def tts_to_file(text,path):
    await edge_tts.Communicate(text,VOICE,rate="-4%").save(path)

def srt_time(sec):
    ms=int((sec-int(sec))*1000); s=int(sec)%60; m=(int(sec)//60)%60; h=int(sec)//3600
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text,duration,path):
    parts=[p.strip() for p in re.split(r"(?<=[.!?])\s+",text) if p.strip()]
    if not parts: parts=[text]
    step=max(duration/len(parts),1.0)
    lines=[]
    for i,p in enumerate(parts):
        a=i*step; b=min((i+1)*step,duration)
        lines += [str(i+1),f"{srt_time(a)} --> {srt_time(b)}",p,""]
    Path(path).write_text("\n".join(lines),encoding="utf-8")

def media_qa(path, expected_duration):
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    report={"ok":True,"issues":[],"duration_expected":expected_duration}
    if not os.path.exists(path) or os.path.getsize(path)<10000:
        return {"ok":False,"issues":["Arquivo ausente ou vazio"]}
    try:
        p=subprocess.run([ff,"-v","error","-i",path,"-f","null","-"],capture_output=True,text=True,timeout=120)
        if p.returncode!=0:
            report["ok"]=False; report["issues"].append("Falha de decodificação: "+p.stderr[-500:])
    except Exception as e:
        report["ok"]=False; report["issues"].append("Não foi possível decodificar o vídeo: "+str(e))
    try:
        p=subprocess.run([ff,"-hide_banner","-i",path,"-af","silencedetect=noise=-45dB:d=2.5","-f","null","-"],
                         capture_output=True,text=True,timeout=120)
        txt=p.stderr
        silences=len(re.findall(r"silence_start",txt))
        report["silence_events"]=silences
        if silences>=3:
            report["ok"]=False; report["issues"].append("Silêncio excessivo detectado")
    except Exception as e:
        report["issues"].append("Aviso no teste de silêncio: "+str(e))
    try:
        size=os.path.getsize(path)
        report["file_size_bytes"]=size
        report["duration_ok"]=expected_duration>=5
    except Exception:
        pass
    return report

def render_free_media(result,workdir):
    wd=Path(workdir); wd.mkdir(parents=True,exist_ok=True)
    script=result["script"].script
    audio=str(wd/"voice.mp3")
    asyncio.run(tts_to_file(script,audio))
    duration=max(float(MP3(audio).info.length),5.0)
    shots=result["storyboard"].shots or [Shot(index=1,narration_excerpt="",visual=result["script"].title,camera_motion="",duration_seconds=duration)]
    shots=shots[:10]
    sources=[]; imgs=[]
    for i,shot in enumerate(shots):
        img=str(wd/f"img_{i:02}.jpg")
        q=safe_text(shot.visual,100)
        try: info=commons_image(q,img)
        except Exception: info=None
        if not info:
            fallback_image(shot.visual,img); info={"title":"ADC fallback visual","license":"generated fallback","source":""}
        imgs.append(img); sources.append(info)
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    segdur=duration/len(imgs); segs=[]
    for i,img in enumerate(imgs):
        seg=str(wd/f"seg_{i:02}.mp4"); segs.append(seg)
        cmd=[ff,"-y","-loop","1","-i",img,"-t",f"{segdur:.3f}","-r","30",
             "-vf","scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,format=yuv420p",
             "-c:v","libx264","-preset","ultrafast","-crf","25",seg]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    concat=wd/"concat.txt"; concat.write_text("\n".join([f"file '{Path(x).name}'" for x in segs]),encoding="utf-8")
    visuals=str(wd/"visuals.mp4")
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",visuals],
                   cwd=wd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    srt=str(wd/"captions.srt"); make_srt(script,duration,srt)
    out=str(wd/"adc_final.mp4")
    vf="subtitles=captions.srt:force_style='FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=90'"
    cmd=[ff,"-y","-i","visuals.mp4","-i","voice.mp3","-vf",vf,"-c:v","libx264","-preset","ultrafast","-crf","25",
         "-c:a","aac","-b:a","128k","-shortest","adc_final.mp4"]
    try:
        subprocess.run(cmd,cwd=wd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:
        subprocess.run([ff,"-y","-i","visuals.mp4","-i","voice.mp3","-c:v","copy","-c:a","aac","-shortest","adc_final.mp4"],
                       cwd=wd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    qa=media_qa(out,duration)
    return out,sources,duration,qa

async def planning_task(job_id,brief):
    try:
        JOBS[job_id]["result"]=await run_pipeline(brief)
        JOBS[job_id]["status"]="blocked" if JOBS[job_id]["result"]["blocked"] else "ready"
    except Exception as e:
        JOBS[job_id]["status"]="failed"; JOBS[job_id]["error"]=str(e)

async def render_task(job_id):
    try:
        JOBS[job_id]["status"]="rendering"
        wd=tempfile.mkdtemp(prefix="adc_")
        out,sources,duration=await asyncio.to_thread(render_free_media,JOBS[job_id]["result"],wd)
        JOBS[job_id].update({"status":"complete","media":out,"sources":sources,"duration":duration,"workdir":wd})
    except Exception as e:
        JOBS[job_id]["status"]="render_failed"; JOBS[job_id]["error"]=str(e)

CSS="""body{font-family:Arial,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:18px}.wrap{max-width:900px;margin:auto}
.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:20px;margin:16px 0}
input,textarea{width:100%;box-sizing:border-box;background:#0d1117;color:#fff;border:1px solid #444;border-radius:10px;padding:12px;font-size:16px}
button,.btn{display:inline-block;background:#7c3aed;color:#fff;border:0;border-radius:10px;padding:12px 18px;font-size:16px;font-weight:bold;text-decoration:none}
h1,h2,h3{margin-top:0}.muted{color:#8b949e}.ok{color:#3fb950}.bad{color:#f85149}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.metric{background:#0d1117;border-radius:10px;padding:12px}
pre{white-space:pre-wrap;word-wrap:break-word;background:#0d1117;padding:14px;border-radius:10px;overflow:auto}
@media(max-width:700px){.grid{grid-template-columns:1fr 1fr}}"""

def page(body,refresh=None):
    meta=f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    return HTMLResponse(f'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">{meta}<title>ADC Studio</title><style>{CSS}</style></head><body><div class="wrap">{body}</div></body></html>')

@app.get("/",response_class=HTMLResponse)
async def home(request:Request):
    if not PASSWORD: return page('<div class="card"><h2>Configuração incompleta</h2></div>')
    if not is_auth(request):
        return page('<div class="card"><h1>🔒 Acima do Comum</h1><form method="post" action="/login"><input type="password" name="password" placeholder="Senha" required><br><br><button>Entrar</button></form></div>')
    status='<span class="ok">Gemini configurado</span>' if API_KEY else '<span class="bad">Gemini ausente</span>'
    return page(f'<div class="card"><h1>🎬 Acima do Comum — AI Studio</h1><p class="muted">V0.9 • Free Media • Brain + QA + TTS + Commons + MP4 + Media Watcher</p><p>{status}</p></div>'
                '<div class="card"><form method="post" action="/produce"><label>O que vamos produzir?</label><br><br>'
                '<textarea name="brief" rows="7" required placeholder="Ex.: vídeo vertical de 60 segundos sobre um mistério histórico brasileiro."></textarea><br><br>'
                '<button>Iniciar produção</button></form></div>')

@app.post("/login")
async def login(password:str=Form(...)):
    if PASSWORD and hmac.compare_digest(password,PASSWORD):
        r=RedirectResponse("/",303); r.set_cookie("adc_auth",auth_token(),httponly=True,secure=True,samesite="lax",max_age=2592000); return r
    return page('<div class="card"><h2>Senha incorreta</h2><a href="/">Voltar</a></div>')

@app.post("/produce")
async def produce(request:Request,brief:str=Form(...)):
    if not is_auth(request): return RedirectResponse("/",303)
    jid=uuid.uuid4().hex[:12]; JOBS[jid]={"status":"planning","brief":brief}
    asyncio.create_task(planning_task(jid,brief.strip()))
    return RedirectResponse(f"/job/{jid}",303)

@app.get("/job/{jid}",response_class=HTMLResponse)
async def job(request:Request,jid:str):
    if not is_auth(request): return RedirectResponse("/",303)
    j=JOBS.get(jid)
    if not j: return page('<div class="card"><h2>Projeto não encontrado</h2></div>')
    st=j["status"]
    if st in ("planning","rendering"):
        label="Planejando e auditando..." if st=="planning" else "Gerando voz, buscando imagens e montando MP4..."
        return page(f'<div class="card"><h2>{label}</h2><p class="muted">Pode deixar esta tela aberta; ela atualiza sozinha.</p></div>',3)
    if st in ("failed","render_failed","media_blocked"):
        msg=j.get("error","")
        if st=="media_blocked": msg="Watcher técnico bloqueou o MP4: "+json.dumps(j.get("qa",{}),ensure_ascii=False)
        return page(f'<div class="card"><h2 class="bad">Falha / bloqueio</h2><pre>{html.escape(msg)}</pre><a class="btn" href="/">Novo projeto</a></div>')
    r=j["result"]; s=r["script"]; c=r["critic"]
    metrics="".join(f'<div class="metric"><b>{k}</b><br>{v}</div>' for k,v in [
        ("Gancho",c.hook),("Retenção",c.retention),("Narrativa",c.narrative),("Clareza",c.clarity),("Credibilidade",c.credibility),("ADC Score",c.average)])
    final='<p class="bad"><b>⛔ BLOQUEADO PELO QA</b></p>' if r["blocked"] else '<p class="ok"><b>✅ PRÉ-PRODUÇÃO APROVADA</b></p>'
    media=""
    if st=="ready":
        media=f'<form method="post" action="/render/{jid}"><button>Gerar vídeo grátis (MP4)</button></form>'
    elif st=="complete":
        media=f'<a class="btn" href="/media/{jid}">Abrir / baixar MP4</a><p class="muted">Duração: {j.get("duration",0):.1f}s</p>'
        credits="".join(f'<li>{html.escape(x.get("title",""))} — {html.escape(x.get("license",""))}</li>' for x in j.get("sources",[]))
        media+=f'<details><summary>Créditos das imagens</summary><ul>{credits}</ul></details>'
    def dump(x): return html.escape(json.dumps(x.model_dump(),ensure_ascii=False,indent=2)) if x else "Bloqueado"
    return page(f'<div class="card"><a href="/">← Novo projeto</a><h1>{html.escape(s.title)}</h1><h3>Gancho</h3><p>{html.escape(s.hook)}</p>'
                f'<div class="grid">{metrics}</div>{final}{media}</div>'
                f'<div class="card"><h2>Roteiro</h2><p>{html.escape(s.script).replace(chr(10),"<br>")}</p></div>'
                f'<div class="card"><h2>Voz</h2><pre>{dump(r["voice"])}</pre></div>'
                f'<div class="card"><h2>Storyboard</h2><pre>{dump(r["storyboard"])}</pre></div>'
                f'<div class="card"><h2>Watcher</h2><pre>{dump(r["watcher"])}</pre></div>')

@app.post("/render/{jid}")
async def render(request:Request,jid:str):
    if not is_auth(request): return RedirectResponse("/",303)
    j=JOBS.get(jid)
    if not j or j.get("status")!="ready": return RedirectResponse(f"/job/{jid}",303)
    asyncio.create_task(render_task(jid))
    return RedirectResponse(f"/job/{jid}",303)

@app.get("/media/{jid}")
async def media(request:Request,jid:str):
    if not is_auth(request): return RedirectResponse("/",303)
    j=JOBS.get(jid); path=j.get("media") if j else None
    if not path or not os.path.exists(path): return HTMLResponse("Arquivo não disponível",404)
    return FileResponse(path,media_type="video/mp4",filename="acima_do_comum.mp4")


async def selftest_runner(tid):
    report={"brain":{},"media":{}}
    try:
        brain=await run_pipeline("Crie um vídeo vertical curto de 20 segundos sobre a invenção da lâmpada, sem inventar fatos e com narrativa natural.")
        report["brain"]={
            "ok":True,
            "title":brain["script"].title,
            "blocked":brain["blocked"],
            "score":brain["critic"].average
        }
    except Exception as e:
        report["brain"]={"ok":False,"error":str(e)}
    try:
        synthetic={
            "script":ScriptDraft(
                title="Teste técnico ADC",
                hook="Um teste curto para validar voz, imagem, edição e Watcher.",
                script="Este é um teste técnico do Acima do Comum. A narração, as imagens, as legendas e o vídeo final estão sendo validados automaticamente.",
                estimated_seconds=15,
                scenes=["microfone de estúdio","edição de vídeo","legendas em vídeo"],
                factual_claims=[]
            ),
            "storyboard":Storyboard(
                format="9:16",
                visual_style="documental",
                shots=[
                    Shot(index=1,narration_excerpt="Este é um teste técnico",visual="microphone recording studio",camera_motion="slow zoom",duration_seconds=5),
                    Shot(index=2,narration_excerpt="narração, imagens",visual="video editing workstation",camera_motion="slow pan",duration_seconds=5),
                    Shot(index=3,narration_excerpt="validados automaticamente",visual="subtitles on video screen",camera_motion="static",duration_seconds=5),
                ]
            )
        }
        wd=tempfile.mkdtemp(prefix="adc_selftest_")
        out,sources,duration,qa=await asyncio.to_thread(render_free_media,synthetic,wd)
        report["media"]={
            "ok":bool(qa.get("ok")),
            "duration":duration,
            "qa":qa,
            "size":os.path.getsize(out) if os.path.exists(out) else 0,
            "sources":sources
        }
    except Exception as e:
        report["media"]={"ok":False,"error":str(e)}
    report["ok"]=bool(report["brain"].get("ok")) and bool(report["media"].get("ok"))
    SELFTESTS[tid]={"status":"complete","report":report}
    print("ADC_SELFTEST_RESULT="+json.dumps(report,ensure_ascii=False), flush=True)

@app.on_event("startup")
async def adc_startup_selftest():
    if SELFTEST_AUTO:
        SELFTESTS["boot"]={"status":"running"}
        asyncio.create_task(selftest_runner("boot"))

@app.get("/_selftest/start/{token}")
async def selftest_start(token:str):
    if not SELFTEST_TOKEN or not hmac.compare_digest(token,SELFTEST_TOKEN):
        return {"ok":False,"error":"forbidden"}
    tid=uuid.uuid4().hex[:10]
    SELFTESTS[tid]={"status":"running"}
    asyncio.create_task(selftest_runner(tid))
    return {"ok":True,"id":tid}

@app.get("/_selftest/status/{token}/{tid}")
async def selftest_status(token:str,tid:str):
    if not SELFTEST_TOKEN or not hmac.compare_digest(token,SELFTEST_TOKEN):
        return {"ok":False,"error":"forbidden"}
    return SELFTESTS.get(tid,{"status":"missing"})

@app.get("/health")
async def health():
    return {"ok":True,"version":"0.9","gemini":bool(API_KEY),"free_media":True,"media_watcher":True}
