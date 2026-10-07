import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {timing} from './timing.generated';

const RED = '#ef233c';
const RED2 = '#b70f27';
const WHITE = '#f7f7f8';
const MUTED = '#a8a8b2';
const PANEL = '#17171d';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

const Brand = () => (
  <div style={{
    position:'absolute', top:54, left:56, display:'flex', alignItems:'center', gap:18,
    fontFamily:'Arial Black, Arial, sans-serif', zIndex:20
  }}>
    <div style={{background:RED, color:WHITE, padding:'13px 20px', borderRadius:12, fontSize:30, letterSpacing:-1}}>
      VIROU ASSUNTO
    </div>
    <div style={{color:MUTED, fontSize:25, fontWeight:800}}>24H</div>
  </div>
);

const Progress = () => {
  const frame = useCurrentFrame();
  const p = interpolate(frame,[0,959],[0,1],clamp);
  return <div style={{position:'absolute',top:0,left:0,width:'100%',height:7,background:'#24242b',zIndex:40}}>
    <div style={{height:'100%',width:`${p*100}%`,background:RED}}/>
  </div>;
};

const Ticker = () => {
  const frame = useCurrentFrame();
  const x = -((frame * 4.2) % 1120);
  return <div style={{
    position:'absolute',left:0,right:0,bottom:55,height:76,background:'#0c0c10',
    borderTop:'1px solid #2f2f38',display:'flex',alignItems:'center',overflow:'hidden',zIndex:15,
    fontFamily:'Arial, sans-serif'
  }}>
    <div style={{height:'100%',width:190,background:RED,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:900,fontSize:28,color:WHITE,zIndex:3}}>AGORA</div>
    <div style={{position:'absolute',left:210+x,whiteSpace:'nowrap',fontSize:27,fontWeight:700,color:'#c8c8cf',letterSpacing:.4}}>
      BETS FORA DO AR  •  R$ 1,325 BI A DEVOLVER  •  PRAZO 9–14 OUT  •  VIROU ASSUNTO 24H  •  BETS FORA DO AR  •  R$ 1,325 BI A DEVOLVER  •
    </div>
  </div>;
};

const GridBackground = () => {
  const frame = useCurrentFrame();
  const dx = (frame*0.7)%72;
  const dy = (frame*0.45)%72;
  const pulse = 0.55 + Math.sin(frame/18)*0.12;
  return <AbsoluteFill style={{
    background:'#09090c',
    overflow:'hidden',
    fontFamily:'Arial, sans-serif'
  }}>
    <div style={{
      position:'absolute',inset:-120,
      backgroundImage:`linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px)`,
      backgroundSize:'72px 72px',
      backgroundPosition:`${dx}px ${dy}px`
    }}/>
    <div style={{
      position:'absolute', width:860,height:860,borderRadius:9999,right:-330,top:-260,
      background:`radial-gradient(circle, rgba(239,35,60,${pulse}) 0%, rgba(239,35,60,.08) 38%, transparent 72%)`,
      filter:'blur(24px)'
    }}/>
    <div style={{
      position:'absolute', width:720,height:720,borderRadius:9999,left:-360,bottom:-100,
      background:'radial-gradient(circle, rgba(183,15,39,.28), transparent 68%)',
      filter:'blur(34px)'
    }}/>
  </AbsoluteFill>;
};

const PopText: React.FC<{children:React.ReactNode; from?:number; style?:React.CSSProperties}> = ({children,from=0,style}) => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const s=spring({frame:frame-from,fps,config:{damping:14,stiffness:165,mass:.75}});
  return <div style={{opacity:s,transform:`translateY(${(1-s)*34}px) scale(${.92+s*.08})`,...style}}>{children}</div>;
};

const CaptionLayer = () => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const t=frame/fps;
  const words = timing.words as readonly {word:string;start:number;end:number;index:number}[];
  const current = words.find((w)=>t>=w.start && t<w.end);
  if(!current) return null;
  const groupStart=Math.floor(current.index/4)*4;
  const group=words.slice(groupStart,groupStart+4);
  return <div style={{
    position:'absolute',left:75,right:75,bottom:275,zIndex:50,
    display:'flex',justifyContent:'center',flexWrap:'wrap',gap:'8px 13px',
    fontFamily:'Arial Black, Arial, sans-serif',fontSize:54,lineHeight:1.04,textAlign:'center',
    textTransform:'uppercase',filter:'drop-shadow(0 4px 14px rgba(0,0,0,.75))'
  }}>
    {group.map((w)=>{
      const active=w.index===current.index;
      return <span key={w.index} style={{
        color:active?RED:WHITE,
        transform:active?'scale(1.09)':'scale(1)',
        display:'inline-block',
      }}>{w.word}</span>;
    })}
  </div>;
};

