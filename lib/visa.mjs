// Job-specific evidence, separate from the student's own eligibility declaration.
export function visaSignals(job){
 const raw=[job.jd||'',job.authorization||'',job.sponsorshipEvidence||'',job.cptEvidence||''].join('\n').replace(/[‐‑–—]/g,'-').replace(/U\.S\./gi,'US');
 const sentences=raw.split(/\n|(?<=[.!?])\s/).map(s=>s.trim()).filter(Boolean);
 const asserted=sentences.filter(s=>!s.endsWith('?')&&!/do not infer|not (?:explicitly )?(?:stated|specified|confirmed|verified)|\bunconfirmed\b|\bunknown\b/i.test(s));
 const find=re=>asserted.find(s=>re.test(s))||'';
 const signal=(status,evidence='',scope='job')=>({status,evidence:evidence.slice(0,700),scope});
 let cpt=signal('unknown'),future=signal('unknown'),current=signal('unknown');
 const f1Block=find(/(?:not eligible|ineligible|not accept|cannot accept|not consider|unable to accept|not available).{0,85}(?:f-?1|j-?1|\bcpt\b|\bopt\b)|(?:f-?1|j-?1|\bcpt\b|\bopt\b).{0,60}(?:not eligible|ineligible|not accepted|not supported)/i);
 const cptYes=find(/(?:\bcpt\b|curricular practical training).{0,65}(?:eligible|welcome|accepted|may apply|can apply|considered)|(?:accept|welcome|eligible|consider).{0,65}(?:\bcpt\b|curricular practical training)/i);
 if(f1Block)cpt=signal('excluded',f1Block);else if(cptYes)cpt=signal('accepted',cptYes);
 const restrictive=s=>/(?:without|not |no |unable|cannot|ineligible|must.{0,12}not|will not|does not|do not)/i.test(s)&&/sponsor/i.test(s);
 const scoped=s=>/(?:for|during|this|these).{0,25}(?:internships?|positions?|roles?|programs?)|at this time/i.test(s);
 const futureNo=asserted.find(s=>restrictive(s)&&(/(?:now.{0,30}(?:future|later)|future.{0,35}sponsor|sponsor.{0,65}(?:future|after graduation))/i.test(s)||!scoped(s)&&/(?:company|\bwe\b).{0,45}(?:not|never|no).{0,20}sponsor/i.test(s)))||'';
 const currentNo=asserted.find(s=>restrictive(s)&&scoped(s))||'';
 const broadNo=asserted.find(s=>restrictive(s))||'';
 const yes=find(/(?:we|company).{0,30}(?:sponsor|provide.{0,20}sponsorship)|(?:visa|immigration|h-?1b).{0,25}sponsorship.{0,25}(?:available|provided|offered)|(?:offer|provide).{0,20}(?:visa|immigration).{0,15}sponsorship/i);
 if(futureNo)future=signal('unavailable',futureNo);
 else if(yes&&!restrictive(yes))future=signal('available',yes);
 else if(job.communitySponsorship==='Offers Sponsorship')future=signal('community-signal','Community source marks sponsorship available; employer and specific role have not confirmed it.','community');
 if(currentNo)current=signal('not-provided',currentNo);
 else if(broadNo&&!futureNo)current=signal('restriction-unclear',broadNo);
 const usPerson=find(/must.{0,25}(?:be|qualify as).{0,15}(?:a )?u\.?s\.? person|u\.?s\.? person.{0,20}(?:required|only)/i);
 return {cpt,future,current,usPerson:signal(usPerson?'required':'unknown',usPerson)};
}
