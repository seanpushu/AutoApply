export function jobIdentity(value){
 try{const u=new URL(value);if(u.protocol!=='https:'||u.username||u.password)return null;const p=u.pathname.split('/').filter(Boolean);
 if(['jobs.ashbyhq.com','jobs.lever.co'].includes(u.hostname)&&p.length>=2)return `${u.hostname==='jobs.lever.co'?'lever':'ashby'}:${p[0].toLowerCase()}:${p[1]}`;
 if(['boards.greenhouse.io','job-boards.greenhouse.io'].includes(u.hostname)){
  if(p[0]==='embed'&&u.searchParams.get('for')&&/^\d+$/.test(u.searchParams.get('token')||''))return `greenhouse:${u.searchParams.get('for').toLowerCase()}:${u.searchParams.get('token')}`;
  if(p[1]==='jobs'&&/^\d+$/.test(p[2]||''))return `greenhouse:${p[0].toLowerCase()}:${p[2]}`;
 }
 }catch{}return null;
}
export function platformFor(url){const key=jobIdentity(url);return key?{ashby:'Ashby',lever:'Lever',greenhouse:'Greenhouse'}[key.split(':')[0]]:null;}
export const questionKey=s=>String(s||'').replace(/[*:]/g,'').trim().replace(/\s+/g,' ').toLowerCase();
export const isSensitiveQuestion=s=>/sponsor|authoriz|visa|citizen|immigra|\bcpt\b|\bopt\b|work permit|legally|eligible to work|background check|criminal|convict|disabilit|veteran|gender|sex(?:ual)?|ethnic|race\b|religio|birth|age\b|consent|agree|certif|attest|signature|salary|compensation|accommodation|why\b|motivation|interest.{0,50}(company|role|position|opportunity|working|joining)/i.test(s);
export function validateKit(kit){
 if(kit?.kind!=='summer27-application-kit'||kit.schemaVersion!==1||!Array.isArray(kit.jobs)||!kit.jobs.length||kit.jobs.length>20)throw Error('Unsupported application kit.');
 if(!kit.profile||typeof kit.profile!=='object'||Object.values(kit.profile).some(v=>typeof v!=='string'||v.length>500))throw Error('Invalid contact details.');
 if(!kit.jobs.every(j=>j&&j.jobKey===jobIdentity(j.url)&&j.jobKey&&typeof j.company==='string'&&typeof j.title==='string'))throw Error('Unsupported job identity.');
 if(new Set(kit.jobs.map(j=>j.jobKey)).size!==kit.jobs.length)throw Error('Duplicate applications in kit.');
 const r=kit.resume;if(!r||!/^.{1,150}\.(pdf|docx)$/i.test(r.name)||!['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(r.type)||!Number.isInteger(r.size)||r.size<1||r.size>3*1024*1024||!/^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(r.base64)||r.base64.length>4200000||!/^[a-f0-9]{64}$/.test(r.sha256))throw Error('Choose a PDF or DOCX resume up to 3 MB.');
 if(!Array.isArray(kit.answers)||kit.answers.length>30||kit.answers.some(a=>typeof a.question!=='string'||a.question.length>500||typeof a.answer!=='string'||a.answer.length>5000||isSensitiveQuestion(a.question)))throw Error('Exact-question answers must exclude eligibility, consent and personal-sensitive questions.');
 return kit;
}
export function makeApplicationKit({profile,jobs,resume,answers=[],factsReviewed=false}){
 if(!factsReviewed)throw Error('Review the selected resume facts and application details first.');
 if(jobs.some(j=>j.match?.eligibility==='blocked'))throw Error('Resolve the recorded qualification conflict before exporting.');
 if(jobs.some(j=>['Applied','OA received','OA completed','Interview','Offer'].includes(j.status)))throw Error('This queue contains a previously submitted application.');
 return validateKit({kind:'summer27-application-kit',schemaVersion:1,createdAt:new Date().toISOString(),profile:Object.fromEntries(['firstName','lastName','name','email','phone','linkedin','github','website'].map(k=>[k,String(profile[k]||'').trim()])),resume,answers:answers.filter(a=>a.question?.trim()&&a.answer?.trim()&&!isSensitiveQuestion(a.question)).map(a=>({question:a.question.trim(),answer:a.answer.trim()})),jobs:jobs.map(j=>({id:j.id,company:j.company,title:j.title,url:j.url,jobKey:jobIdentity(j.url),materialLabel:j.materialLabel||resume.name}))});
}
export function approvalFor(snapshot,now=Date.now()){
 if(!snapshot?.jobKey||!snapshot.hash||snapshot.blockers?.length||!snapshot.submitReady)throw Error('Complete the form and resolve its blockers before confirming submission.');
 return {jobKey:snapshot.jobKey,hash:snapshot.hash,expiresAt:now+120000};
}
export function assertApproval(snapshot,approval,now=Date.now()){
 if(!approval||approval.jobKey!==snapshot?.jobKey||approval.hash!==snapshot.hash||now>approval.expiresAt||snapshot.blockers?.length||!snapshot.submitReady)throw Error('The form changed or confirmation expired. Review it again.');
 return true;
}
