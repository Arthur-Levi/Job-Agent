'use strict';
// Q1 B5.2: zero-dependency contract tests for navigation and diagnostic tab behavior.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8');
function check(condition,message){assert.ok(condition,message);console.log('PASS | '+message)}
check(source.includes("function createDiagnosticViews(root)"),'Explicit diagnostic view builder exists');
check(!source.includes('function organizeDiagnosticTabs()'),'Fragile heading-based organizer removed');
check(source.includes("add(requirements,'h3','Prioridades e lacunas')"),'Requirements assigned explicitly');
check(source.includes("add(act,'h3','As 3 próximas ações')"),'Actions assigned explicitly');
check(source.includes('const billingPromise=api('),'Billing is parallel to content');
check(source.includes("navQueue=navQueue.catch(()=>{}).then(render)"),'Async navigation DOM writers serialized');
check(source.includes('navigationController.abort()'),'Obsolete navigation requests cancelled');
check(source.includes("signal:method==='GET'?navigationSignal():undefined"),'GET requests use abort signal');
check(source.includes("api('/jobs').then(jobs=>"),'Job choices load independently');
check(source.includes("diagnosticDraft.text=result.text+"),'Grounded draft state retained');
const start=source.indexOf('function createDiagnosticViews(root){');
const end=source.indexOf('\nconst EVIDENCE_KINDS=',start);
assert.ok(start>=0&&end>start);
const body=source.slice(start,end);
class Node {
 constructor(tag,text,cls){this.tag=tag;this.textContent=text||'';this.className=cls||'';this.children=[];this.attrs={};this.events={};this.hidden=false}
 append(child){this.children.push(child);return child}
 setAttribute(k,v){this.attrs[k]=v}
 addEventListener(k,fn){this.events[k]=fn}
 focus(){this.focused=true}
}
const context={add:(parent,tag,text,cls)=>parent.append(new Node(tag,text,cls)),diagnosticView:'overview'};
vm.createContext(context);
vm.runInContext(body,context);
const root=new Node('div');
const result=context.createDiagnosticViews(root);
check(Object.keys(result.sections).join(',')==='overview,requirements,resume,actions','Exactly four stable panel IDs');
const bar=root.children[0];
assert.equal(bar.attrs.role,'tablist');
const buttons=bar.children;
check(buttons[0].attrs['aria-selected']==='true'&&result.sections.requirements.hidden,'One active tab by default');
buttons[1].events.click();
check(buttons[1].attrs['aria-selected']==='true'&&!result.sections.requirements.hidden&&result.sections.overview.hidden,'Tab activation hides other panels');
const event={key:'End',preventDefault(){this.prevented=true}};
buttons[1].events.keydown(event);
check(event.prevented&&buttons[3].attrs['aria-selected']==='true'&&buttons[3].focused,'Keyboard End moves selection and focus');
result.sections.requirements.append(new Node('h3','Qualquer novo título'));
result.activate('requirements');
check(result.sections.requirements.children[0].textContent==='Qualquer novo título','Headings can change without affecting panel ownership');
console.log('RESULTADO: 15/15');
console.log('STATUS: PASS');