const HookScene = () => {
  const frame=useCurrentFrame();
  const blink = Math.sin(frame*.35)>-.25;
  return <AbsoluteFill style={{padding:'190px 62px 0'}}>
    <PopText style={{fontFamily:'Arial Black, Arial',fontSize:70,color:WHITE,lineHeight:.98}}>AINDA TINHA</PopText>
    <PopText from={5} style={{fontFamily:'Arial Black, Arial',fontSize:96,color:WHITE,lineHeight:.98,marginTop:10}}>DINHEIRO</PopText>
    <PopText from={10} style={{fontFamily:'Arial Black, Arial',fontSize:124,color:RED,lineHeight:.92,marginTop:2}}>NA BET?</PopText>
    <div style={{marginTop:88,display:'flex',justifyContent:'center'}}>
      <div style={{
        width:540,height:480,border:'3px solid #41414b',borderRadius:52,background:'linear-gradient(145deg,#24242b,#101014)',
        boxShadow:'0 30px 90px rgba(0,0,0,.45)',position:'relative',transform:`rotate(${Math.sin(frame/25)*1.2}deg)`
      }}>
        <div style={{position:'absolute',top:25,left:180,right:180,height:14,borderRadius:10,background:'#555560'}}/>
        <div style={{position:'absolute',inset:48,borderRadius:30,background:'#09090d',overflow:'hidden'}}>
          {[0,1,2].map((i)=><div key={i} style={{margin:'34px 26px 0',height:82,borderRadius:16,background:i===0?'#221219':'#19191f',border:'1px solid #33333c',display:'flex',alignItems:'center',padding:'0 20px',color:'#c9c9cf',fontSize:24,fontWeight:800}}>
            <span style={{width:14,height:14,borderRadius:99,background:i===0?RED:'#565661',marginRight:18}}/>
            APOSTA {i+1}
          </div>)}
          <div style={{position:'absolute',inset:0,display:'flex',alignItems:'center',justifyContent:'center'}}>
            <div style={{width:205,height:205,borderRadius:999,border:`15px solid ${blink?RED:'#6a1a26'}`,position:'relative'}}>
              <div style={{position:'absolute',left:85,top:-16,width:18,height:237,background:RED,transform:'rotate(45deg)',borderRadius:12}}/>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div style={{marginTop:58,background:PANEL,border:'1px solid #34343c',borderRadius:20,padding:'24px 28px',fontSize:35,fontWeight:850,color:WHITE}}>
      PRESTA ATENÇÃO: <span style={{color:RED}}>o prazo está correndo.</span>
    </div>
  </AbsoluteFill>;
};

const OfflineScene = () => {
  const frame=useCurrentFrame();
  const slide=interpolate(frame,[0,18],[120,0],clamp);
  return <AbsoluteFill style={{padding:'210px 58px 0'}}>
    <div style={{color:RED,fontSize:31,fontWeight:900,letterSpacing:2}}>NO BRASIL</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:88,lineHeight:.94,color:WHITE,marginTop:18}}>BETS<br/><span style={{color:RED}}>FORA DO AR</span></div>
    <div style={{fontSize:34,lineHeight:1.22,color:'#d0d0d5',marginTop:36,maxWidth:860}}>As plataformas autorizadas encerraram a operação.</div>
    <div style={{marginTop:80,position:'relative',height:590}}>
      {[0,1,2].map((i)=>{
        const yy=70+i*165;
        const xx=70+slide+i*22;
        return <div key={i} style={{position:'absolute',left:xx,right:65,top:yy,height:126,borderRadius:22,background:'#15151b',border:'1px solid #34343f',boxShadow:'0 18px 44px rgba(0,0,0,.25)',display:'flex',alignItems:'center',padding:'0 28px'}}>
          <div style={{width:54,height:54,borderRadius:14,background:i===0?'#35131b':'#25252d',display:'flex',alignItems:'center',justifyContent:'center',color:RED,fontWeight:900,fontSize:27}}>B</div>
          <div style={{marginLeft:24,flex:1}}>
            <div style={{height:14,width:'61%',background:'#45454f',borderRadius:8}}/>
            <div style={{height:10,width:'42%',background:'#2d2d35',borderRadius:8,marginTop:16}}/>
          </div>
          <div style={{fontSize:24,fontWeight:900,color:RED}}>OFF</div>
        </div>
      })}
      <div style={{position:'absolute',left:125,right:125,top:235,height:18,background:RED,transform:'rotate(-12deg)',borderRadius:10,boxShadow:'0 0 30px rgba(239,35,60,.35)'}}/>
    </div>
  </AbsoluteFill>;
};

