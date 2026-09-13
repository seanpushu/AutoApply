// This function is serialized by chrome.scripting; it must have no outside closures.
export async function pageBridge(action,payload){
 const identity=value=>{try{const u=new URL(value),p=u.pathname.split('/').filter(Boolean);if(u.protocol!=='https:'||u.username||u.password)return null;if(['jobs.ashbyhq.com','jobs.lever.co'].includes(u.hostname)&&p.length>=2)return `${u.hostname==='jobs.lever.co'?'lever':'ashby'}:${p[0].toLowerCase()}:${p[1]}`;if(['boards.greenhouse.io','job-boards.greenhouse.io'].includes(u.hostname)){if(p[0]==='embed'&&u.searchParams.get('for')&&/^\d+$/.test(u.searchParams.get('token')||''))return `greenhouse:${u.searchParams.get('for').toLowerCase()}:${u.searchParams.get('token')}`;if(p[1]==='jobs'&&/^\d+$/.test(p[2]||''))return `greenhouse:${p[0].toLowerCase()}:${p[2]}`;}}catch{}return null;};
 const jobKey=identity(location.href);if(!jobKey||jobKey!==payload.job?.jobKey||jobKey!==identity(payload.job.url))throw Error('Current page does not match the selected job identity.');
 const clean=s=>String(s||'').replace(/[*:]/g,'').trim().replace(/\s+/g,' '),key=s=>clean(s).toLowerCase();
 const sensitive=s=>/sponsor|authoriz|visa|citizen|immigra|\bcpt\b|\bopt\b|work permit|legally|eligible to work|background check|criminal|convict|disabilit|veteran|gender|sex(?:ual)?|ethnic|race\b|religio|birth|age\b|consent|agree|certif|attest|signature|salary|compensation|accommodation|why\b|motivation|interest.{0,50}(company|role|position|opportunity|working|joining)/i.test(s);
 const visible=el=>{for(let p=el;p&&p!==document;p=p.parentElement){if(p.hidden||p.getAttribute('aria-hidden')==='true')return false;const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden')return false;}return true;};
 const forms=[...document.forms].filter(f=>visible(f)&&f.querySelector('input[type="email"],input[type="file"],input[name="email"]'));
 if(forms.length!==1)throw Error('Open the full application page: one unambiguous application form is required. Embedded/custom forms need manual handling.');
 const form=forms[0],label=el=>clean([...el.labels||[]].map(l=>l.innerText||l.textContent).join(' ')||el.getAttribute('aria-label')||(el.getAttribute('aria-labelledby')||'').split(' ').map(id=>document.getElementById(id)?.textContent||'').join(' ').trim()||el.closest('.application-question,.field')?.querySelector('label')?.textContent||el.placeholder||el.name||el.id);
 const controls=()=>[...form.querySelectorAll('input,select,textarea,[role="combobox"]')].filter(el=>!['hidden','submit','button','reset','image'].includes(el.type)&&(el.type==='file'||visible(el)));
 const hash=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',typeof value==='string'?new TextEncoder().encode(value):value))].map(v=>v.toString(16).padStart(2,'0')).join('');
 const buttons=()=>[...form.querySelectorAll('button,input[type="submit"]')].filter(b=>b.type==='submit'&&visible(b)&&!b.disabled&&/^(submit|submit application|submit my application|apply|apply now|send application)$/i.test(clean(b.innerText||b.textContent||b.value)));
 const instant=()=>JSON.stringify([location.href,form.action,form.method,document.querySelector('h1')?.textContent,...controls().map(e=>[label(e),e.type,e.value,e.checked,e.required,e.disabled,e.textContent,[...e.files||[]].map(f=>[f.name,f.size,f.lastModified])]),...buttons().map(b=>b.textContent||b.value)]);
 async function inspect(){
  const before=instant(),fields=[],blockers=[],files=[],resumeFiles=[];let resumeInputs=0;
  for(const [i,el] of controls().entries()){
   const l=label(el)||`Unlabelled field ${i+1}`,type=el.type||el.getAttribute('role'),required=el.required||el.getAttribute('aria-required')==='true';let value;
   if(type==='file'){const resumeInput=/resume|\bcv\b/i.test(l+' '+el.name+' '+el.id)&&!/cover|letter/i.test(l);if(resumeInput)resumeInputs++;value=[];for(const f of el.files||[]){const file={name:f.name,size:f.size,type:f.type,sha256:await hash(await f.arrayBuffer())};files.push(file);value.push(file);if(resumeInput)resumeFiles.push(file);}}
   else if(type==='password'){value='[not displayed]';blockers.push('Password fields require manual handling.');}
   else if(['checkbox','radio'].includes(type))value=el.checked?String(el.value||'checked'):'[not selected]';
   else if(el.tagName==='SELECT')value=[...el.selectedOptions].map(o=>({value:o.value,label:o.textContent}));
   else value=el.value??el.textContent??'';
   fields.push({index:i,label:l,type,required,disabled:el.disabled||false,value});
   const empty=type==='file'?!value.length:['checkbox','radio'].includes(type)?!el.checked:!String(el.value??el.textContent??'').trim();
   if(!el.disabled&&required&&empty&&!(type==='radio'&&[...form.querySelectorAll('input[type=radio]')].some(r=>r.name===el.name&&r.checked)))blockers.push(`Required: ${l}`);
   if(!el.disabled&&el.willValidate&&el.validity&&!el.validity.valid&&!blockers.includes(`Required: ${l}`))blockers.push(`Check value: ${l}`);
  }
  const b=buttons();if(b.length!==1)blockers.push('A unique enabled submit button was not recognized.');
  if(form.querySelector('[aria-busy="true"],button[disabled][type="submit"]'))blockers.push('Wait for the employer page to finish processing.');
  if(payload.expectedResume&&(resumeInputs!==1||resumeFiles.length!==1||!resumeFiles.some(f=>f.sha256===payload.expectedResume.sha256&&f.name===payload.expectedResume.name)))blockers.push('The selected resume attachment could not be verified in the resume field. Attach it on the original page and review again; use manual submit if the site hides its file state.');
  const state={jobKey,url:location.href,title:document.querySelector('h1')?.textContent||document.title,action:form.action,method:form.method,fields,submitLabel:b.length===1?clean(b[0].innerText||b[0].textContent||b[0].value):'',files};
  const digest=await hash(JSON.stringify(state));if(before!==instant())throw Error('The form changed while being read. Review it again.');
  return {...state,hash:digest,blockers:[...new Set(blockers)],submitReady:!blockers.length,reviewedAt:new Date().toISOString()};
 }
 if(action==='inspect')return inspect();
 if(action==='prepare'){
  const filled=[],skipped=[],kit=payload.kit||{},profile=kit.profile||{};
  const map={'first name':'firstName',first_name:'firstName','last name':'lastName',last_name:'lastName','full name':'name',name:'name',email:'email','email address':'email',phone:'phone','phone number':'phone',linkedin:'linkedin','linkedin profile':'linkedin','linkedin url':'linkedin',github:'github','github url':'github','github profile':'github',website:'website','personal website':'website','portfolio url':'website'};
  for(const el of controls()){
   if(el.disabled||el.readOnly||el.value||!['text','email','url','tel','textarea'].includes(el.type))continue;
   const l=label(el),k=key(l);if(!l||sensitive(l)){skipped.push(l||'Unlabelled question');continue;}
   const answer=profile[map[k]]||(kit.answers||[]).find(a=>!sensitive(a.question)&&key(a.question)===k)?.answer;
   if(!answer)continue;
   const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,String(answer));el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));filled.push(l);
  }
  if(kit.resume){
   const r=kit.resume,bytes=Uint8Array.from(atob(r.base64),c=>c.charCodeAt(0));if(bytes.length!==r.size||await hash(bytes)!==r.sha256)throw Error('Resume integrity check failed. Export the kit again.');
   const inputs=controls().filter(el=>el.type==='file'&&!el.disabled&&/resume|\bcv\b/i.test(label(el)+' '+el.name+' '+el.id)&&!/cover|letter/i.test(label(el)));
   if(inputs.length!==1)skipped.push('Resume: use the original upload control; a unique resume input was not recognized.');
   else if(inputs[0].files?.length)skipped.push('Resume: retained the file already selected on the employer page.');
   else{const el=inputs[0],ext=r.name.toLowerCase().endsWith('.pdf')?'.pdf':'.docx',accept=el.accept?.toLowerCase()||'';
    if(accept&&!accept.includes(ext)&&!accept.includes(r.type.toLowerCase())&&!accept.includes('*'))skipped.push('Resume: this form requests a different file type.');
    else{const transfer=new DataTransfer();transfer.items.add(new File([bytes],r.name,{type:r.type}));el.files=transfer.files;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));filled.push('Resume file selected — the employer may upload it immediately.');}
   }
  }
  return {filled,skipped,submitted:false};
 }
 if(action==='submit'){
  globalThis.__summer27Attempts||={};if(globalThis.__summer27Attempts[jobKey])throw Error('A submission was already attempted on this page. Check its receipt; no automatic retry.');
  const before=instant(),refs=controls().flatMap(e=>[...e.files||[]]);const s=await inspect(),a=payload.approval;
  if(!a||a.jobKey!==jobKey||a.hash!==s.hash||Date.now()>a.expiresAt||s.blockers.length||!s.submitReady)throw Error('The form changed, is incomplete, or confirmation expired. Review it again.');
  if(!form.checkValidity())throw Error('The employer form has incomplete or invalid answers.');
  const b=buttons();if(b.length!==1)throw Error('The submit control changed. Review again.');
  const afterRefs=controls().flatMap(e=>[...e.files||[]]);if(before!==instant()||refs.length!==afterRefs.length||refs.some((f,i)=>f!==afterRefs[i]))throw Error('The form or attachment changed. Review again.');
  if(globalThis.__summer27Attempts[jobKey])throw Error('A submission was already attempted.');
  globalThis.__summer27Attempts[jobKey]=true;b[0].click();return {attempted:true,confirmed:false,at:new Date().toISOString(),url:location.href};
 }
 throw Error('Unknown application action.');
}
