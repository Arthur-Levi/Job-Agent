'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
const begin=src.indexOf('function actionSuccessMessage(label){');
const end=src.indexOf('function action(label,fn,secondary=false){',begin);
assert.ok(begin>=0&&end>begin,'Success feedback helper must exist');
const context=vm.createContext({});
vm.runInContext(src.slice(begin,end),context);
const cases=[
 ['Draft confirmation specific',context.actionSuccessMessage('Gerar rascunho rastreável').includes('Rascunho')],
 ['Evidence confirmation specific',context.actionSuccessMessage('Adicionar evidência').includes('Evidência')],
 ['Task confirmation specific',context.actionSuccessMessage('Adicionar tarefa').includes('Tarefa')],
 ['Unknown action fallback',context.actionSuccessMessage('Comando não mapeado')==='Ação concluída.'],
 ['No premature success on cancelled validation',src.includes('outcome!==false')],
 ['Deletion invalid form returns false',src.includes('if(!deleteForm.reportValidity())return false;')],
 ['No change to API path',src.includes("api('/account/delete','POST',{password:passwordField.value})")],
 ['Live region retained',src.includes("feedback.setAttribute('aria-live','polite')")],
 ['Error styling toggled',src.includes("feedback.classList.add('action-feedback-error')")],
 ['Success styling reset',src.includes("feedback.classList.remove('action-feedback-error')")],
 ['Error style present',css.includes('.action-feedback-error{')]
];
for(const [name,ok] of cases){assert.ok(ok,name);console.log('PASS | '+name)}
console.log('RESULTADO: '+cases.length+'/'+cases.length+' | STATUS: PASS (contrato + helper)');
