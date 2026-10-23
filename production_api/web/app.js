'use strict';
const $=id=>document.getElementById(id);
let token=sessionStorage.getItem('jobagent_token')||'',tab='dashboard';
const safe=(x)=>String(x??'');
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=safe(text);if(cls)n.className=cls;return n}
function add(parent,tag,text,cls){const n=el(tag,text,cls);parent.append(n);return n}
function clear(node){node.replaceChildren()}
function note(message){$('message').textContent=message}
async function api(path,method='GET',data){const headers={'Accept':'application/json'};if(token)headers.Authorization='Bearer '+token;if(data!==undefined)headers['Content-Type']='application/json';const r=await fetch('/api'+path,{method,headers,body:data===undefined?undefined:JSON.stringify(data)});let value;try{value=await r.json()}catch{value={detail:'Resposta inválida'}}if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:JSON.stringify(value.detail||'Erro'));return value}
function formField(form,label,key,value='',type='text',required=false){const l=add(form,'label',label);const i=el(type==='textarea'?'textarea':'input');i.name=key;i.value=safe(value);if(type!=='textarea')i.type=type;i.required=required;l.append(i);return i}
function action(label,fn,secondary=false){const b=el('button',label);b.type='button';if(secondary)b.className='secondary';b.onclick=async()=>{b.disabled=true;try{await fn();note('Operação concluída.')}catch(e){note('Erro: '+e.message)}finally{b.disabled=false}};return b}
function panel(title){const root=$('content');clear(root);add(root,'h2',title);return root}
async function show(next=tab){tab=next;const logged=!!token;$('auth').hidden=logged;$('workspace').hidden=!logged;$('logout').hidden=!logged;if(!logged)return;document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));$('pageTitle').textContent=({dashboard:'Visão geral',import:'Importar currículo',master:'Perfil profissional estruturado',ledger:'Registro de fatos',diagnostic:'Diagnóstico profissional',evidence:'Minhas evidências',jobs:'Vagas e requisitos',applications:'Minhas candidaturas',tasks:'Plano de ação',graph:'Mapa de evidências',loop:'Evolução profissional',premium:'Career Professional',account:'Minha conta'})[tab]||tab;try{const billing=await api('/billing/status');$('planBadge').textContent=billing.premium_enabled?'Career Professional ativo':'Plano gratuito';if(tab==='dashboard')await dashboard();if(tab==='import')await importResume();if(tab==='master')await masterView();if(tab==='ledger')await ledgerView();if(tab==='diagnostic'){await diagnostic();await groundedPanel();}if(tab==='evidence')await evidence();if(tab==='jobs')await jobs();if(tab==='applications')await applications();if(tab==='tasks')await tasks();if(tab==='graph')await graphView();if(tab==='loop')await loopView();if(tab==='premium')await premium(billing);if(tab==='account')await account()}catch(e){note('Erro: '+e.message);if(e.message.includes('Sessão inválida')||e.message.includes('Autenticação necessária')){token='';sessionStorage.removeItem('jobagent_token');show()}}}
async function dashboard(){const [d,p,onboard,brief]=await Promise.all([api('/dashboard'),api('/progress'),api('/onboarding'),api('/career/weekly-brief')]);const root=panel('Seu progresso em números');add(root,'h3','Comece por aqui · '+onboard.completed+'/'+onboard.total+' etapas');onboard.steps.forEach(step=>{const line=add(root,'div',undefined,'entry');add(line,'strong',(step.done?'✓ ':'○ ')+step.label);if(!step.done)line.append(action('Completar etapa',async()=>show(step.next_tab),true))});const journey=await api('/journey/first-result');add(root,'h3','Seu próximo passo profissional');add(root,'p',journey.first_result);journey.next_actions.forEach(x=>{const item=add(root,'div',undefined,'entry');add(item,'strong',x.title);add(item,'p',x.why);item.append(action('Fazer agora',async()=>show(x.next_tab),true))});add(root,'h3','Seu resumo da semana');add(root,'p','Tarefas: '+brief.tasks.completed+'/'+brief.tasks.total+' concluídas · Horas disponíveis: '+brief.hours_available);brief.next_actions.forEach(x=>{const e=add(root,'div',undefined,'entry');add(e,'strong',x.action);add(e,'small',x.why)});const g=add(root,'div',undefined,'grid');for(const [label,v] of [['Evidências',d.evidence],['Vagas salvas',d.jobs],['Candidaturas',d.applications],['Tarefas concluídas',p.tasks_done+' / '+p.tasks_total]]){const c=add(g,'div',undefined,'tile');add(c,'div',v,'number');add(c,'p',label)}add(root,'p','Registre ações reais. Não calculamos probabilidade de contratação.');const me=await api('/profile');const f=add(root,'form');add(f,'h3','Meu perfil');for(const [k,l] of [['name','Nome'],['target_role','Cargo-alvo'],['location','Localização'],['summary','Resumo profissional']])formField(f,l,k,me[k]||'',k==='summary'?'textarea':'text');formField(f,'Horas disponíveis por semana','hours_per_week',me.hours_per_week||5,'number');f.append(action('Salvar perfil',async()=>{const x={...me};for(const input of f.querySelectorAll('[name]'))x[input.name]=input.name==='hours_per_week'?Number(input.value):input.value;await api('/profile','PUT',x);await show('dashboard')}))}
async function diagnostic(){
 const [d,priority]=await Promise.all([api('/intelligence'),api('/diagnostic/priority-actions')]);const root=panel('Career Intelligence — diagnóstico rastreável');
 add(root,'h3','Suas próximas ações priorizadas');priority.actions.forEach(a=>{const item=add(root,'div',undefined,'entry');add(item,'strong',a.action);add(item,'p',a.why);add(item,'small','Origem: '+a.source);item.append(action('Agir agora',async()=>show(a.next_tab),true))});
 add(root,'p','Análise por requisitos de vagas reais e evidências declaradas. Não verificamos automaticamente competências nem calculamos chances de contratação.');
 const c=d.quality.coverage,g=add(root,'div',undefined,'grid');
 for(const [label,value] of [['Vagas com requisitos',c.jobs_with_requirements+' / '+c.total_jobs],['Requisitos distintos',c.total_requirements],['Requisitos com indícios',c.requirements_with_candidates],['Evidências com URL',c.evidence_with_sources+' / '+c.total_evidence]]){const tile=add(g,'div',undefined,'tile');add(tile,'div',value,'number');add(tile,'p',label)}
 add(root,'h3','As 3 próximas ações');d.top_actions.forEach((a,i)=>{const e=add(root,'div',undefined,'entry');add(e,'strong',(i+1)+'. '+a.action);add(e,'p','Motivo: '+a.why);if(a.linked_jobs.length)add(e,'small','Vagas relacionadas: '+a.linked_jobs.join(', '));e.append(action('Adicionar ao meu plano',async()=>{await api('/tasks','POST',{title:a.action.slice(0,300)});await show('tasks')},true))});
 add(root,'h3','Prioridades e lacunas');if(!d.requirement_priorities.length)add(root,'p','Cadastre vagas reais e seus requisitos para iniciar a comparação.');
 d.requirement_priorities.forEach(r=>{const e=add(root,'div',undefined,'entry');add(e,'strong',r.requirement+' · '+r.jobs_requiring+' vaga(s)');add(e,'p',r.state==='NOT_DOCUMENTED'?'Não documentado (não significa desconhecimento)':'Indícios textuais — não verificados');add(e,'small',r.rationale);r.evidence_refs.forEach(x=>add(e,'p','Evidência #'+x.evidence_id+': '+x.title+' ('+x.status+')'))});
 add(root,'h3','Oportunidades por indícios documentais');const ranked=await api('/career/opportunity-priorities');ranked.opportunities.forEach(j=>{const e=add(root,'div',undefined,'entry');add(e,'strong',j.title+' · '+j.company);add(e,'p',j.possible_documentary_matches+'/'+j.requirements_total+' requisitos com indícios declarados. Não é uma chance de contratação.')});add(root,'h3','Comparação por oportunidade');d.opportunities.forEach(j=>{const e=add(root,'div',undefined,'entry');add(e,'strong',j.title+' · '+j.company);add(e,'p',j.documented_candidates+' requisitos com indícios; '+j.not_documented+' sem evidência textual.');j.requirements.forEach(r=>add(e,'small',r.requirement+' — '+(r.state==='NOT_DOCUMENTED'?'não documentado':'possível evidência declarada')))});
 add(root,'h3','Limitações e transparência');d.uncertainties.forEach(x=>add(root,'p','• '+x));d.quality.data_quality_notes.forEach(x=>add(root,'p','• '+x));
}
const EVIDENCE_KINDS=[['skill','Competência'],['project','Projeto'],['experience','Experiência profissional'],['education','Formação'],['certificate','Certificação'],['language','Idioma']];
function evidenceKindField(form,value='project'){
 const label=add(form,'label','Categoria da evidência');const select=add(label,'select');select.name='kind';select.required=true;
 for(const [key,name] of EVIDENCE_KINDS){const option=add(select,'option',name);option.value=key}
 select.value=EVIDENCE_KINDS.some(([key])=>key===value)?value:'project';return select;
}
function evidenceUrlField(form,value=''){
 const field=formField(form,'Link público da evidência (opcional)','url',value,'url');field.maxLength=1000;
 const hint=add(form,'small','Use um link público e estável, sem tokens de acesso ou links privados. Máximo: 1.000 caracteres.');hint.className='field-hint';return field;
}
function validatedEvidence(form){
 const data=Object.fromEntries(new FormData(form));data.kind=String(data.kind||'').toLowerCase();
 if(!EVIDENCE_KINDS.some(([key])=>key===data.kind))throw Error('Selecione uma categoria válida.');
 const url=String(data.url||'').trim();if(url.length>1000)throw Error('O link excede 1.000 caracteres. Use uma URL pública mais curta.');
 if(url){let parsed;try{parsed=new URL(url)}catch{throw Error('Informe um link válido começando com https://')}
 if(!['https:','http:'].includes(parsed.protocol))throw Error('Use um link HTTP ou HTTPS.');
 if([...parsed.searchParams.keys()].some(k=>/token|access_token|auth|signature|key|secret|jwt/i.test(k)))throw Error('Este link contém um possível token de acesso. Use a URL pública sem parâmetros de autenticação.');
 }
 return {...data,url};
}
async function evidence(){
 const items=await api('/evidence');const root=panel('Portfólio de evidências');
 add(root,'p','Registre fatos verificáveis e utilize links públicos. Evidências declaradas não são verificadas automaticamente.');
 const f=add(root,'form');evidenceKindField(f);
 formField(f,'Título','title','','text',true);
 formField(f,'Descrição e resultados','description','','textarea',true);
 evidenceUrlField(f);
 f.append(action('Adicionar evidência',async()=>{await api('/evidence','POST',validatedEvidence(f));await show('evidence')}));
 items.forEach(x=>{
  const e=add(root,'div',undefined,'entry');add(e,'h3',x.title);add(e,'small',x.kind+' · '+x.status);add(e,'p',x.description);
  if(x.url)add(e,'small','Fonte declarada: '+x.url);
  e.append(action('Editar evidência',async()=>{
   const edit=add(e,'form');evidenceKindField(edit,x.kind);
   formField(edit,'Título','title',x.title,'text',true);
   formField(edit,'Descrição','description',x.description,'textarea',true);
   evidenceUrlField(edit,x.url||'');
   edit.append(action('Salvar alterações',async()=>{await api('/evidence/'+x.id,'PUT',validatedEvidence(edit));await show('evidence')}));
  },true));
  e.append(action('Avaliar documentação',async()=>{await evidenceAssessment(x.id,e)},true));
  e.append(action('Analisar artefatos técnicos',async()=>{await artifactReviewView(x.id,e)},true));
  e.append(action('Revisão estática e contribuições',async()=>{await technicalReviewView(x.id,e)},true));
  e.append(action('Excluir',async()=>{if(confirm('Excluir esta evidência?')){await api('/evidence/'+x.id,'DELETE');await show('evidence')}},true));
 });
}
async function jobs(){const items=await api('/jobs');const root=panel('Vagas reais e seus requisitos');const f=add(root,'form');formField(f,'Cargo','title','','text',true);formField(f,'Empresa','company','','text',true);formField(f,'Descrição','description','','textarea',true);formField(f,'Requisitos (separe por vírgulas)','requirements','','textarea');formField(f,'Link da vaga','source_url','','url');f.append(action('Salvar vaga',async()=>{const v=Object.fromEntries(new FormData(f));v.requirements=v.requirements.split(',').map(x=>x.trim()).filter(Boolean);await api('/jobs','POST',v);await show()}));items.forEach(x=>{const e=add(root,'div',undefined,'entry');add(e,'h3',x.title+' · '+x.company);add(e,'p',x.requirements.join(' · ')||'Requisitos não informados');e.append(action('Registrar candidatura',async()=>{await api('/applications','POST',{job_id:x.id,status:'saved',notes:''});await show('applications')},true));e.append(action('Comparar Premium',async()=>{const m=await api('/jobs/'+x.id+'/match');note('Correspondências potenciais: '+m.potential_matches.length+' | Não documentados: '+m.unresolved_requirements.length)},true));e.append(action('Preparar entrevista Premium',async()=>{const r=await api('/jobs/'+x.id+'/interview');const section=add(e,'div');add(section,'h3','Perguntas de preparação');r.questions.forEach(q=>add(section,'p',q))},true));e.append(action('Excluir',async()=>{if(confirm('Excluir a vaga e suas candidaturas?')){await api('/jobs/'+x.id,'DELETE');await show()}},true))})}
async function applications(){const [items,jobs]=await Promise.all([api('/applications'),api('/jobs')]);const root=panel('Pipeline de candidaturas');if(!items.length)add(root,'p','Salve uma vaga e registre a candidatura para começar.');items.forEach(x=>{const e=add(root,'div',undefined,'entry');const job=jobs.find(j=>j.id===x.job_id);add(e,'h3',job?job.title+' · '+job.company:'Vaga removida');const s=add(e,'select');for(const status of ['saved','prepared','applied','interview','offer','rejected','withdrawn']){const opt=el('option',status);opt.value=status;opt.selected=status===x.status;s.append(opt)}e.append(action('Atualizar etapa',async()=>{await api('/applications/'+x.id,'PUT',{job_id:x.job_id,status:s.value,notes:x.notes});await show()}))})}
async function tasks(){const items=await api('/tasks');const root=panel('Execução semanal');const f=add(root,'form');formField(f,'Próxima ação concreta','title','','text',true);f.append(action('Adicionar tarefa',async()=>{await api('/tasks','POST',Object.fromEntries(new FormData(f)));await show()}));items.forEach(x=>{const e=add(root,'div',undefined,'entry');const b=el('input');b.type='checkbox';b.checked=x.done;b.onchange=async()=>{try{await api('/tasks/'+x.id,'PATCH',{done:b.checked});await show()}catch(err){note(err.message)}};e.append(b);add(e,'span',' '+x.title);e.append(action('Remover',async()=>{await api('/tasks/'+x.id,'DELETE');await show('tasks')},true))})}