const MoneyScene = () => {
  const frame=useCurrentFrame();
  const p=interpolate(frame,[0,72],[0,1],clamp);
  const value=(1.325*p).toFixed(3).replace('.',',');
  return <AbsoluteFill style={{padding:'220px 58px 0'}}>
    <div style={{color:MUTED,fontSize:30,fontWeight:800}}>SALDO A DEVOLVER</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:96,color:WHITE,marginTop:28}}>R$ <span style={{color:RED}}>{value}</span></div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:132,color:RED,lineHeight:.9}}>BILHÃO</div>
    <div style={{fontSize:36,color:'#d4d4da',marginTop:48}}>ainda aguardava devolução.</div>
    <div style={{marginTop:110,height:360,position:'relative'}}>
      {[0,1,2,3].map((i)=>{
        const rise=interpolate(frame,[i*8,32+i*8],[80,0],clamp);
        return <div key={i} style={{position:'absolute',left:68+i*210,top:140-rise+(i%2)*35,width:178,height:105,borderRadius:18,background:'linear-gradient(135deg,#24242c,#15151a)',border:'1px solid #44444e',display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'Arial Black',fontSize:42,color:i===1?RED:WHITE,boxShadow:'0 18px 45px rgba(0,0,0,.28)'}}>R$</div>
      })}
    </div>
    <div style={{background:'#121217',border:'1px solid #31313a',borderRadius:18,padding:'20px 24px',color:MUTED,fontSize:26}}>Fonte: Governo Federal • 06/10/2026</div>
  </AbsoluteFill>;
};

const PeopleScene = () => {
  const frame=useCurrentFrame();
  const p=interpolate(frame,[0,60],[0,1],clamp);
  return <AbsoluteFill style={{padding:'205px 58px 0'}}>
    <div style={{color:RED,fontWeight:900,fontSize:31,letterSpacing:2}}>CERCA DE</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:133,color:WHITE,marginTop:20}}>26,5</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:83,color:RED,lineHeight:.92}}>MILHÕES</div>
    <div style={{fontSize:37,color:'#d4d4da',marginTop:33}}>de apostadores têm saldo.</div>
    <div style={{marginTop:90,display:'grid',gridTemplateColumns:'repeat(10,1fr)',gap:'26px 18px',padding:'0 18px'}}>
      {Array.from({length:50}).map((_,i)=>{
        const show=p*58>i;
        return <div key={i} style={{height:72,position:'relative',opacity:show?1:.08,transform:`scale(${show?1:.6})`}}>
          <div style={{position:'absolute',left:'50%',transform:'translateX(-50%)',width:22,height:22,borderRadius:99,background:i%7===0?RED:'#9c9ca6'}}/>
          <div style={{position:'absolute',top:28,left:'50%',transform:'translateX(-50%)',width:42,height:39,borderRadius:'19px 19px 10px 10px',background:'#555560'}}/>
        </div>
      })}
    </div>
  </AbsoluteFill>;
};

const BankScene = () => {
  const frame=useCurrentFrame();
  const p=interpolate(frame,[0,80],[0,1],clamp);
  return <AbsoluteFill style={{padding:'200px 58px 0'}}>
    <div style={{color:MUTED,fontWeight:800,fontSize:29}}>HOJE • 07/10</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:78,color:WHITE,lineHeight:.96,marginTop:24}}>SALDOS VÃO<br/><span style={{color:RED}}>PARA OS BANCOS</span></div>
    <div style={{fontSize:34,color:'#d2d2d7',marginTop:38}}>As empresas têm prazo para informar os valores.</div>
    <div style={{height:520,marginTop:80,position:'relative'}}>
      <div style={{position:'absolute',left:95,top:160,width:235,height:310,borderRadius:38,border:'3px solid #555560',background:'#131319'}}>
        <div style={{position:'absolute',top:30,left:78,right:78,height:11,borderRadius:10,background:'#51515b'}}/>
        <div style={{position:'absolute',top:92,left:32,right:32,height:75,borderRadius:16,background:'#2a171d',color:RED,fontSize:27,fontWeight:900,display:'flex',alignItems:'center',justifyContent:'center'}}>SALDO</div>
      </div>
      <div style={{position:'absolute',right:70,top:145,width:300,height:310}}>
        <div style={{position:'absolute',top:0,left:0,right:0,height:74,clipPath:'polygon(50% 0,100% 100%,0 100%)',background:RED}}/>
        <div style={{position:'absolute',top:86,left:25,right:25,height:28,background:WHITE}}/>
        {[0,1,2,3].map(i=><div key={i} style={{position:'absolute',top:130,left:42+i*60,width:30,height:122,background:'#bdbdc4'}}/>)}
        <div style={{position:'absolute',top:270,left:10,right:10,height:33,background:WHITE}}/>
      </div>
      <div style={{position:'absolute',left:340,top:270,width:300,height:16,background:'#34343d',borderRadius:12}}>
        <div style={{width:`${p*100}%`,height:'100%',background:RED,borderRadius:12,boxShadow:'0 0 24px rgba(239,35,60,.4)'}}/>
      </div>
      <div style={{position:'absolute',left:458+p*78,top:238,fontSize:44,color:RED}}>➜</div>
    </div>
  </AbsoluteFill>;
};

