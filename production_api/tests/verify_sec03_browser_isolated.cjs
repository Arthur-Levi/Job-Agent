'use strict';
/* SEC-03 browser security regression. Static assets on a disposable localhost HTTP server.
   All /api requests are intercepted: NO real API, database or accounts.
   The test intentionally FAILS if sensitive draft survives account switching. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const {createRequire}=require('node:module');
let chromium;
try{({chromium}=require('playwright'))}
catch{({chromium}=createRequire(path.join(process.env.JOB_AGENT_PLAYWRIGHT_ROOT||'/workspaces/Job-Agent','package.json'))('playwright'))}
const root=path.resolve(__dirname,'../web');
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8'};
const server=http.createServer((req,res)=>{
 let name=req.url.split('?')[0];if(name==='/')name='/index.html';
 if(name.startsWith('/assets/'))name=name.slice('/assets'.length);
 const file=path.resolve(root,'.'+name);
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end('Not found')}
 res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
 fs.createReadStream(file).pipe(res);
});
let browser;
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:375,height:812}});
 let current='',expired=false;
 const json=(o,status=200)=>({status,contentType:'application/json',body:JSON.stringify(o)});
 await page.route('**/api/**',async route=>{
  const p=new URL(route.request().url()).pathname.slice(4);
  if(p==='/auth/login'){current=route.request().postDataJSON().email;expired=false;return route.fulfill(json({access_token:'fake-'+current,token_type:'bearer'}))}
  if(p==='/auth/logout')return route.fulfill(json({ok:true}));
  if(expired)return route.fulfill(json({detail:'Sessão inválida'},401));
  if(p==='/billing/status')return route.fulfill(json({premium_enabled:false,status:'inactive'}));
  if(p==='/dashboard')return route.fulfill(json({}));
  if(p==='/progress')return route.fulfill(json({applications_by_status:{},tasks_done:0,tasks_total:0}));
  if(p==='/onboarding')return route.fulfill(json({total:0,completed:0,steps:[]}));
  if(p==='/journey/first-result'||p==='/career/weekly-brief')return route.fulfill(json({}));
  if(p==='/jobs')return route.fulfill(json([]));
  return route.fulfill(json({detail:'No mock route: '+p},404));
 });
 const url='http://127.0.0.1:'+server.address().port;
 await page.goto(url);
 const login=async(email)=>{
  await page.locator('#email').fill(email);
  await page.locator('#password').fill('senha-teste-1234567');
  await page.locator('#authForm button[type="submit"]').click();
  await page.locator('[data-tab="jobs"]').click();
  await page.locator('#content textarea').first().waitFor();
 };
 await login('conta-a@example.invalid');
 const secret='TEXTO-PRIVADO-DA-CONTA-A-SEC03';
 await page.locator('#content textarea').first().fill(secret);
 assert.equal(await page.evaluate(()=>sessionStorage.getItem('jobagent_job_draft')),secret);
 console.log('PASS 1 — conta A criou rascunho local');
 await page.locator('#logout').click();
 await page.locator('#auth:not([hidden])').waitFor();
 await login('conta-b@example.invalid');
 const leaked=await page.locator('#content textarea').first().inputValue();
 assert.ok(!leaked.includes(secret),'FAIL PRIVACIDADE: conta B recebeu o rascunho de vaga da conta A');
 console.log('PASS 2 — troca de contas não vazou rascunho de vaga');
 expired=true;
 await page.locator('[data-tab="tasks"]').click();
 await page.locator('#auth:not([hidden])').waitFor();
 assert.equal(await page.evaluate(()=>sessionStorage.getItem('jobagent_token')),null);
 console.log('PASS 3 — 401 de sessão inválida remove token e retorna ao login');
 console.log('RESULTADO: 3/3 PASS (navegador + API simulada; sem banco)');
})().catch(e=>{console.error('FAIL SEC-03:',e.message);process.exitCode=1}).finally(async()=>{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve))});