async function graphView(){
 const [graph,jobs]=await Promise.all([api('/career/graph'),api('/jobs')]);const root=panel('Career Evidence Graph');
 add(root,'p','Vincule uma evidência real a um requisito. Uma ligação declarada não é uma verificação independente.');
 const f=add(root,'form');const eLabel=add(f,'label','Evidência');const eSel=add(eLabel,'select');eSel.name='evidence_id';graph.evidence.forEach(e=>{const o=el('option',e.title+' (#'+e.id+')');o.value=e.id;eSel.append(o)});
 const rLabel=add(f,'label','Requisito das vagas');const rSel=add(rLabel,'select');rSel.name='requirement';graph.requirements.forEach(r=>{const o=el('option',r);o.value=r;rSel.append(o)});
 formField(f,'Por que esta evidência sustenta o requisito?','rationale','','textarea');
 if(!graph.evidence.length||!graph.requirements.length)add(root,'p','Cadastre pelo menos uma evidência e uma vaga com requisitos para criar ligações.');
 const create=action('Vincular evidência',async()=>{const v=Object.fromEntries(new FormData(f));await api('/career/graph/links','POST',{...v,evidence_id:Number(v.evidence_id)});await show('graph')});create.disabled=!graph.evidence.length||!graph.requirements.length;f.append(create);
 add(root,'h3','Ligações persistentes');if(!graph.links.length)add(root,'p','Ainda não há ligações.');
 graph.links.forEach(l=>{const e=graph.evidence.find(x=>x.id===l.evidence_id);const row=add(root,'div',undefined,'entry');add(row,'strong',(e?.title||'Evidência removida')+' → '+l.requirement);add(row,'p',l.rationale||'Sem justificativa detalhada');row.append(action('Remover ligação',async()=>{await api('/career/graph/links/'+l.id,'DELETE');await show('graph')},true))});
}
async function loopView(){
 const [loop,history,outcomes,jobs]=await Promise.all([api('/career/loop'),api('/career/checkins'),api('/career/outcomes'),api('/jobs')]);
 const root=panel('Adaptive Career Loop');add(root,'p','Compare seu progresso com o último registro. Indicadores de atividade não significam aumento comprovado de empregabilidade.');
 const g=add(root,'div',undefined,'grid');for(const [k,label] of [['evidence','Evidências'],['links','Ligações'],['tasks_completed','Tarefas concluídas'],['applications','Candidaturas enviadas'],['interviews_reported','Entrevistas relatadas'],['offers_reported','Ofertas relatadas']]){const c=add(g,'div',undefined,'tile');add(c,'div',loop.current[k]+' ('+(loop.since_last_checkin[k]>=0?'+':'')+loop.since_last_checkin[k]+')','number');add(c,'p',label)}
 root.append(action('Registrar check-in agora',async()=>{const x=await api('/career/checkins','POST');note(x.unchanged?'Nenhuma mudança desde o último check-in.':'Novo check-in registrado.');await show('loop')}));
 add(root,'h3','Próximas ações contextualizadas');loop.next_actions.forEach(a=>{const e=add(root,'div',undefined,'entry');add(e,'strong',a.action);add(e,'p',a.why)});
 const f=add(root,'form');add(f,'h3','Registrar resultado real');const kind=formField(f,'Tipo: interview, rejection, offer, application_sent, feedback ou milestone','kind','feedback');formField(f,'O que aconteceu?','description','','textarea',true);const jl=add(f,'label','Vaga relacionada (opcional)');const sel=add(jl,'select');sel.name='job_id';let blank=el('option','Sem vaga específica');blank.value='';sel.append(blank);jobs.forEach(j=>{const o=el('option',j.title+' · '+j.company);o.value=j.id;sel.append(o)});f.append(action('Registrar resultado',async()=>{const v=Object.fromEntries(new FormData(f));await api('/career/outcomes','POST',{kind:v.kind,description:v.description,job_id:v.job_id?Number(v.job_id):null});await show('loop')}));
 add(root,'h3','Resultados registrados');outcomes.forEach(o=>{const e=add(root,'div',undefined,'entry');add(e,'strong',o.kind);add(e,'p',o.description)});
 add(root,'h3','Histórico de check-ins');if(!history.length)add(root,'p','Registre seu primeiro check-in para criar uma linha de base.');history.forEach(h=>{const e=add(root,'div',undefined,'entry');add(e,'strong',new Date(h.created_at).toLocaleString('pt-BR'));add(e,'p','Evidências: '+h.metrics.evidence+' · Ligações: '+h.metrics.links+' · Tarefas concluídas: '+h.metrics.tasks_completed)})
}
async function premium(b){const root=panel('Career Professional');add(root,'p','O plano pago desbloqueia comparação por vaga, currículo baseado nas evidências e preparação para entrevistas. Sem promessa de contratação.');add(root,'p','Status: '+b.status);if(!b.premium_enabled)root.append(action('Iniciar assinatura',async()=>{const r=await api('/billing/checkout','POST');if(!r.url.startsWith('https://'))throw Error('URL de pagamento inválida');location.assign(r.url)}));root.append(action('Gerenciar assinatura',async()=>{const r=await api('/billing/portal','POST');if(!r.url.startsWith('https://'))throw Error('URL do portal inválida');location.assign(r.url)},true));if(b.premium_enabled){root.append(action('Gerar currículo',async()=>{const r=await api('/resume');const pre=add(root,'pre',r.text);pre.style.whiteSpace='pre-wrap'},true))}}
async function account(){const me=await api('/me');const root=panel('Conta e privacidade');add(root,'p','E-mail: '+me.email);root.append(action('Exportar meus dados',async()=>{const data=await api('/account/export');const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='job-agent-meus-dados.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}));const f=add(root,'form');add(f,'h3','Alterar senha');formField(f,'Senha atual','current_password','','password',true);formField(f,'Nova senha','new_password','','password',true);f.append(action('Alterar senha e encerrar sessões',async()=>{await api('/auth/change-password','POST',Object.fromEntries(new FormData(f)));token='';sessionStorage.removeItem('jobagent_token');await show()}));add(root,'h3','Excluir conta');root.append(action('Solicitar exclusão',async()=>{const password=prompt('Digite sua senha para confirmar a exclusão definitiva.');if(!password)return;if(!confirm('Tem certeza? Seus dados serão excluídos.'))return;await api('/account/delete','POST',{password});token='';sessionStorage.removeItem('jobagent_token');await show()},true))}
$('authForm').onsubmit=async e=>{e.preventDefault();try{const r=await api('/auth/login','POST',{email:$('email').value,password:$('password').value});token=r.access_token;sessionStorage.setItem('jobagent_token',token);note('Bem-vindo ao Job Agent');await show('dashboard')}catch(err){note(err.message)}};
$('register').onclick=async()=>{try{await api('/auth/register','POST',{email:$('email').value,password:$('password').value});note('Conta criada. Agora clique em Entrar.')}catch(err){note(err.message)}};
$('logout').onclick=async()=>{try{await api('/auth/logout','POST')}catch{}token='';sessionStorage.removeItem('jobagent_token');await show()};document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));show();


async function evidenceAssessment(id,container){
 const history=await api('/evidence/'+id+'/assessments');
 const section=add(container,'div',undefined,'entry');add(section,'h3','Força da documentação (não é proficiência)');
 if(history.length){const last=history[0];add(section,'p','Última avaliação: '+last.result.documentation_score+'/100 · '+last.result.documentation_band);}
 const form=add(section,'form');
 for(const [field,label] of [['scope','Contexto e escopo'],['personal_contribution','Sua contribuição específica'],['method','Método, ferramentas e decisões'],['result','Resultados reais observados'],['limitations','Limitações, desafios e incertezas']])formField(form,label,field,'','textarea');
 form.append(action('Salvar avaliação e histórico',async()=>{
   const data=Object.fromEntries(new FormData(form));const response=await api('/evidence/'+id+'/assessments','POST',data);
   add(section,'p','Documentação: '+response.result.documentation_score+'/100. '+response.result.caveats.join(' '));
 }));
}


async function artifactReviewView(id,container){
 const history=await api('/evidence/'+id+'/artifact-reviews');
 const root=add(container,'div',undefined,'entry');add(root,'h3','Inventário técnico — sem execução de código');
 add(root,'p','Cole um JSON com arquivos de texto e seus caminhos. NÃO envie senhas, tokens, dados privados ou repositórios inteiros. O código não é executado e o conteúdo não é armazenado: apenas o inventário e seu hash.');
 if(history.length){const r=history[0].result;add(root,'p','Última análise: '+r.file_count+' arquivos · '+Object.entries(r.checks).filter(x=>x[1]).length+'/5 categorias presentes. Autoria e testes não verificados.');}
 const input=add(root,'textarea');input.rows=8;input.placeholder='[{"path":"src/app.py","content":"print(123)"},{"path":"tests/test_app.py","content":"def test_ok(): assert True"}]';
 root.append(action('Analisar arquivos fornecidos',async()=>{
   let files;try{files=JSON.parse(input.value)}catch{throw Error('JSON inválido. Informe uma lista de arquivos.')}
   const result=await api('/evidence/'+id+'/artifact-reviews','POST',{files});
   add(root,'p','Categorias presentes: '+Object.entries(result.result.checks).filter(x=>x[1]).map(x=>x[0]).join(', '));
   add(root,'p',result.result.interpretation);
 }));
}

async function technicalReviewView(id,container){
 const history=await api('/evidence/'+id+'/technical-reviews');
 const root=add(container,'div',undefined,'entry');add(root,'h3','Revisão técnica estática — sem execução');
 add(root,'p','Análise heurística Python. Metadados de commits são declarações não verificadas. Não envie segredos.');
 if(history.length){const last=history[0].result;add(root,'p','Última revisão: '+last.statistics.python_files+' arquivos Python · '+last.static_findings.length+' observações. Testes NÃO executados.');}
 const filesInput=add(root,'textarea');filesInput.rows=7;filesInput.placeholder='[{"path":"src/app.py","content":"def f():\\n    return 1"}]';
 const commitsInput=add(root,'textarea');commitsInput.rows=3;commitsInput.placeholder='Commits opcionais: [{"sha":"abcdef1234","author":"Nome declarado","files":["src/app.py"]}]';
 root.append(action('Revisar estaticamente',async()=>{
   let files,commits=[];try{files=JSON.parse(filesInput.value);if(commitsInput.value.trim())commits=JSON.parse(commitsInput.value)}catch{throw Error('JSON inválido')}
   const response=await api('/evidence/'+id+'/technical-reviews','POST',{files,commits});const result=response.result;
   add(root,'p','Arquivos Python analisados: '+(result.statistics.python_files||0)+'; observações: '+result.static_findings.length);
   result.static_findings.forEach(f=>add(root,'p',f.path+':'+f.line+' — '+f.rule+' — '+f.detail));
   add(root,'p','Autoria não verificada. Testes não executados. Ausência de alertas não comprova segurança.');
 }));
}

async function importResume(){
 const root=panel('Importação assistida de currículo');
 add(root,'p','Envie PDF, DOCX ou TXT (até 2 MB), ou cole o texto. Revise todas as sugestões antes de salvar. Não envie CPF ou dados sensíveis.');
 const fileLabel=add(root,'label','Selecionar currículo');const file=add(fileLabel,'input');file.type='file';file.accept='.pdf,.docx,.txt';
 const f=add(root,'form');const input=formField(f,'Ou cole o texto','resume','','textarea',false);input.maxLength=25000;input.rows=8;
 const preview=add(root,'div');
 async function renderPreview(r){
  clear(preview);add(preview,'h3','Revise os dados antes de confirmar');
  const roleLabel=add(preview,'label','Cargo-alvo (opcional)');const role=add(roleLabel,'input');role.maxLength=120;role.value=r.target_role_draft||'';
  const drafts=[];
  for(const draft of (r.evidence_drafts||[])){
   const section=add(preview,'div',undefined,'entry');const label=add(section,'label');const checkbox=add(label,'input');checkbox.type='checkbox';checkbox.checked=true;add(label,'span',' Incluir '+draft.kind);
   const title=formField(section,'Título — corrija se necessário','title',draft.title,'text',true);title.maxLength=160;
   const description=formField(section,'Descrição extraída — confirme os fatos','description',draft.description,'textarea',true);description.maxLength=4000;
   drafts.push({checkbox,title,description,kind:draft.kind});
  }
  add(preview,'h4','Menções de competências (não comprovadas)');
  const selected=[];
  (r.skill_mentions||[]).forEach(skill=>{const label=add(preview,'label');const cb=add(label,'input');cb.type='checkbox';cb.checked=false;cb.value=skill;add(label,'span',' '+skill);selected.push(cb)});
  add(preview,'p',(r.limitations||[]).concat(r.caveats||[]).join(' '));
  preview.append(action('Confirmar informações e ver próximas ações',async()=>{
   const evidence=drafts.filter(x=>x.checkbox.checked).map(x=>({kind:x.kind,title:x.title.value.trim(),description:x.description.value.trim(),url:''}));
   evidence.push(...selected.filter(x=>x.checked).map(x=>({kind:'skill',title:x.value,description:'Menção declarada no currículo; proficiência não verificada.',url:''})));
   if(!evidence.length&&!role.value.trim())throw Error('Confirme ao menos uma informação ou defina um cargo-alvo');
   const payload={evidence,target_role:role.value.trim()||null};
   try{await api('/import/resume/confirm','POST',payload)}catch(err){
     if(!err.message.includes('possible_duplicate')&&!err.message.includes('Possíveis duplicidades'))throw err;
     const conflict=err.message;
     if(!confirm('Foram encontradas evidências parecidas com registros existentes. Confira antes de prosseguir. '+conflict+'\nDeseja incluir mesmo assim?'))return;
     await api('/import/resume/confirm','POST',{...payload,allow_possible_duplicates:true});
   }
   await show('diagnostic');
  }));
 }
 f.append(action('Analisar sem salvar',async()=>{
  if(file.files.length){const selectedFile=file.files[0];if(selectedFile.size>2000000)throw Error('Limite de 2 MB');
   const body=new FormData();body.append('file',selectedFile);
   const response=await fetch('/api/import/resume/file-preview',{method:'POST',headers:{Authorization:'Bearer '+token},body});
   const result=await response.json();if(!response.ok)throw Error(result.detail||'Erro de importação');await renderPreview(result);
  }else{await renderPreview(await api('/import/resume/preview','POST',{text:input.value}))}
 }));
}


async function masterView(){
 const data=await api('/master-profile'),root=panel('Perfil mestre estruturado');
 add(root,'p','Registre experiências, projetos, formação e competências com campos reutilizáveis. Os dados continuam declarados até verificação independente.');
 const f=add(root,'form');
 formField(f,'Categoria: experience, project, education, certificate, language ou skill','category','experience');
 formField(f,'Título','title','', 'text',true);formField(f,'Organização','organization');
 formField(f,'Início (AAAA-MM)','start_date');formField(f,'Fim (AAAA-MM)','end_date');
 formField(f,'Descrição','description','','textarea');
 f.append(action('Adicionar ao perfil',async()=>{const v=Object.fromEntries(new FormData(f));await api('/master-profile/items','POST',v);await show('master')}));
 for(const item of data.items){const e=add(root,'div',undefined,'entry');add(e,'strong',item.title+' · '+item.category);add(e,'p',[item.organization,item.start_date,item.end_date].filter(Boolean).join(' · '));add(e,'p',item.description);e.append(action('Editar',async()=>{const edit=add(e,'form');for(const [key,label] of [['category','Categoria'],['title','Título'],['organization','Organização'],['start_date','Início'],['end_date','Fim'],['description','Descrição']])formField(edit,label,key,item[key]||'',key==='description'?'textarea':'text');edit.append(action('Salvar',async()=>{await api('/master-profile/items/'+item.id,'PUT',Object.fromEntries(new FormData(edit)));await show('master')}))},true));e.append(action('Excluir',async()=>{if(confirm('Excluir item do perfil?')){await api('/master-profile/items/'+item.id,'DELETE');await show('master')}},true))}
}
async function ledgerView(){
 const data=await api('/fact-ledger?include_history=true'),root=panel('Fact Ledger — origem e histórico');
 const review=await api('/fact-ledger/contradictions');
 if(review.conflicts.length){add(root,'h3','Divergências para revisar');for(const c of review.conflicts){const entry=add(root,'div',undefined,'entry');add(entry,'strong',c.subject+' · '+c.predicate);add(entry,'p',c.facts.map(f=>'#'+f.id+': '+f.value).join(' | '));add(entry,'small',c.reason)}}
 add(root,'p','Cada fato é uma declaração rastreável. Origem informada não significa fonte autenticada. Correções preservam a versão anterior.');
 const f=add(root,'form');formField(f,'Assunto','subject','', 'text',true);formField(f,'Predicado (ex.: utilizou_ferramenta)','predicate','utilizou_ferramenta','text',true);formField(f,'Informação','value','', 'textarea',true);formField(f,'Origem: user_statement, resume_import, evidence ou artifact','source_type','user_statement');formField(f,'Referência da origem','source_reference');
 f.append(action('Registrar declaração',async()=>{await api('/fact-ledger','POST',Object.fromEntries(new FormData(f)));await show('ledger')}));
 for(const x of data.facts){const e=add(root,'div',undefined,'entry');add(e,'strong',x.subject+' · '+x.predicate+' · '+x.status);add(e,'p',x.value);add(e,'small',x.source_type+' · '+x.verification+' · '+(x.source_reference||'Sem referência'));if(x.status==='ACTIVE')e.append(action('Corrigir mantendo histórico',async()=>{const value=prompt('Novo valor:',x.value);if(value===null)return;const reason=prompt('Motivo da correção:');if(reason===null)return;await api('/fact-ledger/'+x.id+'/correct','POST',{value,reason});await show('ledger')},true))}
}

// v12.4: grounded draft UI is mounted in the existing diagnostic tab.
async function groundedPanel(){
 const root=panel('Currículo fundamentado no Fact Ledger');
 add(root,'p','Somente declarações ativas, com identificação da fonte. Nenhuma competência é certificada.');
 const jobs=await api('/jobs');const label=add(root,'label','Vaga de referência (opcional)');const select=add(label,'select');
 const empty=add(select,'option','Sem vaga');empty.value='';
 for(const job of jobs){const o=add(select,'option',job.title+' — '+job.company);o.value=job.id}
 const output=add(root,'pre');
 root.append(action('Gerar rascunho rastreável',async()=>{
  const result=await api('/resume/grounded-draft','POST',{job_id:select.value?Number(select.value):null});
  output.textContent=result.text+'\n\n'+result.notice;
  add(root,'p','Fontes: '+result.claims.map(x=>'Fato #'+x.fact_id+' ('+x.verification+')').join(', '));
 }));
}
