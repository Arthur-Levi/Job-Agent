'use strict';
/* Q1 browser acceptance with mocked API. No real account or database is mutated.
   Run from repository root: JOB_AGENT_URL=http://127.0.0.1:8001 node production_api/tests/verify_b52_q1_browser.cjs
   Requires locally installed playwright + chromium. */
const assert=require('node:assert/strict');
const { chromium }=require('playwright');
const base=process.env.JOB_AGENT_URL||'http://127.0.0.1:8001';
const sample={
 quality:{coverage:{jobs_with_requirements:1,total_jobs:1,total_requirements:1,requirements_with_candidates:0,evidence_with_sources:0,total_evidence:0},data_quality_notes:['Fonte ainda não verificada']},
 top_actions:[{action:'Atualizar portfólio',why:'Falta evidência',linked_jobs:[1]}],
 requirement_priorities:[{requirement:'Excel',jobs_requiring:1,state:'NOT_DOCUMENTED',rationale:'Sem documento',evidence_refs:[]}],
 opportunities:[{title:'Analista',company:'Empresa Teste',documented_candidates:0,not_documented:1,requirements:[{requirement:'Excel',state:'NOT_DOCUMENTED'}]}],
 uncertainties:['Competências ainda não verificadas']
};
let account='A',tasks=[],posts=0,logouts=0;
const json=(body,status=200)=>({status,contentType:'application/json',body:JSON.stringify(body)});
async function main(){
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const issues=[];
 page.on('pageerror',e=>issues.push(e.message));
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),p=url.pathname.replace(/^\/api/,'');
  const method=req.method();
  if(p==='/auth/login'&&method==='POST'){const data=req.postDataJSON();account=data.email.includes('b@')?'B':'A';return route.fulfill(json({access_token:'test-token-'+account,token_type:'bearer'}))}
  if(p==='/auth/logout'&&method==='POST'){logouts++;return route.fulfill(json({ok:true}))}
  if(p==='/billing/status')return route.fulfill(json({status:'inactive',premium_enabled:false}));
  if(p==='/intelligence')return route.fulfill(json(sample));
  if(p==='/diagnostic/priority-actions')return route.fulfill(json({actions:[{action:'Atualizar portfólio',why:'Falta evidência',next_tab:'tasks'}]}));
  if(p==='/career/opportunity-priorities')return route.fulfill(json({opportunities:[{title:'Analista',company:'Empresa Teste',possible_documentary_matches:0,requirements_total:1}]}));
  if(p==='/jobs')return route.fulfill(json([{id:1,title:'Analista',company:'Empresa Teste',requirements:['Excel']}]));
  if(p==='/resume/grounded-draft'&&method==='POST')return route.fulfill(json({text:'RASCUNHO PRIVADO '+account,notice:'Declaração não verificada',claims:[{fact_id:17,verification:'DECLARED'}]}));
  if(p==='/tasks'&&method==='POST'){posts++;const data=req.postDataJSON();tasks.push({id:posts,done:false,title:data.title});return route.fulfill(json({id:posts,...data}))}
  if(p==='/tasks')return route.fulfill(json(tasks));
  if(p==='/me')return route.fulfill(json({id:account==='A'?1:2,email:account==='A'?'a@teste.local':'b@teste.local'}));
  if(p==='/dashboard')return route.fulfill(json({}));
  if(p==='/progress')return route.fulfill(json({applications_by_status:{},tasks_done:0,tasks_total:0}));
  if(p==='/onboarding')return route.fulfill(json({total:0,completed:0,steps:[]}));
  if(p==='/journey/first-result')return route.fulfill(json({}));
  if(p==='/career/weekly-brief')return route.fulfill(json({}));
  return route.fulfill(json({detail:'Mock endpoint not implemented: '+p},404));
 });
 const navigate=async label=>{await page.locator('[data-tab="'+label+'"]').click();await page.waitForTimeout(250)};
 const login=async email=>{await page.locator('#email').fill(email);await page.locator('#password').fill('senha-de-teste-123');await page.locator('#authForm button[type="submit"]').click();await page.locator('#workspace').waitFor({state:'visible'})};
 await page.goto(base,{waitUntil:'domcontentloaded'});
 await login('a@teste.local');
 await navigate('diagnostic');
 const tabs=page.locator('[role="tablist"][aria-label="Seções do diagnóstico"] [role="tab"]');
 await tabs.first().waitFor();
 assert.equal(await tabs.count(),4);
 console.log('PASS 1 — quatro abas do diagnóstico');
 await tabs.nth(2).click();
 const resume=page.locator('#diag-panel-resume');
 const sel=resume.locator('select');
 await sel.locator('option[value="1"]').waitFor({state:'attached'});
 await sel.selectOption('1');
 await resume.getByRole('button',{name:'Gerar rascunho rastreável'}).click();
 await resume.getByText('RASCUNHO PRIVADO A').waitFor();
 assert.match(await resume.innerText(),/RASCUNHO PRIVADO A/);
 console.log('PASS 2 — seleciona vaga e gera currículo fundamentado');
 await tabs.nth(0).click();await tabs.nth(2).click();
 assert.equal(await sel.inputValue(),'1');
 assert.match(await resume.innerText(),/RASCUNHO PRIVADO A/);
 console.log('PASS 3 — rascunho e seleção preservados ao trocar de aba');
 await tabs.nth(3).click();
 await page.getByRole('button',{name:'Adicionar ao meu plano'}).click();
 await page.getByText('Atualizar portfólio',{exact:true}).first().waitFor();
 assert.equal(posts,1);
 console.log('PASS 4 — ação adicionada e exibida no plano semanal');
 await navigate('diagnostic');
 await page.setViewportSize({width:375,height:812});
 await page.locator('#diag-tab-resume').click();
 await page.screenshot({path:'b52-q1-mobile-375.png',fullPage:true});
 const sizes=await page.evaluate(()=>({body:document.documentElement.scrollWidth,screen:window.innerWidth}));
 assert.ok(sizes.body<=sizes.screen+1,'Horizontal overflow on mobile: '+JSON.stringify(sizes));
 assert.equal(await page.locator('#diag-tab-resume').getAttribute('aria-selected'),'true');
 console.log('PASS 5 — diagnóstico autenticado em 375px sem overflow horizontal; captura b52-q1-mobile-375.png');
 await page.setViewportSize({width:1440,height:900});
 await page.locator('#logout').click();
 await page.locator('#auth').waitFor({state:'visible'});
 await login('b@teste.local');
 await navigate('diagnostic');
 await page.locator('#diag-tab-resume').click();
 assert.doesNotMatch(await page.locator('#diag-panel-resume').innerText(),/RASCUNHO PRIVADO A/);
 assert.equal(await page.locator('#diag-panel-resume select').inputValue(),'');
 assert.ok(logouts>=1);
 console.log('PASS 6 — rascunho A não aparece na conta B');
 assert.deepEqual(issues,[],'Browser JS errors: '+issues.join('; '));
 console.log('PASS 7 — sem exceções JavaScript não tratadas');
 await browser.close();
 console.log('RESULTADO: 7/7 | STATUS: PASS (browser + API simulada)');
}
main().catch(err=>{console.error('FAIL Q1 BROWSER:',err);process.exitCode=1});
