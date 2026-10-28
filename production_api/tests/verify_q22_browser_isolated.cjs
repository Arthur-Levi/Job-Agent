'use strict';
/* Browser-only Q2.2 acceptance. Static UI on localhost + intercepted fake API.
   No PostgreSQL, Uvicorn, migrations, or real accounts. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const {createRequire}=require('node:module');
let chromium;
try{({chromium}=require('playwright'))}
catch{({chromium}=createRequire(path.join(process.env.JOB_AGENT_PLAYWRIGHT_ROOT||'/workspaces/Job-Agent','package.json'))('playwright'))}
const root=path.resolve(__dirname,'../web');
const types={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
const server=http.createServer((req,res)=>{
 let name=req.url.split('?')[0];
 if(name==='/')name='/index.html';
 if(name.startsWith('/assets/'))name=name.slice('/assets'.length);
 const file=path.resolve(root,'.'+name);
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end('Not found');return}
 res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
 fs.createReadStream(file).pipe(res);
});
const json=(obj,status=200)=>({status,contentType:'application/json',body:JSON.stringify(obj)});
let browser;
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 const uncaught=[];page.on('pageerror',e=>uncaught.push(e.message));
 let previewCalls=0, taskGETFailures=0, taskPosts=0, tasks=[], releaseThirdPreview=null;
 await page.route('**/api/**',async route=>{
  const req=route.request(),p=new URL(req.url()).pathname.slice(4),method=req.method();
  if(p==='/auth/login')return route.fulfill(json({access_token:'fake-q22-token',token_type:'bearer'}));
  if(p==='/billing/status')return route.fulfill(json({premium_enabled:false,status:'inactive'}));
  if(p==='/dashboard')return route.fulfill(json({}));
  if(p==='/progress')return route.fulfill(json({applications_by_status:{},tasks_done:0,tasks_total:0}));
  if(p==='/onboarding')return route.fulfill(json({total:0,completed:0,steps:[]}));
  if(p==='/journey/first-result'||p==='/career/weekly-brief')return route.fulfill(json({}));
  if(p==='/jobs'&&method==='GET')return route.fulfill(json([]));
  if(p==='/jobs/text-preview'&&method==='POST'){
   previewCalls++;
   await new Promise(r=>setTimeout(r,180));
   if(previewCalls===1)return route.fulfill(json({detail:'Prévia temporariamente indisponível'},503));
   if(previewCalls===3)await new Promise(resolve=>{releaseThirdPreview=resolve});
   return route.fulfill(json({title_draft:'Analista de dados',company_draft:'Empresa fictícia',description_draft:'Oportunidade fictícia de testes',requirements_draft:['SQL']}));
  }
  if(p==='/tasks'&&method==='GET'){
   if(taskGETFailures++===0)return route.fulfill(json({detail:'Serviço temporariamente indisponível'},503));
   return route.fulfill(json(tasks));
  }
  if(p==='/tasks'&&method==='POST'){taskPosts++;await new Promise(r=>setTimeout(r,200));tasks.push({id:taskPosts,title:req.postDataJSON().title,done:false});return route.fulfill(json(tasks[tasks.length-1],201))}
  return route.fulfill(json({detail:'Rota simulada não configurada: '+p},404));
 });
 await page.goto(url);
 await page.locator('#email').fill('test@local.invalid');
 await page.locator('#password').fill('senha-ficticia-1234');
 await page.locator('#authForm button[type="submit"]').click();
 await page.locator('[data-tab="jobs"]').click();
 const raw=page.locator('#content textarea').first();
 await raw.fill('Cargo: Analista de Dados. Empresa: Fictícia. Requisitos: Excel, SQL e Power BI.');
 const preview=page.getByRole('button',{name:'Analisar vaga sem salvar'});
 await preview.click();
 await page.getByText('Prévia temporariamente indisponível').waitFor();
 assert.match(await raw.inputValue(),/Analista de Dados/);
 console.log('PASS 1 — erro de ação exibido e texto preservado');
 assert.equal(await preview.isDisabled(),false);
 await preview.click();await page.getByText('Revise a vaga antes de salvar').waitFor();
 assert.equal(previewCalls,2);
 console.log('PASS 2 — repetição após erro funciona');
 await preview.click({noWaitAfter:true});
 await page.waitForFunction(()=>document.querySelector('#content .action-feedback')!==null);
 assert.equal(previewCalls,3,'Third request should have reached the mock');
 assert.equal(await preview.isDisabled(),true,'Button must remain disabled while request is held');
 await preview.evaluate(button=>button.click()); // force second click to verify handler guard
 assert.equal(previewCalls,3,'Concurrent click must not start another request');
 releaseThirdPreview();
 await preview.waitFor({state:'visible'});
 await page.waitForFunction(()=>{const b=[...document.querySelectorAll('#content button')].find(b=>b.textContent==='Analisar vaga sem salvar');return b&&!b.disabled});
 console.log('PASS 3 — botão desabilitado durante requisição; nenhuma ação duplicada');
 await page.locator('[data-tab="tasks"]').click();
 await page.getByText('Serviço temporariamente indisponível').waitFor();
 const retry=page.getByRole('button',{name:'Tentar novamente'});
 assert.equal(await retry.count(),1);
 await retry.click();
 await page.getByText('Seu plano semanal está vazio').waitFor();
 console.log('PASS 4 — erro de carregamento oferece retry único e recupera');
 const form=page.locator('#content form').first();
 await form.locator('input[name="title"]').fill('Tarefa fictícia Q2.2');
 await form.getByRole('button',{name:'Adicionar tarefa'}).click();
 await page.getByText('Tarefa fictícia Q2.2').waitFor();
 assert.equal(taskPosts,1);
 console.log('PASS 5 — ação persistida apenas no mock e refletida na interface');
 await page.setViewportSize({width:375,height:812});
 await page.screenshot({path:'q22-feedback-mobile-375.png',fullPage:true});
 const metrics=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
 assert.ok(metrics.scroll<=metrics.viewport+1,'overflow horizontal: '+JSON.stringify(metrics));
 console.log('PASS 6 — layout mobile 375px sem overflow');
 assert.deepEqual(uncaught,[]);
 console.log('PASS 7 — sem erros JavaScript não tratados');
 console.log('RESULTADO: 7/7 | STATUS: PASS (navegador e API simulada; sem banco)');
})().catch(e=>{console.error('FAIL Q2.2 BROWSER:',e);process.exitCode=1}).finally(async()=>{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve))});
