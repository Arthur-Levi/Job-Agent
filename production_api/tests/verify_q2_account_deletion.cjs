'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const js=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'..','web','style.css'),'utf8');
const account=js.slice(js.indexOf('async function account(){'),js.indexOf("$('authForm').onsubmit"));
const cases=[
 ['Native confirmation removed',!account.includes("prompt(")&&!account.includes("confirm(")],
 ['Disclosure is accessible native details',account.includes("'details',undefined,'account-delete-disclosure'")],
 ['Password remains required',account.includes("formField(deleteForm,'Confirme sua senha','password','','password',true)")],
 ['Explicit acknowledgment required',account.includes("confirmBox.required=true")],
 ['Form validation precedes deletion',account.includes('if(!deleteForm.reportValidity())return')],
 ['Backend endpoint retained',account.includes("api('/account/delete','POST',{password:passwordField.value})")],
 ['Sensitive state cleared',account.includes('clearDiagnosticPrivateState()')],
 ['Risk-specific style exists',css.includes('.account-delete-disclosure')&&css.includes('.danger-action')],
 ['Mobile action sized',css.includes('.account-delete-form .danger-action{width:100%}')]
];
for(const [label,ok] of cases){assert.ok(ok,label);console.log('PASS | '+label)}
console.log('RESULTADO: '+cases.length+'/'+cases.length+' | STATUS: PASS');