const TimelineScene = () => {
  const frame=useCurrentFrame();
  const p=interpolate(frame,[0,85],[0,1],clamp);
  return <AbsoluteFill style={{padding:'210px 58px 0'}}>
    <div style={{color:RED,fontWeight:900,fontSize:31,letterSpacing:2}}>DEVOLUÇÃO</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:128,color:WHITE,marginTop:25}}>09 → 14</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:71,color:RED,lineHeight:.9}}>DE OUTUBRO</div>
    <div style={{fontSize:34,color:'#d1d1d7',marginTop:45}}>Bancos devem devolver os saldos nesse período.</div>
    <div style={{marginTop:145,position:'relative',height:300}}>
      <div style={{position:'absolute',left:80,right:80,top:95,height:11,borderRadius:8,background:'#3e3e48'}}/>
      <div style={{position:'absolute',left:80,top:95,height:11,borderRadius:8,background:RED,width:`${p*760}px`}}/>
      {[{x:80,d:'09',l:'SEX'},{x:840,d:'14',l:'QUA'}].map((m)=><div key={m.d} style={{position:'absolute',left:m.x-36,top:60,textAlign:'center'}}>
        <div style={{width:72,height:72,borderRadius:99,background:RED,color:WHITE,display:'flex',alignItems:'center',justifyContent:'center',fontSize:29,fontWeight:900}}>{m.d}</div>
        <div style={{color:MUTED,fontSize:23,fontWeight:800,marginTop:18}}>{m.l}</div>
      </div>)}
    </div>
    <div style={{marginTop:45,background:PANEL,border:'1px solid #373741',borderRadius:22,padding:'30px 32px'}}>
      <div style={{fontWeight:900,fontSize:31,color:WHITE}}>NÃO RECEBEU?</div>
      <div style={{fontSize:29,lineHeight:1.25,color:'#d2d2d7',marginTop:12}}>A Caixa passa a atuar a partir de <span style={{color:RED,fontWeight:900}}>14/10</span>.</div>
    </div>
  </AbsoluteFill>;
};

const CTAScene = () => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const s=spring({frame,fps,config:{damping:12,stiffness:150}});
  return <AbsoluteFill style={{padding:'245px 58px 0',textAlign:'center'}}>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:72,color:MUTED}}>CONHECE ALGUÉM</div>
    <div style={{fontFamily:'Arial Black, Arial',fontSize:93,color:WHITE,lineHeight:.96,marginTop:20}}>QUE AINDA<br/>TINHA <span style={{color:RED}}>SALDO?</span></div>
    <div style={{margin:'110px auto 0',width:760,padding:'34px 30px',borderRadius:25,background:RED,color:WHITE,fontFamily:'Arial Black, Arial',fontSize:49,transform:`scale(${.88+s*.12})`,boxShadow:'0 20px 70px rgba(239,35,60,.28)'}}>MANDA ESTE VÍDEO</div>
    <div style={{fontSize:31,color:MUTED,marginTop:55}}>Fonte oficial na legenda • @virouassunto24h</div>
  </AbsoluteFill>;
};

const scene = (frame:number) => {
  if(frame<95) return <HookScene/>;
  if(frame<205) return <OfflineScene/>;
  if(frame<330) return <MoneyScene/>;
  if(frame<465) return <PeopleScene/>;
  if(frame<620) return <BankScene/>;
  if(frame<805) return <TimelineScene/>;
  return <CTAScene/>;
};

export const VirouAssuntoReel:React.FC=()=>{
  const frame=useCurrentFrame();
  return <AbsoluteFill style={{background:'#09090c',color:WHITE}}>
    <GridBackground/>
    <Audio src={staticFile('bed.wav')} volume={0.20}/>
    <Audio src={staticFile('voiceover.wav')} volume={1}/>
    <Brand/>
    <Progress/>
    {scene(frame)}
    <CaptionLayer/>
    <Ticker/>
    <div style={{position:'absolute',inset:28,border:'1px solid rgba(255,255,255,.08)',borderRadius:28,pointerEvents:'none',zIndex:12}}/>
  </AbsoluteFill>;
};
