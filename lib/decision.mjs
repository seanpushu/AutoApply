// Prioritization is separate from skill coverage and never grants permission to apply.
export function judgeJob(job,today=new Date().toISOString().slice(0,10)){
 const m=job.match||{},checks=m.checks||[],conflicts=checks.filter(c=>c.status==='blocked').map(c=>c.message);
 const intern=/\bintern(?:ship)?\b|\bco[ -]?op\b/i.test(job.title||'')||/^internship|^intern$/i.test(job.employmentType||'');
 const permanent=!intern&&(/full[ -]?time|permanent/i.test(job.employmentType||'')||/new grad|graduate engineer|senior|staff engineer/i.test(job.title||''));
 if(permanent)conflicts.unshift('这是正式岗位，不在当前实习范围。');
 if(conflicts.length)return {key:'conflict',label:'暂不适合',tone:'danger',reasons:conflicts,action:'查看冲突',rank:3};
 const gaps=[];
 if(!intern)gaps.push('尚未确认这是实习岗位。');
 if(!['US','USA','United States'].includes(job.country))gaps.push('美国工作地点尚未确认。');
 if(job.year!==2027||job.season!=='Summer')gaps.push('2027 暑期批次尚未确认。');
 const full=!!job.jd&&['live-api','live-page','official-page','live','verified'].includes(job.sourceState)&&!/summary|not.*full/i.test(job.jdTextKind||'');
 if(!full)gaps.push('缺少完整雇主 JD，先核对原文。');
 const age=Math.floor((Date.parse(today)-Date.parse(String(job.checkedAt||'').slice(0,10)))/86400000);
 if(!Number.isFinite(age)||age>14)gaps.push('来源超过 14 天未核查或缺少核查日期。');
 if(gaps.length)return {key:'verify',label:'先核实',tone:'warning',reasons:gaps,action:'补全证据',rank:1};
 if(m.score===null||m.score===undefined||(m.required?.length||0)+(m.preferred?.length||0)<3)return {key:'verify',label:'先核实',tone:'warning',reasons:['可评分的技能要求太少，不能仅凭高分排序。'],action:'核对要求',rank:1};
 if(m.score<60)return {key:'prepare',label:'先补证据',tone:'neutral',reasons:[`技能证据覆盖 ${m.score}%，先检查关键差距。`,...(m.missingRequired||[]).slice(0,3)],action:'查看差距',rank:2};
 return {key:'priority',label:'优先查看',tone:'positive',reasons:['实习批次、美国地点和完整 JD 已记录，未发现明确资格冲突。','仍需逐岗确认学位、CPT、未来赞助与当前开放状态。'],action:'审阅后入队',rank:0};
}
