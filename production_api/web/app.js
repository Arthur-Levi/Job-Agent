'use strict';
const $=id=>document.getElementById(id);
let token=sessionStorage.getItem('jobagent_token')||'',tab='dashboard';
const safe=(x)=>String(x??'');
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=safe(text);if(cls)n.className=cls;return n}
function add(parent,tag,text,cls){const n=el(tag,text,cls);parent.append(n);return n}
function clear(node){node.replaceChildren()}
function note(message){$('message').textContent=message} 
function friendlyError(e){const m=String(e&&e.message||'').trim();if(!m||m==='Resposta inválida')return 'O servidor não enviou uma resposta válida. Tente novamente.';if(m[0]==='['||m[0]==='{')return 'Confira os campos preenchidos e tente novamente.';return m.length>220?'Não foi possível concluir. Confira os dados e tente novamente.':m.replace(/^Erro:\s*/i,'')}
async function api(path,method='GET',data){const headers={'Accept':'application/json'};if(token)headers.Authorization='Bearer '+token;if(data!==undefined)headers['Content-Type']='application/json';const r=await fetch('/api'+path,{method,headers,body:data===undefined?undefined:JSON.stringify(data)});let value;try{value=await r.json()}catch{throw Error(r.ok?'O servidor enviou dados inesperados.':'O servidor não enviou uma resposta válida. Tente novamente.')}if(!r.ok){const detail=value.detail;const msg=typeof detail==='string'?detail:(Array.isArray(detail)?detail.map(x=>String(x.msg||'Campo inválido')).slice(0,3).join(' · '):'Confira os campos e tente novamente.');throw Error(msg)}return value}
function formField(form,label,key,value='',type='text',required=false){const l=add(form,'label',label);const i=el(type==='textarea'?'textarea':'input');i.name=key;i.value=safe(value);if(type!=='textarea')i.type=type;i.required=required;l.append(i);return i}
function action(label,fn,secondary=false){
 const b=el('button',label);b.type='button';if(secondary)b.className='secondary';
 b.onclick=async()=>{
  if(b.disabled)return;
  b.disabled=true;b.setAttribute('aria-busy','true');
  const original=b.textContent;b.textContent='Processando...';
  let feedback=b.nextElementSibling;
  if(!feedback||!feedback.classList.contains('action-feedback')){
   feedback=el('span',undefined,'action-feedback');feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');
   b.insertAdjacentElement('afterend',feedback);
  }
  feedback.textContent='';
  try{
   await fn();
   if(b.isConnected)feedback.textContent='Concluído.';
  }catch(e){
   const msg=friendlyError(e);
   if(b.isConnected)feedback.textContent=msg;
  }finally{
   b.disabled=false;b.removeAttribute('aria-busy');b.textContent=original;
  }
 };
 return b;
}
function panel(title){const root=$('content');clear(root);add(root,'h2',title);return root}
let navVersion=0;
let navQueue=Promise.resolve();
function show(next=tab){
 const destination=next;tab=destination;const revision=++navVersion;
 const logged=!!token;
 document.body.classList.toggle('is-public',!logged);
 $('auth').hidden=logged;$('workspace').hidden=!logged;$('logout').hidden=!logged;
 note('');
 if(!logged){clear($('content'));return Promise.resolve()}
 document.querySelectorAll('[data-tab]').forEach(b=>{const active=b.dataset.tab===destination;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
 $('pageTitle').textContent=({dashboard:'Visão geral',import:'Importar currículo',master:'Perfil profissional estruturado',ledger:'Registro de fatos',diagnostic:'Diagnóstico profissional',evidence:'Minhas evidências',jobs:'Vagas e requisitos',applications:'Minhas candidaturas',tasks:'Plano de ação',graph:'Mapa de evidências',loop:'Evolução profissional',premium:'Career Professional',account:'Minha conta'})[destination]||destination;
 // Serialize navigation so a slow previous request cannot paint over a newer tab.
 // Pending destinations are discarded; the latest requested destination wins.
 clear($('content'));add($('content'),'p','Carregando página...','dashboard-loading');
 navQueue=navQueue.catch(()=>{}).then(async()=>{
  if(revision!==navVersion)return;
  try{
   let billing;
   try{billing=await api('/billing/status')}
   catch{billing={premium_enabled:false,status:'temporariamente indisponível',billing_unavailable:true}}
   if(revision!==navVersion)return;
   $('planBadge').textContent=billing.billing_unavailable?'Plano indisponível':(billing.premium_enabled?'Career Professional ativo':'Plano gratuito');
   clear($('content'));
   if(destination==='dashboard')await dashboard();
   else if(destination==='import')await importResume();
   else if(destination==='master')await masterView();
   else if(destination==='ledger')await ledgerView();
   else if(destination==='diagnostic'){await diagnostic();if(revision===navVersion){await groundedPanel();if(revision===navVersion)organizeDiagnosticTabs()}}
   else if(destination==='evidence')await evidence();
   else if(destination==='jobs')await jobs();
   else if(destination==='applications')await applications();
   else if(destination==='tasks')await tasks();
   else if(destination==='graph')await graphView();
   else if(destination==='loop')await loopView();
   else if(destination==='premium')await premium(billing);
   else if(destination==='account')await account();
  }catch(e){
   if(revision!==navVersion)return;
   const msg=friendlyError(e);
   clear($('content'));add($('content'),'h2','Não foi possível carregar esta página');
   add($('content'),'p',msg,'action-feedback');
   $('content').append(action('Tentar novamente',()=>show(destination)));
   if(e.message.includes('Sessão inválida')||e.message.includes('Autenticação necessária')){
    token='';sessionStorage.removeItem('jobagent_token');sessionStorage.removeItem('jobagent_resume_draft');return show();
   }
  }
 });
 return navQueue;
}
async function openDashboardProfileEditor(){
 const root=$('content');
 const me=await api('/profile');
 const section=add(root,'section',undefined,'dashboard-section');
 section.id='onboarding-profile-editor';
 add(section,'h3','Complete seu perfil profissional');
 add(section,'p','Informe seu cargo-alvo e descreva sua experiência real para avançar no onboarding.');
 const form=add(section,'form');
 formField(form,'Nome','name',me.name||'','text');
 const role=formField(form,'Cargo-alvo','target_role',me.target_role||'','text');role.maxLength=120;
 formField(form,'Localização','location',me.location||'','text');
 const summary=formField(form,'Resumo da experiência profissional','summary',me.summary||'','textarea');summary.rows=5;
 form.append(action('Salvar e continuar',async()=>{
  const updated={...me};for(const input of form.querySelectorAll('[name]'))updated[input.name]=input.value;
  await api('/profile','PUT',updated);await show('dashboard');
 }));
 section.scrollIntoView({behavior:'smooth',block:'start'});
 role.focus();
}
async function dashboard(){
 const root=panel('Seu centro de carreira');root.classList.add('dashboard-panel');
 const intro=add(root,'div',undefined,'dashboard-intro');
 const lead=add(intro,'div');add(lead,'p','SEU PRÓXIMO MOVIMENTO','eyebrow');
 add(lead,'h2','Seu próximo passo, sem complicação.');
 add(lead,'p','Comece pelo currículo ou informe seu objetivo. Depois, consulte seu diagnóstico.');
 const start=add(intro,'div',undefined,'dashboard-intro-actions');
 start.append(action('Analisar meu currículo',async()=>show('import')));
 start.append(action('Preencher meu perfil',async()=>show('master'),true));
 const status=add(root,'div',undefined,'dashboard-loading');status.setAttribute('role','status');status.textContent='Carregando seu progresso...';
 const results=await Promise.allSettled([api('/dashboard'),api('/progress'),api('/onboarding'),api('/journey/first-result'),api('/career/weekly-brief')]);
 status.remove();
 const [d,p,onboard,journey,brief]=results.map(x=>x.status==='fulfilled'?x.value:null);
 const finished=!!(onboard&&Number(onboard.total)>0&&Number(onboard.completed)>=Number(onboard.total));const quickStart=document.querySelector('.quick-start');if(quickStart)quickStart.hidden=true;
 if(finished){
  intro.classList.add('dashboard-intro-complete');
  lead.querySelector('h2').textContent='Sua carreira, em movimento.';
  lead.querySelector('p:not(.eyebrow)').textContent='Seu perfil inicial está organizado. Continue acompanhando oportunidades e suas próximas ações.';
  lead.querySelector('.eyebrow').textContent='WORKSPACE ATIVO';
  start.replaceChildren();
  start.append(action('Ver diagnóstico',async()=>show('diagnostic')));
  start.append(action('Plano de ação',async()=>show('tasks'),true));
 }
 if(results.some(x=>x.status==='rejected')){
  const warning=add(root,'div',undefined,'dashboard-notice');
  add(warning,'strong','Algumas informações estão temporariamente indisponíveis.');
  add(warning,'p','Você ainda pode importar seu currículo, preencher seu perfil e acessar os módulos pelo menu.');
 }
 const progress=add(root,'section',undefined,'dashboard-section');
 const ph=add(progress,'div',undefined,'dashboard-section-heading');
 add(ph,'h3',finished?'Seu perfil está preparado':'Prepare seu primeiro diagnóstico');
 if(onboard&&Number(onboard.total)>0){
  const completed=Math.max(0,Math.min(Number(onboard.completed)||0,Number(onboard.total)));
  add(ph,'span',completed+' de '+onboard.total+' etapas','progress-count');
  const track=add(progress,'div',undefined,'progress-track');track.setAttribute('role','progressbar');track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax',String(onboard.total));track.setAttribute('aria-valuenow',String(completed));
  const fill=add(track,'div',undefined,'progress-fill');fill.style.width=(completed/onboard.total*100)+'%';

  const pendingSteps=(onboard.steps||[]).filter(step=>!step.done);
  const stepsDetails=add(progress,'details',undefined,'dashboard-optional');add(stepsDetails,'summary','Ver todas as etapas ('+pendingSteps.length+' pendentes)');
  const stepsList=add(stepsDetails,'div',undefined,'onboarding-steps');
  if(pendingSteps.length){const next=pendingSteps[0];const lead=add(progress,'div',undefined,'dashboard-priority-step');add(lead,'strong',next.label);const to=({target:'master',summary:'master',evidence:'evidence',job:'jobs'})[next.key]||next.next_tab||'import';lead.append(action('Continuar etapa',()=>show(to)));}
  for(const [index,step] of (onboard.steps||[]).entries()){
   const item=add(stepsList,'div',undefined,'onboarding-step'+(step.done?' is-done':''));
   add(item,'span',step.done?'✓':String(index+1).padStart(2,'0'),'step-index');
   const copy=add(item,'div',undefined,'step-copy');add(copy,'strong',step.label);
   add(copy,'small',step.done?'Concluído':'Pendente');
   if(!step.done){const destination=({target:'profile',summary:'profile',evidence:'evidence',job:'jobs'})[step.key]||step.next_tab;if(destination)item.append(action('Continuar →',async()=>{if(destination==='profile'){await show('dashboard');await openDashboardProfileEditor()}else await show(destination)},true));}
  }
 }else{
  add(progress,'p','Comece importando seu currículo ou preenchendo o perfil para iniciar sua jornada.');
 }
 if(journey){
  const next=add(root,'section',undefined,'dashboard-next');
  add(next,'p','PRIORIDADE ATUAL','eyebrow');add(next,'h3','Seu próximo passo profissional');
  add(next,'p',journey.first_result||'Complete seu perfil para receber orientações contextualizadas.');
  const actions=add(next,'div',undefined,'dashboard-next-actions');
  for(const x of (journey.next_actions||[]).slice(0,2)){
   const item=add(actions,'div',undefined,'next-action');
   const copy=add(item,'div');add(copy,'strong',x.title);add(copy,'p',x.why);
   if(x.next_tab)item.append(action('Realizar →',async()=>show(x.next_tab),true));
  }
 }
 const detail=add(root,'details',undefined,'dashboard-optional');add(detail,'summary','Ver números e resumo da semana');
 const metrics=add(detail,'section',undefined,'dashboard-section');
 add(metrics,'h3','Seu workspace em números');
 const grid=add(metrics,'div',undefined,'grid');
 const cards=[['Evidências',d?.evidence],['Vagas salvas',d?.jobs],['Candidaturas',d?.applications],['Tarefas concluídas',p?p.tasks_done+' / '+p.tasks_total:null]];
 for(const [label,value] of cards){
  const tile=add(grid,'div',undefined,'tile');
  add(tile,'div',value===null||value===undefined?'—':value,'number');
  add(tile,'p',label);
 }
 if(brief){
  const weekly=add(detail,'section',undefined,'dashboard-section dashboard-weekly');
  add(weekly,'h3','Resumo da semana');
  add(weekly,'p','Tarefas concluídas: '+brief.tasks.completed+' de '+brief.tasks.total+' · Horas disponíveis: '+brief.hours_available);
  for(const x of (brief.next_actions||[]).slice(0,3)){
   const item=add(weekly,'div',undefined,'entry');add(item,'strong',x.action);add(item,'small',x.why);
  }
 }
 add(root,'p','As informações são declaradas e não representam certificação de competências ou probabilidade de contratação.','dashboard-disclaimer');
}
async function diagnostic(){
 const [d,priority]=await Promise.all([api('/intelligence'),api('/diagnostic/priority-actions')]);const root=panel('Career Intelligence — diagnóstico rastreável');
 add(root,'h3','Suas próximas ações priorizadas');priority.actions.forEach(a=>{const item=add(root,'div',undefined,'entry');add(item,'strong',a.action);add(item,'p',a.why);item.append(action('Agir agora',async()=>show(a.next_tab),true))});
 add(root,'p','Análise por requisitos de vagas reais e evidências declaradas. Não verificamos automaticamente competências nem calculamos chances de contratação.');
 const c=d.quality.coverage,g=add(root,'div',undefined,'grid');
 for(const [label,value] of [['Vagas com requisitos',c.jobs_with_requirements+' / '+c.total_jobs],['Requisitos distintos',c.total_requirements],['Requisitos com indícios',c.requirements_with_candidates],['Evidências com URL',c.evidence_with_sources+' / '+c.total_evidence]]){const tile=add(g,'div',undefined,'tile');add(tile,'div',value,'number');add(tile,'p',label)}
 add(root,'h3','As 3 próximas ações');d.top_actions.forEach((a,i)=>{const e=add(root,'div',undefined,'entry');add(e,'strong',(i+1)+'. '+a.action);add(e,'p','Motivo: '+a.why);if(a.linked_jobs.length)add(e,'small','Vagas relacionadas: '+a.linked_jobs.join(', '));e.append(action('Adicionar ao meu plano',async()=>{await api('/tasks','POST',{title:a.action.slice(0,300)});await show('tasks')},true))});
 add(root,'h3','Prioridades e lacunas');if(!d.requirement_priorities.length)add(root,'p','Cadastre vagas reais e seus requisitos para iniciar a comparação.');
 d.requirement_priorities.forEach(r=>{const e=add(root,'div',undefined,'entry');add(e,'strong',r.requirement+' · '+r.jobs_requiring+' vaga(s)');add(e,'p',r.state==='NOT_DOCUMENTED'?'Não documentado (não significa desconhecimento)':'Indícios textuais — não verificados');add(e,'small',r.rationale);r.evidence_refs.forEach(x=>add(e,'p','Evidência #'+x.evidence_id+': '+x.title+' ('+x.status+')'))});
 add(root,'h3','Oportunidades por indícios documentais');const ranked=await api('/career/opportunity-priorities');ranked.opportunities.forEach(j=>{const e=add(root,'div',undefined,'entry');add(e,'strong',j.title+' · '+j.company);add(e,'p',j.possible_documentary_matches+'/'+j.requirements_total+' requisitos com indícios declarados. Não é uma chance de contratação.')});add(root,'h3','Comparação por oportunidade');d.opportunities.forEach(j=>{const e=add(root,'div',undefined,'entry');add(e,'strong',j.title+' · '+j.company);add(e,'p',j.documented_candidates+' requisitos com indícios; '+j.not_documented+' sem evidência textual.');j.requirements.forEach(r=>add(e,'small',r.requirement+' — '+(r.state==='NOT_DOCUMENTED'?'não documentado':'possível evidência declarada')))});
 add(root,'h3','Limitações e transparência');d.uncertainties.forEach(x=>add(root,'p','• '+x));d.quality.data_quality_notes.forEach(x=>add(root,'p','• '+x));
}

// B5.2: Reorganize the already-rendered diagnostic without new requests or data writes.
// Moving existing DOM nodes preserves button handlers, selection, draft text and provenance.
function organizeDiagnosticTabs(){
 const content=$('content');
 const title=content.querySelector(':scope > h2');
 const grounded=content.querySelector(':scope > section.dashboard-section');
 if(!title||!grounded)return;
 const groups=[
  {id:'overview',label:'Visão geral',nodes:[]},
  {id:'requirements',label:'Requisitos',nodes:[]},
  {id:'resume',label:'Currículo fundamentado',nodes:[]},
  {id:'actions',label:'Próximas ações',nodes:[]}
 ];
 const byId=Object.fromEntries(groups.map(g=>[g.id,g]));
 let active='actions';
 for(const node of [...content.children]){
  if(node===title||node===grounded)continue;
  if(node.tagName==='H3'){
   const heading=node.textContent.trim();
   if(heading==='Suas próximas ações priorizadas'||heading==='As 3 próximas ações')active='actions';
   else if(heading==='Prioridades e lacunas'||heading==='Oportunidades por indícios documentais'||heading==='Comparação por oportunidade')active='requirements';
   else if(heading==='Limitações e transparência')active='overview';
  }else if(node.classList.contains('grid'))active='overview';
  byId[active].nodes.push(node);
 }
 byId.resume.nodes.push(grounded);
 const tabs=el('div',undefined,'diagnostic-tabs');
 tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Seções do diagnóstico');
 const panels=[];
 for(const group of groups){
  const tabButton=add(tabs,'button',group.label,'diagnostic-tab');
  tabButton.type='button';tabButton.id='diag-tab-'+group.id;tabButton.setAttribute('role','tab');
  tabButton.setAttribute('aria-controls','diag-panel-'+group.id);
  const panelNode=el('section',undefined,'diagnostic-tab-panel');
  panelNode.id='diag-panel-'+group.id;panelNode.setAttribute('role','tabpanel');
  panelNode.setAttribute('aria-labelledby',tabButton.id);panelNode.tabIndex=0;
  for(const child of group.nodes)panelNode.append(child);
  panels.push({id:group.id,button:tabButton,panel:panelNode});
 }
 const select=id=>{
  for(const item of panels){
   const chosen=item.id===id;
   item.button.setAttribute('aria-selected',String(chosen));
   item.button.tabIndex=chosen?0:-1;
   item.panel.hidden=!chosen;
  }
 };
 for(let i=0;i<panels.length;i++){
  const item=panels[i];
  item.button.addEventListener('click',()=>select(item.id));
  item.button.addEventListener('keydown',event=>{
   if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
   event.preventDefault();
   const next=event.key==='Home'?0:event.key==='End'?panels.length-1:
    (i+(event.key==='ArrowRight'?1:-1)+panels.length)%panels.length;
   select(panels[next].id);panels[next].button.focus();
  });
 }
 content.replaceChildren(title,tabs,...panels.map(x=>x.panel));
 select('overview');
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
async function jobs(){
 const items=await api('/jobs');
 const root=panel('Vagas reais e seus requisitos');
 add(root,'p','Cole uma descrição fornecida por você. A análise sugere campos, mas nada será salvo sem sua confirmação.');
 const inputLabel=add(root,'label','Descrição da oportunidade (texto fornecido por você)');
 const raw=add(inputLabel,'textarea');raw.rows=7;raw.maxLength=12000;raw.placeholder='Ex.: Cargo: Desenvolvedor Backend\\nEmpresa: Exemplo\\nRequisitos:\\n- Python\\n- SQL';
 const draftKey='jobagent_job_draft';
 raw.value=sessionStorage.getItem(draftKey)||'';
 raw.addEventListener('input',()=>sessionStorage.setItem(draftKey,raw.value));
 const preview=add(root,'div',undefined,'import-preview');preview.setAttribute('aria-live','polite');
 const controls=add(root,'div',undefined,'resume-review-controls');
 controls.append(action('Analisar vaga sem salvar',async()=>{
  if(raw.value.trim().length<40)throw Error('Cole uma vaga com ao menos 40 caracteres.');
  const r=await api('/jobs/text-preview','POST',{text:raw.value});
  clear(preview);
  add(preview,'h3','Revise a vaga antes de salvar');
  add(preview,'p','Prévia gerada a partir do texto informado. Nada foi salvo. Confirme somente requisitos que realmente aparecem na oportunidade.','import-guidance');
  const form=add(preview,'form');
  const title=formField(form,'Cargo','title',r.title_draft||'','text',true);title.maxLength=160;
  const company=formField(form,'Empresa','company',r.company_draft||'','text',true);company.maxLength=160;
  const description=formField(form,'Descrição','description',r.description_draft||'','textarea',true);description.maxLength=10000;
  const source=formField(form,'URL da vaga (opcional)','source_url','','url');source.maxLength=1000;
  add(form,'h4','Requisitos sugeridos — revise cada um');
  const requirementFields=[];
  const holder=add(form,'div');
  const pushRequirement=(value='')=>{
   if(requirementFields.length>=40)return;
   const row=add(holder,'div',undefined,'job-requirement-row');
   const field=add(row,'input');field.type='text';field.maxLength=160;field.value=value;field.setAttribute('aria-label','Requisito da vaga');
   const remove=action('Remover',()=>{row.remove();requirementFields.splice(requirementFields.indexOf(field),1)},true);
   row.append(remove);requirementFields.push(field);
  };
  (r.requirements_draft||[]).forEach(x=>pushRequirement(x));
  form.append(action('Adicionar requisito',()=>pushRequirement(''),true));
  add(form,'p','Menções automáticas são apenas sugestões; revise antes de confirmar.','import-guidance');
  form.append(action('Confirmar e salvar vaga',async()=>{
   const requirements=[...new Set(requirementFields.map(x=>x.value.trim()).filter(Boolean))];
   const payload={title:title.value.trim(),company:company.value.trim(),description:description.value.trim(),requirements,source_url:source.value.trim()};
   if(payload.title.length<2||payload.company.length<2||payload.description.length<10)throw Error('Informe cargo, empresa e descrição da vaga.');
   await api('/jobs','POST',payload);
   sessionStorage.removeItem(draftKey);
   await show('jobs');
  }));
 }));
 add(root,'h3','Vagas cadastradas');
 if(!items.length)add(root,'p','Ainda não há vagas cadastradas. Cole uma oportunidade acima para começar.');
 items.forEach(x=>{
  const e=add(root,'div',undefined,'entry');
  add(e,'h3',x.title+' · '+x.company);
  add(e,'p',x.requirements.join(' · ')||'Requisitos não informados');
  e.append(action('Analisar requisitos',async()=>{
   const result=await api('/jobs/'+x.id+'/guidance');
   let previous=e.querySelector('.job-guidance');if(previous)previous.remove();
   const area=add(e,'div',undefined,'job-guidance');
   add(area,'h4','Análise desta oportunidade');
   add(area,'p',result.counts.mentioned_unverified+' requisito(s) com menções declaradas · '+result.counts.not_documented+' sem documentação textual.');
   add(area,'p','Não é pontuação de adequação nem previsão de contratação.','import-guidance');
   for(const r of result.requirements){
    const details=add(area,'details',undefined,'entry import-evidence-card');
    add(details,'summary',r.requirement+' — '+r.label);
    add(details,'p',r.explanation);
    for(const ev of r.evidence)add(details,'p','Evidência declarada: '+ev.title);
    add(details,'p',r.next_action);
    details.append(action('Adicionar ação ao meu plano',async()=>{
     await api('/tasks','POST',{title:r.action_title.slice(0,300)});
     await show('tasks');
    },true));
   }
   if(!result.requirements.length)add(area,'p','Cadastre requisitos reais nesta vaga para obter uma comparação.');
  }));
  e.append(action('Registrar candidatura',async()=>{await api('/applications','POST',{job_id:x.id,status:'saved',notes:''});await show('applications')},true));
  e.append(action('Comparar Premium',async()=>{const m=await api('/jobs/'+x.id+'/match');note('Correspondências potenciais: '+m.potential_matches.length+' | Não documentados: '+m.unresolved_requirements.length)},true));
  e.append(action('Preparar entrevista Premium',async()=>{const r=await api('/jobs/'+x.id+'/interview');const section=add(e,'div');add(section,'h3','Perguntas de preparação');r.questions.forEach(q=>add(section,'p',q))},true));
  e.append(action('Excluir',async()=>{if(confirm('Excluir a vaga e suas candidaturas?')){await api('/jobs/'+x.id,'DELETE');await show('jobs')}},true));
 });
}
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
async function account(){const me=await api('/me');const root=panel('Conta e privacidade');add(root,'p','E-mail: '+me.email);root.append(action('Exportar meus dados',async()=>{const data=await api('/account/export');const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='job-agent-meus-dados.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}));const f=add(root,'form');add(f,'h3','Alterar senha');formField(f,'Senha atual','current_password','','password',true);formField(f,'Nova senha','new_password','','password',true);f.append(action('Alterar senha e encerrar sessões',async()=>{await api('/auth/change-password','POST',Object.fromEntries(new FormData(f)));token='';sessionStorage.removeItem('jobagent_token');sessionStorage.removeItem('jobagent_resume_draft');await show()}));add(root,'h3','Excluir conta');root.append(action('Solicitar exclusão',async()=>{const password=prompt('Digite sua senha para confirmar a exclusão definitiva.');if(!password)return;if(!confirm('Tem certeza? Seus dados serão excluídos.'))return;await api('/account/delete','POST',{password});token='';sessionStorage.removeItem('jobagent_token');sessionStorage.removeItem('jobagent_resume_draft');await show()},true))}
$('authForm').onsubmit=async e=>{e.preventDefault();try{const r=await api('/auth/login','POST',{email:$('email').value,password:$('password').value});token=r.access_token;sessionStorage.removeItem('jobagent_resume_draft');sessionStorage.setItem('jobagent_token',token);note('Bem-vindo ao Job Agent');await show('dashboard')}catch(err){note(err.message)}};
$('register').onclick=async()=>{try{await api('/auth/register','POST',{email:$('email').value,password:$('password').value});note('Conta criada. Agora clique em Entrar.')}catch(err){note(err.message)}};
$('logout').onclick=async()=>{try{await api('/auth/logout','POST')}catch{}token='';sessionStorage.removeItem('jobagent_token');sessionStorage.removeItem('jobagent_resume_draft');await show()};document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));show();


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
 const status=add(root,'p','Etapa 1 de 3 · Envie seu currículo','import-stage');
 const fileLabel=add(root,'label','Selecionar currículo');const file=add(fileLabel,'input');file.type='file';file.accept='.pdf,.docx,.txt';
 const f=add(root,'form');const input=formField(f,'Ou cole o texto','resume',sessionStorage.getItem('jobagent_resume_draft')||'','textarea',false);input.maxLength=25000;input.rows=8;
 input.addEventListener('input',()=>{sessionStorage.setItem('jobagent_resume_draft',input.value);});
 const preview=add(root,'div');preview.className='import-preview';preview.setAttribute('aria-live','polite');
 file.addEventListener('change',()=>{if(file.files.length){input.disabled=true;status.textContent='Arquivo selecionado: '+file.files[0].name+' · Clique em Analisar sem salvar.'}else{input.disabled=false;status.textContent='Etapa 1 de 3 · Envie seu currículo'}});
 input.addEventListener('input',()=>{if(input.value.trim()&&file.files.length){file.value='';input.disabled=false} });
 async function renderPreview(r){
  clear(preview);
  status.textContent='Etapa 2 de 2 · Revise antes de confirmar';
  add(preview,'h3','Seu currículo, em resumo');
  add(preview,'p','Esta é uma prévia. Nada foi salvo no seu perfil. Revise e confirme somente informações verdadeiras.','import-guidance');
  const evidenceDrafts=Array.isArray(r.evidence_drafts)?r.evidence_drafts:[];
  const skills=Array.isArray(r.skill_mentions)?r.skill_mentions:[];
  const summary=add(preview,'div',undefined,'resume-summary');
  const counts=add(summary,'p',evidenceDrafts.length+' informação(ões) sugerida(s) · '+skills.length+' competência(s) mencionada(s)');
  counts.setAttribute('aria-live','polite');
  const roleLabel=add(preview,'label','Cargo-alvo (opcional)');
  const role=add(roleLabel,'input');role.maxLength=120;role.value=r.target_role_draft||'';
  add(preview,'h4','Informações encontradas');
  const controls=add(preview,'div',undefined,'resume-review-controls');
  const openAll=action('Revisar todos os detalhes',()=>{for(const x of drafts)x.section.open=true},true);
  controls.append(openAll);
  const drafts=[];
  for(const draft of evidenceDrafts){
   const section=add(preview,'details',undefined,'entry import-evidence-card');
   const heading=add(section,'summary',(draft.title||'Informação do currículo')+' · '+draft.kind);
   heading.title='Abrir para revisar esta informação';
   const label=add(section,'label');const checkbox=add(label,'input');checkbox.type='checkbox';checkbox.checked=true;
   add(label,'span',' Incluir no meu perfil');
   const title=formField(section,'Título — corrija se necessário','title',draft.title,'text',true);title.maxLength=160;
   const description=formField(section,'Descrição extraída — confirme os fatos','description',draft.description,'textarea',true);description.maxLength=4000;
   drafts.push({section,checkbox,title,description,kind:draft.kind});
  }
  if(!drafts.length)add(preview,'p','Nenhuma experiência estruturada foi identificada. Você pode informar seu cargo-alvo ou revisar as menções abaixo.');
  const skillBox=add(preview,'details',undefined,'entry import-evidence-card');
  add(skillBox,'summary','Competências mencionadas ('+skills.length+') — não comprovadas');
  add(skillBox,'p','Essas palavras aparecem no currículo, mas não significam que sua proficiência foi verificada. Selecione apenas as que deseja declarar.');
  const selected=[];
  for(const skill of skills){const label=add(skillBox,'label');const cb=add(label,'input');cb.type='checkbox';cb.checked=false;cb.value=skill;add(label,'span',' '+skill);selected.push(cb)}
  const warnings=[...(r.limitations||[]),...(r.caveats||[])].filter(x=>typeof x==='string'&&x.trim());
  if(warnings.length){const details=add(preview,'details',undefined,'entry');add(details,'summary','Limitações da análise');add(details,'p',warnings.join(' '))}
  preview.append(action('Confirmar e abrir diagnóstico',async()=>{
   const chosen=drafts.filter(x=>x.checkbox.checked);
   // A collapsed item can be accepted as extracted. Only user-edited items need expanded review.
   for(const x of chosen){
    if(!x.title.value.trim()||!x.description.value.trim()){
     x.section.open=true;
     x.title.focus();
     throw Error('Revise os campos obrigatórios do cartão aberto.');
    }
   }
   const evidence=chosen.map(x=>({kind:x.kind,title:x.title.value.trim(),description:x.description.value.trim(),url:''}));
   evidence.push(...selected.filter(x=>x.checked).map(x=>({kind:'skill',title:x.value,description:'Menção declarada no currículo; proficiência não verificada.',url:''})));
   if(!evidence.length&&!role.value.trim())throw Error('Selecione uma informação ou informe um cargo-alvo.');
   const payload={evidence,target_role:role.value.trim()||null};
   try{await api('/import/resume/confirm','POST',payload)}catch(err){
    if(!err.message.includes('possible_duplicate')&&!err.message.includes('Possíveis duplicidades'))throw err;
    if(!confirm('Existem informações semelhantes já cadastradas. Deseja confirmar mesmo assim?'))return;
    await api('/import/resume/confirm','POST',{...payload,allow_possible_duplicates:true});
   }
   status.textContent='Informações confirmadas. Abrindo diagnóstico...';
   sessionStorage.removeItem('jobagent_resume_draft');
   await show('diagnostic');
  }));
 }
 f.append(action('Analisar sem salvar',async()=>{
  clear(preview);
  if(!file.files.length&&!input.value.trim())throw Error('Selecione um arquivo ou cole o texto do currículo.');
  status.textContent='Analisando currículo, sem salvar dados...';
  try{
  if(file.files.length){const selectedFile=file.files[0];if(selectedFile.size>2000000)throw Error('Limite de 2 MB');
   const body=new FormData();body.append('file',selectedFile);
   const response=await fetch('/api/import/resume/file-preview',{method:'POST',headers:{Authorization:'Bearer '+token},body});
   let result;try{result=await response.json()}catch{throw Error('O servidor não enviou uma resposta válida. Tente novamente.')}if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Não foi possível analisar o arquivo. Confira o formato e tente novamente.');await renderPreview(result);
  }else{await renderPreview(await api('/import/resume/preview','POST',{text:input.value}))}
  }catch(e){status.textContent='Não foi possível analisar. Corrija o problema e tente novamente.';throw e}
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
 const root=add($('content'),'section',undefined,'dashboard-section');add(root,'h2','Currículo fundamentado no Fact Ledger');
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
