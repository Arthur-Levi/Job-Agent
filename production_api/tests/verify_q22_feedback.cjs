'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const js=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
const testCases=[
 ['Shared state builder',js.includes('function uiState(parent,kind,title,description,buttonLabel,onClick)')],
 ['Error live role',js.includes("kind==='error'?'alert':'status'")],
 ['Safe text rendering',js.includes("add(root,'p',description)")],
 ['Loading state in navigation',js.includes("uiState($('content'),'loading','Preparando sua área'")],
 ['Error includes retry',js.includes("'Tentar novamente',()=>show(destination)")],
 ['Retry not duplicated',!js.includes("$('content').append(action('Tentar novamente'")],
 ['Empty applications with next step',js.includes("'Nenhuma candidatura registrada'")],
 ['Empty evidence guidance',js.includes("'Ainda não há evidências'")],
 ['Empty jobs guidance',js.includes("'Nenhuma vaga salva'")],
 ['Empty tasks guidance',js.includes("'Seu plano semanal está vazio'")],
 ['Responsive state styling',css.includes('@media(max-width:520px){.ui-state{padding:16px}')],
 ['Error state styling',css.includes('.ui-state-error{border-left:3px')]
];
for(const [label,pass] of testCases){assert.ok(pass,label);console.log('PASS | '+label)}
console.log('RESULTADO: '+testCases.length+'/'+testCases.length+' | STATUS: PASS (contrato estático)');
