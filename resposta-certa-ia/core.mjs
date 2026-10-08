
export const fields=['age','gender','city','state','education','job','marital','children','income','housing','extra'];
export const norm=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9\s]/g,' ').replace(/\s+/g,' ').trim();
const stop=new Set('qual voce seus seu sua para como what which your with many tem que sao quantos esta onde uma umas quando do does have sobre outras todos how many as it de da das dos do a o os e or in'.split(' '));
export function similarity(a,b){let x=new Set(norm(a).split(' ').filter(w=>w.length>=3&&!stop.has(w)));let y=new Set(norm(b).split(' ').filter(w=>w.length>=3&&!stop.has(w)));if(!x.size||!y.size)return 0;let n=0;for(const k of x)if(y.has(k))n++;return n/Math.max(x.size,y.size)}
export function selectQuestion(raw){const l=String(raw||'').split(/\n/).map(s=>s.trim()).filter(Boolean);return (l.find(s=>s.includes('?')||/^(?:qual|quantos|quantas|onde|voce|você|seu|sua|indique|selecione|marque|how|what|which|where|do you|are you)\b/i.test(s))||l[0]||'').slice(0,500)}
const rules=[
['age',/\bidade\b|\bquantos anos\b|\bage\b|how old/i],
['gender',/g[eê]nero|\bsexo\b|\bgender\b|your sex/i],
['city',/\bcidade\b|munic[ií]pio|which city|what city|which town/i],
['state',/qual estado|estado onde|unidade federativa|which state|state of residence/i],
['education',/escolaridade|forma[cç][aã]o acad[eê]mica|n[ií]vel de ensino|grau de instru[cç][aã]o|education|highest degree/i],
['job',/profiss[aã]o|ocupa[cç][aã]o|trabalha com|seu trabalho|\bemprego\b|\bjob\b|occupation|work as/i],
['marital',/estado civil|marital status|relationship status/i],
['children',/\bfilhos\b|\bfilhas\b|\bchildren\b|\bkids\b/i],
['income',/\brenda\b|sal[aá]rio familiar|ganhos mensais|household income|monthly income/i],
['housing',/\bmoradia\b|casa pr[oó]pria|\baluguel\b|home ownership|rented home/i]
];
export function suggest(raw,profile={},memories=[]){raw=String(raw||'').trim();if(!raw)return {kind:'unknown',answer:'Insira a pergunta ou um print.',reason:'Não há conteúdo para analisar.'};
if(/did not qualify|different target group|not qualified|n[aã]o (foi )?qualificad|desclassificad|n[aã]o se enquadra/i.test(raw))return {kind:'info',answer:'Essa tela informa que você não se qualificou.',reason:'Não há pergunta a responder. Escolha outra pesquisa.'};
const question=selectQuestion(raw);const matches=(memories||[]).map(x=>({...x,score:similarity(question,x.question)})).sort((a,b)=>b.score-a.score);
if(matches.length&&matches[0].score>=.72)return{kind:'found',answer:matches[0].answer,reason:'Resposta da memória. Confira o contexto antes de usar.',question};
const candidates=rules.filter(x=>x[1].test(question));
if(candidates.length===1){const key=candidates[0][0],v=String(profile[key]??'').trim();if(v)return {kind:'found',answer:key==='age'?v+' anos':v,reason:'Dado recuperado do perfil. Se houver opções, selecione a correspondente.',question}}
for(const ln of String(profile.extra||'').split(/\n/)){const pair=ln.split(/\s*[:=]\s*/);if(pair.length>1&&similarity(question,pair[0])>.69)return {kind:'found',answer:pair.slice(1).join(': '),reason:'Dado extra do perfil. Confira o contexto.',question}}
if(matches.length&&matches[0].score>=.43)return {kind:'review',answer:'Resposta possivelmente relacionada: '+matches[0].answer,reason:'Pergunta semelhante: '+matches[0].question+'. Verifique manualmente.',question};
return {kind:'unknown',answer:'Não tenho informações suficientes para sugerir uma resposta verdadeira.',reason:'Responda pessoalmente e, se desejar, salve para reutilizar.',question}}
export function safeParse(text){let x=String(text||'').trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');try{return JSON.parse(x)}catch{let a=x.indexOf('{'),b=x.lastIndexOf('}');if(a>=0&&b>a)return JSON.parse(x.slice(a,b+1));throw Error('A IA retornou formato inesperado. Tente novamente.')}}
