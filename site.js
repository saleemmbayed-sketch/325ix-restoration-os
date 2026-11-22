'use strict';
const $=id=>document.getElementById(id);
let activeAssembly=null, currentJob=null, allGroups=[], restorationDomains=[], livingMission=null, lastMissionAI=null;
let uiLanguage=localStorage.getItem('325ix-ui-language')||'en';
const text=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==undefined&&value!==null)e.textContent=String(value);if(cls)e.className=cls;return e};
const link=(label,url)=>{const a=text('a',label);if(url&&(/^https:\/\//.test(url)||/^\/api\/job\/\d+\.md$/.test(url))){a.href=url;a.target='_blank';a.rel='noopener noreferrer'}return a};
async function api(path,opts={}){const next={...opts};if((opts.method||'GET').toUpperCase()!=='GET')next.headers={...(opts.headers||{}),'X-Workbench-Request':'same-origin'};const r=await fetch(path,next);const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function fail(e){alert('Workbench: '+(e.message||e))}
function tab(name){for(const b of document.querySelectorAll('.tab'))b.classList.toggle('active',b.dataset.tab===name);for(const p of document.querySelectorAll('.page'))p.hidden=p.id!==name;if(name==='garage')loadGarage();if(name==='jobs')loadJobs();if(name==='sources')loadSources();if(name==='chat')loadAIStatus();if(name==='twin'){loadTwin();loadVisualTwin()}}
for(const b of document.querySelectorAll('.tab'))b.addEventListener('click',()=>tab(b.dataset.tab));
function applyUiLanguage(){document.documentElement.dir=uiLanguage==='ar'?'rtl':'ltr';document.documentElement.lang=uiLanguage;$('uilang').textContent=uiLanguage==='ar'?'AR':'EN';$('language-toggle').setAttribute('aria-pressed',uiLanguage==='ar'?'true':'false')}
if($('language-toggle')){$('language-toggle').addEventListener('click',()=>{uiLanguage=uiLanguage==='ar'?'en':'ar';localStorage.setItem('325ix-ui-language',uiLanguage);applyUiLanguage()});applyUiLanguage()}
function syncMissionSystems(){const domain=restorationDomains.find(x=>x.id===$('missiondomain').value),select=$('missionsystem');select.replaceChildren();for(const g of domain?.groups||[]){const o=document.createElement('option');o.value=g.group_name;o.textContent=g.group_name.replaceAll('_',' ')+' · '+g.assemblies+' assemblies';select.append(o)}if(domain?.default_system)select.value=domain.default_system}
async function loadGarage(){try{const [coverage,missions]=await Promise.all([api('/api/restoration/domains'),api('/api/missions')]);restorationDomains=coverage.domains;const domainSelect=$('missiondomain'),selected=domainSelect.value;domainSelect.replaceChildren();for(const d of restorationDomains){const o=document.createElement('option');o.value=d.id;o.textContent=d.priority+' · '+d.label;domainSelect.append(o)}if(selected&&restorationDomains.some(x=>x.id===selected))domainSelect.value=selected;syncMissionSystems();const cards=$('domaincards');cards.replaceChildren();for(const d of restorationDomains){const card=text('article',null,'domaincard');card.append(text('div',d.priority+' · '+d.label,'title'),text('p',d.promise),text('div',`${d.assembly_count} assemblies · ${d.mission_count} missions`,'code'),text('div',d.groups.map(x=>x.group_name.replaceAll('_',' ')).join(' · '),'meta'));cards.append(card)}const list=$('missionlist');list.replaceChildren();if(!missions.missions.length)list.append(text('p','No restoration missions yet. Start with the highest-priority observed issue or inspection objective.','info'));for(const m of missions.missions){const row=text('div',null,'source');row.append(text('div',`IX-${String(m.job_id).padStart(4,'0')} · ${m.domain_label} · ${m.mission_status}`,'title'),text('p',m.symptom),text('div',`${m.priority} · ${m.system.replaceAll('_',' ')} · ${m.risk} · clearance ${m.clearance}`,'info'));const resume=text('button','Resume mission','light');resume.addEventListener('click',()=>resumeMission(m));row.append(resume);list.append(row)}}catch(e){$('missionlist').replaceChildren(text('p','Garage unavailable: '+e.message,'risk'))}}
async function resumeMission(m){currentJob=m.job_id;livingMission=m;tab('mission');await loadLivingMission(m)}
async function loadLivingMission(m){
 const jobId=m.job_id;const root=$('livingmissionevidence');root.replaceChildren(text('p','Loading connected mission evidence…','info'));
 try{
  lastMissionAI=null;$('missionsaveai').disabled=true;$('missionaianswer').textContent='No mission question asked yet.';$('missionaistatus').textContent='';
  const o=await api('/api/job/'+jobId+'/overview'),job=o.job;
  $('livingmissiontitle').textContent='IX-'+String(jobId).padStart(4,'0')+' · '+(m.domain_label||m.domain_id||'Restoration mission');
  $('livingmissionmeta').textContent=`${job.system.replaceAll('_',' ')} · ${job.symptom} · ${m.mission_status||job.status}`;
  $('livingmissionbadge').textContent=m.priority?m.priority+' · ACTIVE':'ACTIVE';
  $('livingmissionrisk').textContent=`${job.risk} · safety clearance ${o.readiness.clearance}. Qualified physical sign-off remains mandatory.`;
  const progress=o.mission_progress,stages=progress.stages;$('livingmissionprogress').style.width=progress.percent+'%';$('livingmissionprogresslabel').textContent=`${progress.completed_stages} of ${progress.total_stages} evidence stages recorded · next gate ${progress.current_stage.replaceAll('_',' ')}. Progress never represents roadworthiness.`;
  const stepRoot=$('livingmissionsteps');stepRoot.replaceChildren();let currentMarked=false;for(const stage of stages){const state=stage.complete?'complete':(!currentMarked?(currentMarked=true,'current'):'pending');const card=text('article',null,'missionstep '+state);card.append(text('div',(stage.complete?'✓ ':state==='current'?'→ ':'○ ')+stage.label,'title'),text('p',stage.detail,'small'),text('span',stage.complete?'EVIDENCE RECORDED':state==='current'?'NEXT GATE':'PENDING','factstatus'));stepRoot.append(card)}
  const blockers=$('livingmissionblockers');blockers.replaceChildren();const ul=text('ul');for(const b of o.readiness.blockers)ul.append(text('li',b));blockers.append(ul);
  root.replaceChildren();[['Observations & measurements',o.observations.length],['Checks recorded',o.checks.filter(x=>x.status!=='NOT_CHECKED').length+o.expert_steps.filter(x=>x.status!=='NOT_CHECKED').length],['Specialist findings',o.specialist_findings.length],['Repair options',o.options.length],['Twin events',o.twin_events.length]].forEach(([label,value])=>{const card=text('article',null,'item');card.append(text('div',value,'missionmetric'),text('div',label,'desc'));root.append(card)});
  const feed=$('livingmissionfeed');feed.replaceChildren();const entries=[...o.observations.map(x=>({at:x.created_utc,title:`Evidence · ${x.type}`,detail:x.value,meta:`${x.unit||''} · ${x.tool||'method not recorded'} · ${x.source}`})),...o.specialist_findings.map(x=>({at:x.created_utc,title:`Specialist · ${x.agent_id} · ${x.status}`,detail:x.finding,meta:'Uncertainty: '+x.uncertainty})),...o.options.map(x=>({at:x.created_utc,title:`Decision · ${x.path.replaceAll('_',' ')}`,detail:x.description,meta:`${x.fitment_status} · ${x.decision_status} · ${x.source}`}))].sort((a,b)=>String(b.at).localeCompare(String(a.at))).slice(0,8);if(!entries.length)feed.append(text('p','No mission evidence recorded yet. Use the evidence form below.','info'));for(const x of entries){const row=text('div',null,'source');row.append(text('div',x.title,'title'),text('p',x.detail),text('div',x.meta,'meta'));feed.append(row)}
  renderMissionChecks(o.checks);
  if(!$('missionaiquestion').value)$('missionaiquestion').value=`For mission IX-${String(jobId).padStart(4,'0')}: ${job.symptom}. Summarize verified evidence, uncertainties, contradictions, and the safest next discriminating test.`;
  const actions=$('livingmissionactions');actions.replaceChildren();
  const action=(label,fn,primary=false)=>{const b=text('button',label,primary?'':'light');b.type='button';b.onclick=fn;actions.append(b)};
  action('Identify parts & drawings',()=>{tab('lookup');$('group').value=job.system;$('search').value='';search()},true);
  action('Record evidence & checks',()=>{tab('jobs');$('newjob').hidden=false;$('newjobtitle').textContent='IX-'+String(jobId).padStart(4,'0')+' · Mission evidence';$('jobprompts').replaceChildren(text('p','Record only observed, measured or sourced evidence.','risk'));$('jobdownload').replaceChildren(link('Download current work order','/api/job/'+jobId+'.md'));loadCheckpoints(jobId);$('newjob').scrollIntoView({behavior:'smooth'})});
  action('Ask AI mechanic',()=>{tab('chat');$('aigroup').value=job.system;$('aiquestion').value=`For mission IX-${String(jobId).padStart(4,'0')}: ${job.symptom}. What evidence is known, what remains uncertain, and what is the safest next discriminating test?`});
  action('Find technical evidence',()=>{tab('manuals');$('manualq').value=job.system.replaceAll('_',' ');loadManualStatus()});
  action('Open digital twin',()=>tab('twin'));
  action('Export work order',()=>window.open('/api/job/'+jobId+'.md','_blank','noopener'));
 }catch(e){root.replaceChildren(text('p','Living Mission unavailable: '+e.message,'risk'))}
}
function renderMissionChecks(checks){const root=$('missionchecks');root.replaceChildren();for(const check of checks){const wrap=text('div',null,'missioncheck');wrap.append(text('div',check.label,'title'));const status=document.createElement('select');for(const value of ['NOT_CHECKED','OBSERVED','NEEDS_SPECIALIST','NOT_APPLICABLE']){const option=document.createElement('option');option.value=value;option.textContent=value.replaceAll('_',' ');option.selected=check.status===value;status.append(option)}const finding=document.createElement('textarea');finding.rows=2;finding.placeholder='Observed finding or unresolved issue';finding.value=check.finding;const source=document.createElement('input');source.placeholder='Photo ID / manual page / mechanic';source.value=check.source;const save=text('button','Save check','light');save.type='button';save.onclick=async()=>{try{await api('/api/job/checks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:currentJob,code:check.code,status:status.value,finding:finding.value,source:source.value})});await loadLivingMission(livingMission)}catch(e){fail(e)}};wrap.append(status,finding,source,save);root.append(wrap)}}
$('missionback').addEventListener('click',()=>tab('garage'));
$('missionevidenceform').addEventListener('submit',async e=>{e.preventDefault();if(!currentJob||!livingMission)return;const status=$('missionevidencestatus');try{await api('/api/job/'+currentJob+'/observation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:$('missionevidencetype').value,value:$('missionevidencevalue').value,unit:$('missionevidenceunit').value,tool:$('missionevidencetool').value,source:$('missionevidencesource').value})});status.textContent='Evidence saved · clearance remains NOT APPROVED';e.target.reset();await loadLivingMission(livingMission)}catch(err){status.textContent=err.message;status.className='risk'}});
$('missionoptionform').addEventListener('submit',async e=>{e.preventDefault();if(!currentJob||!livingMission)return;const status=$('missionoptionstatus');try{await api('/api/job/'+currentJob+'/options',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:$('missionoptionpath').value,description:$('missionoptiondescription').value,part_number:$('missionoptionpart').value,fitment_status:$('missionoptionfit').value,decision_status:$('missionoptiondecision').value,evidence:$('missionoptionevidence').value,source:$('missionoptionsource').value,cost_estimate:$('missionoptioncost').value,availability:$('missionoptionavailability').value})});status.textContent='Option saved for human review · clearance remains NOT_APPROVED';e.target.reset();await loadLivingMission(livingMission)}catch(err){status.textContent=err.message;status.className='risk'}});
$('missionaiform').addEventListener('submit',async e=>{e.preventDefault();if(!currentJob||!livingMission)return;const answer=$('missionaianswer'),status=$('missionaistatus');answer.textContent='Retrieving mission evidence and routing specialist…';$('missionsaveai').disabled=true;try{lastMissionAI=await api('/api/ai/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('missionaiquestion').value,system:livingMission.system,language:uiLanguage,job_id:currentJob})});answer.textContent=lastMissionAI.answer+'\n\nPolicy: '+lastMissionAI.policy;status.textContent=`${lastMissionAI.routing.specialist.label} · ${lastMissionAI.routing.safety_class} · review required`;$('missionsaveai').disabled=false}catch(err){answer.textContent=err.message;status.textContent='AI request failed'}});
$('missionsaveai').addEventListener('click',async()=>{if(!lastMissionAI||!currentJob||!livingMission)return;const status=$('missionaistatus'),route=lastMissionAI.routing;const evidence=[];for(const x of lastMissionAI.catalog_evidence||[])evidence.push(`Catalog ${x.part_number||'unknown'} · ${x.description||x.slug||'row'}`);for(const x of lastMissionAI.manual_excerpts||[])evidence.push(x.citation||`${x.title||'Manual'} · ${x.page_label||'page unknown'}`);for(const x of lastMissionAI.case_context?.observations||[])evidence.push(`Case ${x.type}: ${x.value}`);if(!evidence.length)evidence.push('No supporting source retrieved; stored only as an unverified hypothesis');try{await api('/api/job/'+currentJob+'/specialist-finding',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent_id:route.specialist.id||route.intent,intent:route.intent,finding:lastMissionAI.answer,evidence,uncertainty:'Model-generated synthesis; source applicability, diagnosis and safety remain unverified until human review.',tests:route.required_evidence?.length?route.required_evidence:['Qualified physical inspection'],status:'REQUIRES_HUMAN_REVIEW',source:`${lastMissionAI.model} · ${lastMissionAI.policy}`})});status.textContent='Saved as review-required specialist finding; no diagnosis or clearance granted';$('missionsaveai').disabled=true;await loadLivingMission(livingMission)}catch(err){status.textContent=err.message;status.className='risk'}});
$('missiondomain').addEventListener('change',syncMissionSystems);
$('missionform').addEventListener('submit',async e=>{e.preventDefault();try{const d=await api('/api/missions/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({domain_id:$('missiondomain').value,system:$('missionsystem').value,symptom:$('missionsymptom').value,context:$('missioncontext').value})});$('missionstatus').textContent=`Mission IX-${String(d.job_id).padStart(4,'0')} created · ${d.mission.domain_label} · safety ${d.clearance}`;$('missionsymptom').value='';$('missioncontext').value='';await loadGarage()}catch(err){$('missionstatus').textContent=err.message;$('missionstatus').className='risk'}});
async function init(){
try{
 allGroups=await api('/api/groups');for(const x of allGroups){for(const id of ['group','jobgroup','guidegroup','aigroup']){const o=document.createElement('option');o.value=x.group_name;o.textContent=x.group_name.replaceAll('_',' ')+' ('+x.assemblies+')';$(id).append(o)}}
 const o=$('jobgroup').querySelector('option[value="front_axle"]');if(o)o.selected=true;
}catch(e){fail(e)}
 try{const h=await api('/api/integration/health'),m=await api('/api/manuals/status');$('launchstatus').textContent=`${h.status} · ${m.indexed_documents} evidence documents / ${m.indexed_pages} searchable sections · safety clearance NOT APPROVED`;}catch(e){$('launchstatus').textContent='Subsystem status unavailable: '+e.message}
 await loadGarage();
}
function presentResult(x){const c=text('div',null,'item');c.append(text('div',x.group_name?.replaceAll('_',' '),'group'));
 if(x.part_number)c.append(text('div',x.part_number,'partnum'));
 c.append(text('div',x.description||x.slug?.replaceAll('_',' ')||'Assembly','desc'));
 if(x.callout_position)c.append(text('div',`Callout ${x.callout_position} · Qty ${x.quantity_raw||'?'} · ${x.date_condition_raw||'No date noted'}`,'info'));
 if(x.part_count!==undefined)c.append(text('div',`${x.part_count} catalog rows`,'info'));
 const actions=text('div',null,'actions');const btn=text('button','Open parts & diagram');btn.addEventListener('click',()=>openAssembly(x.assembly_id||x.id));actions.append(btn);
 if(x.anchor)actions.append(document.createTextNode('  '),link('Catalog row',x.anchor));c.append(actions);return c
}
async function search(){const q=$('search').value.trim(),g=$('group').value;if(!q&&!g){$('results').replaceChildren();$('searchmeta').textContent='Enter a term or select a system.';return}
 $('searchmeta').textContent='Searching local catalog…';try{
 const d=await api('/api/search?q='+encodeURIComponent(q)+'&group='+encodeURIComponent(g));$('searchmeta').textContent=`${d.results.length} results returned. ${d.scope||''}`;
 const frag=document.createDocumentFragment();for(const x of d.results)frag.append(presentResult(x));$('results').replaceChildren(frag);
 if(!d.results.length)$('results').append(text('p','No matching records. Try a broader keyword or change system.'));
}catch(e){fail(e)} }
$('searchbtn').addEventListener('click',search);$('search').addEventListener('keydown',e=>{if(e.key==='Enter')search()});$('group').addEventListener('change',search);
function addPartsTable(parts){const tbody=$('partstable').querySelector('tbody');tbody.replaceChildren();for(const p of parts){const tr=text('tr');tr.className='partrow';tr.title='Click to inspect this component';tr.tabIndex=0;tr.addEventListener('click',e=>{if(e.target.tagName!=='A')openPart(p.id)});tr.addEventListener('keydown',e=>{if(e.key==='Enter')openPart(p.id)});for(const v of [p.callout_position,p.part_number,p.description,p.quantity_raw,p.date_condition_raw]){const td=text('td',v||'—');tr.append(td)}if(p.anchor){const a=link('Catalog',p.anchor);tr.lastChild.append(' ',a)}tbody.append(tr)}}
async function openAssembly(id){try{const d=await api('/api/assembly?id='+encodeURIComponent(id));activeAssembly=d.assembly;
 $('detailtitle').textContent=d.assembly.slug.replaceAll('_',' ');$('detailmeta').replaceChildren(text('span',`${d.assembly.group_name} · ${d.parts.length} table rows · `),link('Original catalog page',d.assembly.source_url));
 const target=$('diagrams');target.replaceChildren();for(const f of d.figures){const fig=text('div',null,'diagram');const img=document.createElement('img');img.alt='Exploded diagram (unverified diagram pixel positions)';img.loading='lazy';img.src='/api/diagram?asset='+encodeURIComponent(f.image_asset_id);img.onerror=()=>{
  if(/^https:\/\/ills\.bmwfans\.info\/[a-z0-9-]+\.webp(?:\?.*)?$/.test(f.figure_url||'')){
    img.onerror=()=>{img.remove();fig.append(text('span','Drawing unavailable locally and from the original source.','info'))};
    img.src=f.figure_url;fig.append(text('div','Online source drawing (not an offline file).','info'));
  }else{img.remove();fig.append(text('span','Local drawing missing and remote reference unverified.','info'))}
};fig.append(img);const refs=text('div',null,'links');refs.append(text('div','Figure asset: '+f.image_asset_id,'info'),link('View original source image',f.figure_url));fig.append(refs);target.append(fig)}
 addPartsTable(d.parts);$('detailpanel').hidden=false;window.scrollTo({top:$('detailpanel').offsetTop-10,behavior:'smooth'});
}catch(e){fail(e)}}
$('clearassembly').addEventListener('click',()=>{$('detailpanel').hidden=true;activeAssembly=null});
$('openjobwithassembly').addEventListener('click',()=>{if(!activeAssembly)return;$('jobgroup').value=activeAssembly.group_name;$('jobassembly').textContent='Selected assembly: '+activeAssembly.slug+' ('+activeAssembly.id+')';tab('jobs')});
async function loadSources(){try{const list=await api('/api/sources');$('sourcelist').replaceChildren();for(const s of list){const row=text('div',null,'source');row.append(text('div',s.title,'title'),text('div',`${s.id} · ${s.evidence_tier}`,'code'),text('p',s.status+' — '+s.market_caveat),link('Open reference',s.url));$('sourcelist').append(row)}}catch(e){fail(e)}}
async function loadJobs(){try{const j=await api('/api/jobs');$('joblist').replaceChildren();if(!j.length)$('joblist').append(text('p','No inspection jobs recorded yet.'));for(const x of j){const row=text('div',null,'source');row.append(text('div',`IX-${String(x.id).padStart(4,'0')} · ${x.system.replaceAll('_',' ')} · ${x.status}`,'title'),text('p',x.symptom),text('div',x.risk+' · clearance: '+x.clearance,'code'));const a=text('a','Download job card');a.href='/api/job/'+x.id+'.md';row.append(a);const b=text('button','Add evidence','light');b.style.marginLeft='12px';b.addEventListener('click',()=>{currentJob=x.id;$('newjob').hidden=false;$('newjobtitle').textContent='IX-'+String(x.id).padStart(4,'0')+' · Evidence log';$('jobprompts').replaceChildren();$('jobdownload').replaceChildren(link('Download current job card','/api/job/'+x.id+'.md'));loadCheckpoints(currentJob);window.scrollTo({top:$('newjob').offsetTop-10,behavior:'smooth'})});row.append(b);$('joblist').append(row)}}catch(e){fail(e)}}
$('refreshjobs').addEventListener('click',loadJobs);
$('jobform').addEventListener('submit',async e=>{e.preventDefault();const d={system:$('jobgroup').value,symptom:$('symptom').value,context:$('context').value,assembly_id:activeAssembly?.id||''};try{const x=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});currentJob=x.job_id;$('newjob').hidden=false;$('newjobtitle').textContent='IX-'+String(currentJob).padStart(4,'0')+' · OPEN';const panel=$('jobprompts');panel.replaceChildren(text('p',x.prompts.safety,'risk'),text('h3','Evidence-gathering questions'));
 const ul=text('ul');for(const q of x.prompts.questions)ul.append(text('li',q));panel.append(ul,text('p',x.prompts.reminder,'info'));
 $('jobdownload').replaceChildren(link('Download work order (Markdown)','/api/job/'+currentJob+'.md'));$('notestatus').textContent='Job saved to a separate local database, not your V3/V4 corpus.';await loadJobs();window.scrollTo({top:$('newjob').offsetTop-10,behavior:'smooth'});
}catch(e){fail(e)}});
$('noteform').addEventListener('submit',async e=>{e.preventDefault();if(!currentJob)return;const d={type:$('notetype').value,value:$('notevalue').value,unit:$('noteunit').value,tool:$('notetool').value,source:$('notesource').value};try{await api('/api/job/'+currentJob+'/observation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});$('notestatus').textContent='Observation saved. Job remains OPEN; no safety clearance has been issued.';$('notevalue').value='';await loadJobs()}catch(e){fail(e)}});
init();

async function loadTwin(){try{const d=await api('/api/twin');const t=d.twin;const xp=d.gamification.xp;$('twinxp').textContent=xp+' XP · Level '+d.gamification.level;$('twinfacts').replaceChildren();[['VIN',t.vin],['Factory state',JSON.stringify(t.factory_state)],['As-installed state',JSON.stringify(t.as_installed_state)],['Confidence',JSON.stringify(t.confidence)],['Last updated',t.updated_utc]].forEach(([k,v])=>$('twinfacts').append(fieldRow(k,v,'RECORDED')));const progress=Math.min(100,Math.round((xp%100)));$('twinprogress').querySelector('span').style.width=progress+'%';$('twinprogresslabel').textContent=`${xp} evidence points recorded · ${100-(xp%100)} points to next level · rewards never grant safety or fitment approval.`;const root=$('twinevents');root.replaceChildren();if(!d.events.length)root.append(text('p','No twin events recorded yet. Start a case or add structured evidence.','info'));for(const e of d.events.slice(0,30)){const row=text('div',null,'source');row.append(text('div',`${e.event_type.replaceAll('_',' ')} · ${e.entity_type} ${e.entity_id} · +${e.xp_value} XP`,'title'),text('div',JSON.stringify(e.payload),'info'),text('div',`${e.created_utc} · ${e.source}`,'meta'));root.append(row)}}catch(e){$('twinfacts').replaceChildren(text('p','Digital twin unavailable: '+e.message,'risk'))}}
async function loadTwinComponents(){let root=$('twincomponents');if(!root){root=text('section',null,'panel');root.id='twincomponents';root.innerHTML='<h3>As-built component registry</h3><p class="small">Record component instances without collapsing catalog identity, installed condition or mechanic verification.</p><form id="componentform"><div class="searchrow"><label>Component<input id="componenttype" required placeholder="e.g. front-left steering tie rod"></label><label>Location<input id="componentlocation" placeholder="Front axle / steering rack…"></label><label>Side<select id="componentside"><option value="UNKNOWN">Unknown</option><option value="LEFT">Left</option><option value="RIGHT">Right</option><option value="BOTH">Both</option></select></label></div><div class="searchrow"><label>OEM number<input id="componentpart" placeholder="Optional exact number"></label><label>Marking<input id="componentmarking" placeholder="Stamped marking / serial"></label><label>Condition<input id="componentcondition" placeholder="Observed only"></label></div><label>Source / person<input id="componentsource" required placeholder="Owner photo, mechanic, catalog…"></label><button type="submit">Add component instance</button><span id="componentstatus" class="info" role="status"></span></form><div id="componentlist"></div>';$("twinfacts").after(root);$("componentform").addEventListener('submit',async e=>{e.preventDefault();try{const d=await api('/api/twin/component',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({component_type:$("componenttype").value,location:$("componentlocation").value,side:$("componentside").value,oem_part_number:$("componentpart").value,marking:$("componentmarking").value,condition:$("componentcondition").value,source:$("componentsource").value})});$("componentstatus").textContent=`Saved component ${d.component_id}; identity remains unconfirmed`;e.target.reset();await loadTwinComponents();await loadTwin()}catch(e){$("componentstatus").textContent=e.message;$("componentstatus").className='risk'}})}try{const d=await api('/api/twin/components');const list=$("componentlist");list.replaceChildren();if(!d.components.length)list.append(text('p','No component instances recorded yet.','info'));for(const c of d.components){const row=text('div',null,'source');row.append(text('div',`${c.component_type} · ${c.location||'location unknown'} · ${c.side||'side unknown'}`,'title'),text('div',`OEM ${c.oem_part_number||'unknown'} · marking ${c.marking||'unknown'} · status ${c.status}`,'info'));for(const f of c.facts||[])row.append(text('div',`${f.layer}.${f.field}: ${f.value} · ${f.confidence} · ${f.source}`,'meta'));list.append(row)}const u=d.uncertainty;list.append(text('p',`Uncertainty map: owner ${u.owner_reported||0} · source ${u.source_verified||0} · mechanic ${u.mechanic_verified||0} · conflicting ${u.conflicting||0}`,'code'))}catch(e){if(root)$("componentlist").replaceChildren(text('p','Component registry unavailable: '+e.message,'risk'))}}
$('twineventform').addEventListener('submit',async e=>{e.preventDefault();try{const payload=JSON.parse($('twineventpayload').value);const d=await api('/api/twin/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_type:$('twineventtype').value,entity_type:$('twinevententity').value,payload,source:$('twineventsource').value})});$('twineventstatus').textContent=`Saved · +${d.xp_value} evidence points · safety remains NOT APPROVED`;$('twineventpayload').value='';await loadTwin()}catch(e){$('twineventstatus').textContent=e.message;$('twineventstatus').className='risk'}});

async function loadAIStatus(){try{const x=await api('/api/ai/status');$('aistatus').textContent=x.enabled?(x.available?`Connected to ${x.selected}. Installed models: ${(x.installed_models||[]).join(', ')}`:`Ollama not available: ${x.error||'Start it first'}`):x.message}catch(e){$('aistatus').textContent=e.message}}
$('guidebtn').addEventListener('click',async()=>{const system=$('guidegroup').value,symptom=$('guidesymptom').value.trim();if(!system||!symptom){alert('Choose a system and describe the observed symptom');return}const target=$('guideresult');target.replaceChildren(text('p','Retrieving inspection guidance…'));try{const d=await api('/api/diagnostic?system='+encodeURIComponent(system)+'&symptom='+encodeURIComponent(symptom));target.replaceChildren();target.append(text('h3','Safety gate'),text('p',d.safety,'risk'),text('h3','Questions and observations to record'));const ul=text('ul');for(const x of d.questions)ul.append(text('li',x));target.append(ul,text('p',d.reminder,'info'),text('h3','Candidate assemblies (not a diagnosis)'));const items=text('div',null,'gridresults');for(const a of d.candidate_assemblies.slice(0,8)){const row=text('div',null,'item');row.append(text('div',a.slug.replaceAll('_',' '),'desc'),text('div',a.part_count+' catalog rows','info'));const b=text('button','View catalog');b.onclick=()=>{tab('lookup');openAssembly(a.id)};row.append(b);items.append(row)}target.append(items,text('h3','Source references to consult'));for(const r of d.technical_references.slice(0,8)){const line=text('p');line.append(link(r.title,r.url),text('span',' · '+r.status,'info'));target.append(line)}target.append(text('p',d.caution,'risk'));const b=text('button','Create inspection work order');b.onclick=()=>{$('jobgroup').value=system;$('symptom').value=symptom;$('context').value='Created from diagnostic guide; candidate causes not confirmed.';activeAssembly=null;$('jobassembly').textContent='Assembly not yet selected';tab('jobs')};target.append(b)}catch(e){fail(e)}});
$('aibtn').addEventListener('click',async()=>{const question=$('aiquestion').value.trim();if(question.length<8){alert('Describe the technical question first');return}$('aibtn').disabled=true;$('aianswer').textContent='Grounded assistant is analyzing retrieved evidence…';$('aievidence').replaceChildren();try{const d=await api('/api/ai/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,system:$('aigroup').value,language:$('ailanguage').value,job_id:typeof expertJobId!=='undefined'?(expertJobId||currentJob||''):currentJob||''})});$('aianswer').textContent=d.answer+'\n\nCAUTION: '+d.policy;const evidence=$('aievidence');evidence.append(text('h3','Retrieved catalog evidence'));for(const r of d.catalog_evidence.slice(0,12)){const p=text('p');p.append(text('strong',(r.part_number||'?')+' · '+r.description+' ['+r.slug+'] · '),link('Source',r.source_url));evidence.append(p)}if(d.manual_excerpts?.length)evidence.append(text('p',`${d.manual_excerpts.length} cited manual excerpts included with provenance.`,'info'));}catch(e){$('aianswer').textContent=e.message}finally{$('aibtn').disabled=false}});
async function showAIRouting(){const question=$('aiquestion').value.trim();if(question.length<8)return;let root=$('airouting');if(!root){root=text('div',null,'caseoverview');root.id='airouting';$('aibtn').after(root)}try{const r=await api('/api/ai/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,system:$('aigroup').value})});root.replaceChildren(text('h3','Specialist routing'),text('p',`${r.specialist.label} · ${r.safety_class} · ${r.confidence}`,'code'),text('p','Required evidence: '+r.required_evidence.join('; '),'info'),text('p','Approval gate: '+r.approval_gates.join(', '),'risk'))}catch(e){root.replaceChildren(text('p','Routing unavailable: '+e.message,'risk'))}}
$('aibtn').addEventListener('click',showAIRouting);
function setupVoice(){const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){$('voicebtn').disabled=true;$('voicestatus').textContent='Browser speech recognition is unavailable; type the question instead.';return}$('voicebtn').addEventListener('click',()=>{const r=new SpeechRecognition();r.lang=$('ailanguage').value==='ar'?'ar-LB':'en-US';r.interimResults=false;r.maxAlternatives=1;$('voicestatus').textContent='Listening…';r.onresult=e=>{$('aiquestion').value=e.results[0][0].transcript;$('voicestatus').textContent='Dictation captured; review before sending.'};r.onerror=e=>$('voicestatus').textContent='Voice input failed: '+e.error;r.onend=()=>{if($('voicestatus').textContent==='Listening…')$('voicestatus').textContent='Voice input ended.'};r.start()});$('speakbtn').addEventListener('click',()=>{const answer=$('aianswer').textContent.trim();if(!answer)return;$('voicestatus').textContent='Reading answer…';const u=new SpeechSynthesisUtterance(answer);u.lang=$('ailanguage').value==='ar'?'ar-LB':'en-US';u.onend=()=>{$('voicestatus').textContent='Answer read aloud.'};speechSynthesis.cancel();speechSynthesis.speak(u)})}
setupVoice();

// V0.3: independently tracked inspection steps; no automatic sign-off.
async function loadCheckpoints(jobId){
 if(!jobId)return;const root=$('jobchecks');if(!root)return;
 try{const d=await api('/api/job/checks?job_id='+encodeURIComponent(jobId));root.replaceChildren();
 if(!d.checks.length){root.append(text('p','No tracked checkpoints for this older work order. Create a new job to use the guided checklist.','info'));return}
 for(const check of d.checks){const wrap=text('div',null,'source');wrap.append(text('div',check.label,'title'));
 const select=document.createElement('select');for(const v of ['NOT_CHECKED','OBSERVED','NOT_APPLICABLE','NEEDS_SPECIALIST']){const opt=document.createElement('option');opt.value=v;opt.textContent=v.replaceAll('_',' ');opt.selected=check.status===v;select.append(opt)}
 const finding=document.createElement('textarea');finding.rows=2;finding.placeholder='What was actually seen or measured?';finding.value=check.finding;
 const source=document.createElement('input');source.placeholder='Photo ID / manual page / mechanic';source.value=check.source;
 const save=text('button','Save checkpoint','light');save.onclick=async()=>{try{await api('/api/job/checks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:jobId,code:check.code,status:select.value,finding:finding.value,source:source.value})});save.textContent='Saved';setTimeout(()=>save.textContent='Save checkpoint',1000)}catch(e){fail(e)}};
 wrap.append(select,finding,source,save);root.append(wrap)
 }}catch(e){root.replaceChildren(text('p',e.message,'risk'))}}

// Wrap existing job entry points without modifying the V0.2 catalog search.
const _existingLoadJobs=loadJobs;
loadJobs=async function(){await _existingLoadJobs(); if(currentJob)await loadCheckpoints(currentJob)};

async function loadManualStatus(){try{const s=await api('/api/manuals/status');$('manualstatus').textContent=s.indexed_documents+' documents, '+s.indexed_pages+' searchable text sections, '+(s.claim_records||0)+' curated claims, '+(s.unresolved_conflict_groups||0)+' unresolved conflict groups. '+s.message}catch(e){$('manualstatus').textContent=e.message}}
$('manualbtn').addEventListener('click',async()=>{const q=$('manualq').value.trim();if(!q){$('manualresults').textContent='Enter a manual keyword.';return}
try{const d=await api('/api/manuals/search?q='+encodeURIComponent(q));const root=$('manualresults');root.replaceChildren();if(!d.results.length){root.append(text('p','No matching passages in currently imported documents. Source links are not searchable text until imported.','info'));return}
for(const r of d.results){const item=text('div',null,'source');const p=r.provenance||{};item.append(text('div',r.citation||r.title+' · '+r.page_label,'title'),text('pre',r.excerpt,'manualexcerpt'),text('p','Evidence: '+(p.verification_status||r.verification_status)+' · market '+(p.market||r.market)+' · variant '+(p.variant_scope||'UNVERIFIED'),'info'),text('p','Authority: '+(p.authority||'UNVERIFIED')+' · hash '+(p.page_sha256||'not available'),'meta'));if(r.source_url)item.append(link('Source',r.source_url));root.append(item)}
}catch(e){fail(e)}});
$('manualq').addEventListener('keydown',e=>{if(e.key==='Enter')$('manualbtn').click()});
// Existing tab() call happens at click time, and this additive listener updates status.
for(const b of document.querySelectorAll('[data-tab="manuals"]'))b.addEventListener('click',loadManualStatus);
api('/api/v4/status').then(s=>{$('v4status').textContent=s.connected?`V4 connected: ${s.images_present_locally} of ${s.manifest_assets} diagrams available on this Mac.`:'V4 drawings are complete in Drive; copy the V4 folder locally and start with --v4-root to display them.'}).catch(()=>{});

// V0.4 part-detail workspace: strictly separate drawing, photographed physical part, and evidence.
let activePart=null;
function fieldRow(k,v,status){const row=text('div',null,'factrow');const lab=text('div',k,'factlabel');const value=text('div',v===null||v===undefined||v===''?'Not verified / not supplied':v,'factvalue');const badge=text('span',status||'UNKNOWN','factstatus');row.append(lab,value,badge);return row}
async function openPart(id){
 try{
  const d=await api('/api/part-dossier?id='+encodeURIComponent(id));activePart=d.part;
  const e=d.curated||{};
  $('parttitle').textContent=(d.part.part_number||'Unknown number')+' · '+(e.label||d.part.description||'Component');
  $('partscope').textContent='Callout '+(d.part.callout_position||'?')+' · '+d.part.group_name+' / '+d.part.slug.replaceAll('_',' ')+' · catalog evidence, not certified fitment';
  const fact=$('partfacts');fact.replaceChildren();for(const f of d.technical_fields){fact.append(fieldRow(f.name,f.value,f.status))}
  const ev=$('partevidence');ev.replaceChildren();
  if(e.label&&d.part.description&&e.label.toLowerCase()!==d.part.description.toLowerCase()) ev.append(text('p','Source-reviewed description: '+e.label+' · original catalog: '+d.part.description,'info'));
  for(const item of (e.conflicts||[])) ev.append(text('div','CATALOG QUALITY FLAG: '+item,'risk'));
  for(const s of (e.sources||[])){const p=text('p');p.append(link(s.label,s.url),text('span',' · '+s.status,'info'));ev.append(p)}
  if(e.inspection_questions?.length){ev.append(text('h4','Before deciding on repair/replacement'));const u=text('ul');for(const q of e.inspection_questions)u.append(text('li',q));ev.append(u)}
  for(const f of (d.researched_fields||[])){const row=fieldRow('RESEARCH · '+f.name,f.value,f.status);if(f.source_url)row.append(link('Evidence',f.source_url));fact.append(row)}

  const catalog=text('p');catalog.append(link('Original assembly catalog',d.part.source_url));ev.append(catalog);
  if(d.part.anchor){const p=text('p');p.append(link('Exact catalog part row',d.part.anchor));ev.append(p)}
  for(const f of d.figures){const p=text('p');p.append(link('Original exploded drawing',f.figure_url),text('span','  · '+f.image_asset_id,'info'));ev.append(p)}
  ev.append(text('p',d.evidence_policy,'info'));
  const pd=$('partdiagrams');pd.replaceChildren();
  for(const fig of (d.figures||[])){
    const panel=text('div',null,'partdiagramcard');
    const badge=text('div','PART CALLOUT: '+(d.part.callout_position||'?')+' — exact pixel hotspot not verified','info');
    const img=document.createElement('img');img.alt='Exploded assembly drawing for '+d.part.part_number+'; see numbered callout '+d.part.callout_position;
    img.src='/api/diagram?asset='+encodeURIComponent(fig.image_asset_id);img.loading='lazy';
    img.onerror=()=>{
      if(/^https:\/\/ills\.bmwfans\.info\/[a-z0-9-]+\.webp(?:\?.*)?$/.test(fig.figure_url||'')){
        img.onerror=()=>img.replaceWith(text('div','Drawing unavailable; open the catalog source.','emptyphoto'));
        img.src=fig.figure_url;panel.append(text('p','Online reference · not locally stored','info'));
      }else img.replaceWith(text('div','No local drawing available','emptyphoto'));
    };
    panel.append(badge,img,link('Original exploded drawing',fig.figure_url));pd.append(panel)
  }
  const photos=$('partphotos');photos.replaceChildren();
  const remote=(e.supplier_photo_refs||[]);
  if(!d.photos.length&&!remote.length)photos.append(text('div','No source-matched physical part photograph found yet. Use the supplier references to research it or add your own workshop photo.','emptyphoto'));
  for(const ref of remote){
    const card=text('div',null,'photocard external-photo');
    const label=text('div',ref.label,'photolabel');
    const status=text('div',ref.status,'info');
    if(/^https:\/\/(?:www\.bimmerworld\.com|i\.ebayimg\.com|www\.rageitparts\.com|3a663eb0fef48c6d2d60-a88f8ebfcdb877ad223e888bfcb7f7ec\.ssl\.cf1\.rackcdn\.com)\//.test(ref.url)){
      const img=document.createElement('img');img.src=ref.url;img.loading='lazy';img.referrerPolicy='no-referrer';img.alt='Third-party product photo: '+ref.label;img.onerror=()=>{img.replaceWith(text('div','External image unavailable — open seller source','emptyphoto'))};card.append(img)
    }
    card.append(label,status,link('Original product listing',ref.source_url));photos.append(card)
  }

  for(const ph of d.photos){const card=text('div',null,'photocard');const img=document.createElement('img');img.src=ph.image_url;img.alt=ph.kind+' for part '+ph.part_number+' supplied by '+ph.source_label;img.loading='lazy';const label=text('div',ph.kind.replaceAll('_',' ')+' · '+ph.source_label,'photolabel');card.append(img,label);if(ph.source_url)card.append(link('Source listing',ph.source_url));photos.append(card)}
  const notice=text('p',(e.evidence_status||'NOT_RESEARCHED')+' · Online supplier references are not evidence of what is installed on your vehicle.','info');
  ev.append(notice);
  const reg=d.catalog_research||{};
  if(reg.catalog_flags?.length){for(const issue of reg.catalog_flags)ev.append(text('div','CATALOG REVIEW FLAG: '+issue,'risk'))}
  if(reg.candidate_research_links){
    ev.append(text('h4','Unverified research leads — open original listings and check exact number'));
    const row=text('p');row.append(link('Part-number search',reg.candidate_research_links.web_evidence_lookup),
       document.createTextNode(' · '),link('Product-photo search',reg.candidate_research_links.web_image_lookup));ev.append(row);
  }
  $('partdossier').hidden=false;$('partdossier').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){fail(e)}
}
$('closepart').addEventListener('click',()=>{$('partdossier').hidden=true;activePart=null});
$('partphoto-add').addEventListener('click',async()=>{
 const f=$('partphoto-file').files[0];const label=$('partphoto-source').value.trim();
 if(!activePart||!activePart.part_number)return alert('Choose a part with a catalog number first');
 if(!f||!label)return alert('Select a file and enter who supplied the photograph');
 if(f.size>2800000)return alert('Please reduce photo size to 2.8 MB or less');
 const upload=$('partphoto-add');upload.disabled=true;$('partphoto-result').textContent='Saving actual-part photo locally…';
 try{
  const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Cannot read photo'));reader.readAsDataURL(f)});
  await api('/api/part-photo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({part_number:activePart.part_number,kind:$('partphoto-type').value,source_label:label,source_url:$('partphoto-url').value.trim(),filename:f.name,image_base64:encoded})});
  $('partphoto-result').textContent='Photo saved with attribution. Fitment remains unverified.';
  const id=activePart.id;await openPart(id);
 }catch(e){$('partphoto-result').textContent=e.message}finally{upload.disabled=false}
});

api('/api/evidence/coverage').then(s=>{const el=document.createElement('div');el.className='meta';el.textContent=`Live curated evidence: ${s.researched_exact_part_numbers} exact OEM-number dossiers; ${s.physical_photo_reference_count} supplier photo references (external); ${s.alternative_photo_reference_count} alternative photo examples. `+$('v4status').textContent;$('v4status').replaceWith(el);el.id='v4status'}).catch(()=>{});

// V0.6 full catalog research program; independent from parts catalog and job DB.
let lastProgramBatch=0;
async function loadProgramCoverage(){
 try{
  const s=await api('/api/catalog/coverage');
  $('catalogcoverage').textContent=`Catalog: ${s.unique_part_numbers} distinct OEM numbers / ${s.catalog_rows} ETK rows / ${s.assemblies} assemblies / ${s.unique_diagram_assets} drawings. `+
   `Researched: ${s.researched_exact_number_records}. Unresearched: ${s.unique_part_numbers-s.researched_exact_number_records}. `+
   `Physical photo references: ${s.supplier_photo_references} (external). Offline verified product photos: ${s.offline_individual_product_photos_verified}. `+
   `Research batches: ${s.batches} × up to ${s.batch_size}. Fitment and full technical specs: unverified unless specifically sourced.`;
 }catch(e){$('catalogcoverage').textContent=e.message}
}
async function viewProgramBatch(n){
 try{
  const d=await api('/api/catalog/worklist?batch='+n);lastProgramBatch=n;
  const target=$('batchresults');target.replaceChildren();
  for(const v of d.parts){
   const card=text('div',null,'item');card.append(text('div',v.part_number,'partnum'),text('div',v.catalog_description,'desc'),
      text('div',v.groups.join(', '),'group'),text('div',v.evidence_status,'info'));
   if(v.catalog_flags?.length)card.append(text('div',v.catalog_flags.join(' · '),'risk'));
   const actions=text('div',null,'actions');
   const btn=text('button','Open part dossier','light');btn.addEventListener('click',async()=>{
    try{const x=await api('/api/search?q='+encodeURIComponent(v.part_number));if(!x.results?.length)throw Error('Catalog occurrence missing');
     tab('lookup');await openAssembly(x.results[0].assembly_id);await openPart(x.results[0].id)}catch(e){fail(e)}
   });actions.append(btn,link('Find product photo',v.candidate_research_links.web_image_lookup),link('Part evidence',v.candidate_research_links.web_evidence_lookup));
   card.append(actions);target.append(card);
  }
 }catch(e){$('batchresults').textContent=e.message}
}
$('loadbatch').addEventListener('click',()=>viewProgramBatch(Number($('batchnum').value||1)));
$('nextunresearched').addEventListener('click',()=>{const n=lastProgramBatch||1;$('batchnum').value=Math.min(n+1,144);viewProgramBatch(Number($('batchnum').value))});
for(const btn of document.querySelectorAll('[data-tab="program"]'))btn.addEventListener('click',()=>{loadProgramCoverage();viewProgramBatch(Number($('batchnum').value||1))});


// RC0.7 guided front-axle inspection workflow. Persistent job records, never auto-diagnose.
let expertDefinition=null, expertJobId=null;
function expertStateTag(status){return status.replaceAll('_',' ').toLowerCase()}
async function expertInit(){
 try{
  expertDefinition=await api('/api/expert/front-play');
  $('expertwarning').textContent=expertDefinition.warning;
  $('expertv4').textContent=expertDefinition.v4.present+' locally available image assets / '+expertDefinition.v4.assets_in_manifest+' manifest entries. Incomplete local pack must be supplied separately.';
  const asm=$('expertassemblies');asm.replaceChildren();
  for(const a of expertDefinition.assemblies){
   const wrap=text('article',null,'expertassembly');
   wrap.append(text('h4',a.label),text('p',a.system.replaceAll('_',' ')+' · '+a.slug.replaceAll('_',' '),'info'));
   const f=a.figures[0];
   if(f?.image_asset_id){const img=document.createElement('img');img.alt='Exploded parts diagram for '+a.label+'; graphic callout coordinates not verified';img.loading='lazy';img.src='/api/diagram?asset='+encodeURIComponent(f.image_asset_id);
    img.onerror=()=>{img.remove();wrap.append(text('p','Local drawing missing; use source link.','risk'))};wrap.append(img)}
   const open=text('button','Open diagram and parts','light');open.addEventListener('click',()=>{tab('lookup');openAssembly(a.id)});
   wrap.append(open,link('Catalog source',a.source_url));asm.append(wrap)
  }
  const parts=$('expertparts');parts.replaceChildren();
  for(const p of expertDefinition.parts){const card=text('div',null,'source');card.append(text('strong',p.number+' · '+p.label),text('p',p.source_reviewed?'Source-reviewed exact-number record; fitment still unverified':'Original catalog only; source review pending','info'));
   if(p.rows.length){const btn=text('button','Inspect component','light');btn.addEventListener('click',async()=>{tab('lookup');await openAssembly(p.rows[0].assembly_id);await openPart(p.rows[0].id)});card.append(btn)}
   parts.append(card)
  }
  const sources=$('expertsources');sources.replaceChildren();
  for(const s of expertDefinition.sources){const card=text('article',null,'source');card.append(text('h4',s.title),text('p','Page '+s.source_page+' · '+s.status,'info'),text('p',s.summary),link('Read referenced BMW TIS page',s.url));sources.append(card)}
  await expertList();
 }catch(e){$('expertv4').textContent='Expert workflow cannot load: '+e.message}
}
async function expertList(){
 try{const res=await api('/api/expert/front-play/cases');const wrap=$('expertcases');wrap.replaceChildren();if(!res.cases.length)wrap.append(text('p','No saved front-wheel-play cases yet.','info'));
  for(const c of res.cases){const el=text('div',null,'item');el.append(text('strong','IX-'+String(c.job_id).padStart(4,'0')+' · '+c.side),text('p',c.symptom));const open=text('button','Resume inspection','light');open.addEventListener('click',()=>expertOpen(c.job_id));el.append(open);wrap.append(el)}
 }catch(e){$('expertcases').replaceChildren(text('p',e.message,'risk'))}
}
async function expertOpen(jobId){
 try{
  if(!expertDefinition)await expertInit();
  const res=await api('/api/expert/front-play/cases?job_id='+encodeURIComponent(jobId));
  expertJobId=jobId;$('expertcasepanel').hidden=false;$('expertoverview').hidden=false;
  const overview=await api('/api/job/'+jobId+'/overview');const ov=$('expertoverview');ov.replaceChildren(text('h3','Case cockpit'),text('p',`Evidence items: ${overview.readiness.evidence_count} · Twin events: ${overview.twin_events.length} · Clearance: ${overview.readiness.clearance}`,'code'));
  const blockers=text('ul');for(const b of overview.readiness.blockers)blockers.append(text('li',b,'risk'));ov.append(text('h4','Current blockers'),blockers);if(overview.specialist_findings.length){ov.append(text('h4','Specialist findings'));for(const f of overview.specialist_findings)ov.append(text('p',`${f.agent_id} · ${f.intent} · ${f.status} · uncertainty: ${f.uncertainty}`,'info'))}
  $('expertcasetitle').textContent='IX-'+String(jobId).padStart(4,'0')+' · '+res.case.side+' · road clearance NOT APPROVED';
  $('expertexport').href='/api/job/'+jobId+'.md';
  const stateByCode=Object.fromEntries(res.steps.map(x=>[x.code,x]));
  const root=$('expertsteps');root.replaceChildren();
  for(const step of expertDefinition.steps){
   const state=stateByCode[step.code]||{status:'NOT_CHECKED',finding:'',source:''};
   const el=text('section',null,'expertstep');el.append(text('h3',step.title),text('p',step.purpose),text('p',step.prompt,'meta'),text('p','Required evidence: '+step.evidence,'info'));
   const refs=text('div',null,'expertrefs');for(const sid of step.source_ids){const s=expertDefinition.sources.find(x=>x.id===sid);if(s)refs.append(link(s.id+' · page '+s.source_page,s.url))}el.append(refs);
   const status=document.createElement('select');status.setAttribute('aria-label','Check status for '+step.title);
   for(const value of ['NOT_CHECKED','OBSERVED','NEEDS_SPECIALIST','NOT_APPLICABLE']){const op=document.createElement('option');op.value=value;op.textContent=expertStateTag(value);op.selected=state.status===value;status.append(op)}
   const finding=document.createElement('textarea');finding.rows=2;finding.setAttribute('aria-label','Observed finding for '+step.title);finding.placeholder='Finding or unresolved issue; do not enter assumed measurements';finding.value=state.finding;
   const source=document.createElement('input');source.setAttribute('aria-label','Evidence source for '+step.title);source.placeholder='Photo ID / BMW page / mechanic';source.value=state.source;
   const msg=text('span','','info');msg.setAttribute('role','status');
   const save=text('button','Save step','light');save.type='button';save.addEventListener('click',async()=>{
    try{await api('/api/expert/front-play/step',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:jobId,code:step.code,status:status.value,finding:finding.value,source:source.value})});msg.textContent='Saved · road approval still NOT APPROVED'}catch(e){msg.textContent=e.message;msg.className='risk'}
   });el.append(status,finding,source,save,msg);root.append(el)
  }
  const obsroot=$('expertobservations');obsroot.replaceChildren();
  for(const o of (res.observations||[])){const row=text('div',null,'source');row.append(text('div',o.type+' · '+o.value,'title'),text('div',(o.unit||'')+' · tool '+(o.tool||'?')+' · source '+(o.source||'?'),'info'));obsroot.append(row)}
  const options=await api('/api/job/'+jobId+'/options');const optroot=$('expertoptions');optroot.replaceChildren();for(const o of (options.options||[])){const row=text('div',null,'source');row.append(text('div',o.path.replaceAll('_',' ')+' · '+o.description,'title'),text('div','Part '+(o.part_number||'?')+' · fitment '+o.fitment_status+' · decision '+o.decision_status,'info'),text('div','Evidence: '+o.evidence+' · source: '+o.source+' · cost: '+(o.cost_estimate||'?')+' · availability: '+(o.availability||'?'),'meta'));optroot.append(row)}
  $('expertobservationform').onsubmit=async e=>{e.preventDefault();try{await api('/api/job/'+jobId+'/observation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:$('expertobstype').value,value:$('expertobsvalue').value,unit:$('expertobsunit').value,tool:$('expertobstool').value,source:$('expertobssource').value})});$('expertobsstatus').textContent='Saved · case remains open and NOT_APPROVED';$('expertobsvalue').value='';await expertOpen(jobId)}catch(e){$('expertobsstatus').textContent=e.message;$('expertobsstatus').className='risk'}};
  $('expertoptionform').onsubmit=async e=>{e.preventDefault();try{await api('/api/job/'+jobId+'/options',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:$('expertoptionpath').value,description:$('expertoptiondesc').value,part_number:$('expertoptionpart').value,fitment_status:$('expertoptionfit').value,decision_status:$('expertoptiondecision').value,evidence:$('expertoptionevidence').value,source:$('expertoptionsource').value,cost_estimate:$('expertoptioncost').value,availability:$('expertoptionavailability').value})});$('expertoptionstatus').textContent='Saved · pending qualified review; clearance remains NOT_APPROVED';$('expertoptiondesc').value='';$('expertoptionevidence').value='';await expertOpen(jobId)}catch(e){$('expertoptionstatus').textContent=e.message;$('expertoptionstatus').className='risk'}};
  $('expertcasepanel').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){alert('Expert inspection: '+e.message)}
}
$('expertstart').addEventListener('submit',async e=>{
 e.preventDefault();try{const c=await api('/api/expert/front-play/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({side:$('expertside').value,symptom:$('expertsymptom').value,context:$('expertcontext').value})});await expertList();await expertOpen(c.job_id)}catch(e){alert('Cannot start inspection: '+e.message)}
});
$('expertrefresh').addEventListener('click',expertList);
for(const b of document.querySelectorAll('[data-tab="expert"]'))b.addEventListener('click',expertInit);
const _twinLoadWithComponents=loadTwin;loadTwin=async function(){await _twinLoadWithComponents();await loadTwinComponents()};/*
async function ensureComponentAttachmentUI(){let root=$('twincomponents');if(!root)return;let form=$('componentattachmentform');if(!form){form=document.createElement('form');form.id='componentattachmentform';form.innerHTML='<h4>Attach photo evidence</h4><div class="searchrow"><label>Component<select id="attachmentcomponent"></select></label><label>Title<input id="attachmenttitle" required placeholder="Front-left tie-rod as-found photo"></label></div><div class="searchrow"><label>Photo<input id="attachmentfile" type="file" accept="image/jpeg,image/png,image/webp" required></label><label>Source / person<input id="attachmentsource" required placeholder="Owner photo / mechanic"></label></div><label>Variant scope<input id="attachmentvariant" placeholder="Swiss/ECE 1987-12 325iX; verify"></label><button type="submit">Attach photo to component</button><span id="attachmentstatus" class="info" role="status"></span>';root.append(form);form.addEventListener('submit',async e=>{e.preventDefault();const file=$("attachmentfile").files[0];if(!file){$("attachmentstatus").textContent='Choose an image first';return}const reader=new FileReader();reader.onload=async()=>{try{const d=await api('/api/twin/component/'+$("attachmentcomponent").value+'/attachment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'PHOTO',title:$("attachmenttitle").value,source:$("attachmentsource").value,variant_scope:$("attachmentvariant").value,image_base64:String(reader.result).split(',')[1]})});$("attachmentstatus").textContent=`Attached photo ${d.attachment_id}; hash ${d.sha256.slice(0,12)}…`;form.reset();await loadTwinComponents()}catch(err){$("attachmentstatus").textContent=err.message;$("attachmentstatus").className='risk'}};reader.readAsDataURL(file)});};}try{const d=await api('/api/twin/components');const select=$("attachmentcomponent");if(select){select.replaceChildren();for(const c of d.components){const option=document.createElement('option');option.value=c.id;option.textContent=c.component_type+' · '+(c.location||'location unknown');select.append(option)}select.disabled=!d.components.length}}catch(e){if($("attachmentstatus"))$("attachmentstatus").textContent=e.message}}
*/
const _baseComponentLoader=loadTwinComponents;loadTwinComponents=async function(){await _baseComponentLoader();await ensureComponentAttachmentUI()};
async function ensureComponentAttachmentUI(){const root=$('twincomponents');if(!root)return;let form=$('componentattachmentform');if(!form){form=document.createElement('form');form.id='componentattachmentform';form.innerHTML='<h4>Attach photo evidence</h4><div class="searchrow"><label>Component<select id="attachmentcomponent"></select></label><label>Title<input id="attachmenttitle" required placeholder="Front-left tie-rod as-found photo"></label></div><div class="searchrow"><label>Photo<input id="attachmentfile" type="file" accept="image/jpeg,image/png,image/webp" required></label><label>Source / person<input id="attachmentsource" required placeholder="Owner photo / mechanic"></label></div><label>Variant scope<input id="attachmentvariant" placeholder="Swiss/ECE 1987-12 325iX; verify"></label><button type="submit">Attach photo to component</button><span id="attachmentstatus" class="info" role="status"></span>';root.append(form);form.addEventListener('submit',async e=>{e.preventDefault();const file=$("attachmentfile").files[0];if(!file){$("attachmentstatus").textContent='Choose an image first';return}const reader=new FileReader();reader.onload=async()=>{try{const d=await api('/api/twin/component/'+$("attachmentcomponent").value+'/attachment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'PHOTO',title:$("attachmenttitle").value,source:$("attachmentsource").value,variant_scope:$("attachmentvariant").value,image_base64:String(reader.result).split(',')[1]})});$("attachmentstatus").textContent=`Attached photo ${d.attachment_id}; hash ${d.sha256.slice(0,12)}…`;form.reset();await loadTwinComponents()}catch(err){$("attachmentstatus").textContent=err.message;$("attachmentstatus").className='risk'}};reader.readAsDataURL(file)});}try{const d=await api('/api/twin/components');const select=$("attachmentcomponent");if(select){select.replaceChildren();for(const c of d.components){const option=document.createElement('option');option.value=c.id;option.textContent=c.component_type+' · '+(c.location||'location unknown');select.append(option)}select.disabled=!d.components.length}}catch(e){if($("attachmentstatus"))$("attachmentstatus").textContent=e.message}}
function ensureVisualTwinUI(){
 if($('visualtwin'))return;
 const panel=text('div',null,'panel visual-twin ix-studio-v2');panel.id='visualtwin';
 panel.innerHTML=`
 <div class="ix-studio-head">
  <div><div class="ix-eyebrow">BMW 325iX · RESTORATION OS / VISUAL WORKSHOP</div><h2>Explore the car. Find the part.</h2><p>3D model for orientation · BMW catalog drawings for part identification · documented workshop decisions</p></div>
  <span class="ix-ref-chip">REFERENCE GEOMETRY · NOT DIMENSIONAL CAD</span>
 </div>
 <div class="ix-studio-toolbar">
  <div class="ix-mode-tabs"><button id="ix-mode-3d" class="ix-mode-btn active" type="button">◈ 3D model</button><button id="twin2d" class="ix-mode-btn" type="button">▤ OEM drawings</button></div>
  <div class="ix-studio-tools"><button type="button" id="twinreset" class="light">Reset view</button><label class="ix3d-explode-label">Explode <input type="range" id="ix3d-explode" min="0" max="100" value="0"><output id="ix3d-explode-value">0%</output></label>
   <select id="ix-view-select" aria-label="Camera angle"><option value="iso">3/4 angle</option><option value="front">Front</option><option value="side">Side</option><option value="top">Top</option></select>
   <label class="ix3d-inline ix-wire">Wireframe <input id="ix3d-wireframe" type="checkbox"></label></div>
 </div>
 <div class="twin-layout ix-studio-layout">
 <div class="twin-stage ix-studio-stage">
   <div class="ix3d-hud"><span class="ix3d-kicker">BMW E30 · INTERACTIVE REFERENCE</span><strong id="ix-stage-heading">3D VIEW</strong><span id="ix3d-status">Checking reference assets…</span></div>
   <div id="ix3d-stage" class="ix3d-stage" aria-label="Interactive 3D viewer"></div>
   <p id="ix3d-fallback" class="ix3d-fallback" hidden></p>
   <svg id="twin-canvas" viewBox="0 0 1000 560" hidden aria-hidden="true"></svg>
   <section id="twin-diagram-panel" class="twin-diagram-panel ix-oem-instage" hidden>
      <div class="ix-drawing-head"><div><div class="ix-eyebrow">BMW ORIGINAL PARTS CATALOG</div><h3 id="twin-diagram-title">OEM drawing</h3><p id="twin-diagram-meta" class="small">Exploded parts and original identifiers</p></div><span class="ix-drawing-chip">2D · DOCUMENTED</span></div>
      <div id="twin-diagram-body"></div>
   </section>
   <div class="ix-stage-foot"><span id="twinvisualstatus">Preparing model…</span><span>Reference only · fitment requires evidence</span></div>
 </div>
 <aside id="twin-inspector" class="twin-inspector ix-studio-inspector">
   <div class="ix-eyebrow">INSPECTION / NAVIGATION</div><h3>Systems & assemblies</h3>
   <label class="ix3d-system-field">BMW catalog system<select id="ix3d-system-select"><option value="">Choose a subsystem</option></select></label>
   <p class="info">Pick a system to inspect its available original drawings and part numbers. The 3D reference is not used to establish fitment.</p>
   <div id="ix3d-selection-info" hidden class="ix-mesh-selection"><strong>Selected reference mesh</strong><p id="ix3d-mesh-name"></p></div>
   <div id="twin-system-list" class="ix-system-details"></div>
   <details class="ix3d-advanced"><summary>Use another licensed 3D model</summary><input id="ix3d-local-model" type="file" accept=".glb,.gltf"><p class="info">Only geometry you have permission to use. No automatic OEM identification.</p></details>
 </aside>
 </div>`;
 $('twin').prepend(panel);
 $('twinreset').onclick=()=>window.ixStudio3D?.reset();
 $('twin2d').onclick=()=>activate2DFallback(false);
 $('ix-mode-3d').onclick=async()=>{
   const status=await api('/api/3d/status');
   if(!status.ready){const s=$('ix3d-fallback');s.hidden=false;s.textContent='3D asset kit is not installed. Showing the available OEM drawing.';return;}
   $('twin-diagram-panel').hidden=true;$('ix3d-stage').hidden=false;$('ix-mode-3d').classList.add('active');$('twin2d').classList.remove('active');
   if(window.ixStudio3D&&window.visualTwinData)await window.ixStudio3D.mount(window.visualTwinData);
 };
 $('ix-view-select').onchange=e=>document.querySelector(`[data-ix3d-view="${e.target.value}"]`)?.click()||window.ixStudio3D?.positionView?.(e.target.value);
}
const VISUAL_LAYOUT={engine:[165,260,150,62],radiator:[105,177,120,48],fuel_preparation_system:[225,176,126,44],fuel_supply:[260,348,118,42],exhaust_system:[154,386,145,42],manual_transmission:[360,258,155,58],clutch:[350,343,120,40],gearshift:[442,197,105,38],pedals:[285,136,92,34],transfer_box_electric_gearbox:[525,258,164,58],drive_shaft:[670,270,145,34],front_axle:[815,224,112,46],rear_axle:[780,395,112,46],steering:[795,151,112,40],wheels:[790,305,116,40],brakes:[715,344,102,40],vehicle_electrical_system:[555,126,145,38],engine_electrical_system:[132,126,155,38],lighting:[65,105,90,34],instruments_measuring_systems:[370,108,180,36],heater_and_air_conditioning:[570,192,170,36]};
function visualShort(s){return s.replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function twinNode(svg,system){const p=VISUAL_LAYOUT[system.id]||[40,430,120,38],ns='http://www.w3.org/2000/svg',g=document.createElementNS(ns,'g');g.classList.add('twin-node');g.dataset.system=system.id;g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label',system.label);const r=document.createElementNS(ns,'rect');r.setAttribute('x',p[0]);r.setAttribute('y',p[1]);r.setAttribute('width',p[2]);r.setAttribute('height',p[3]);r.setAttribute('rx','12');g.append(r);const t=document.createElementNS(ns,'text');t.setAttribute('x',p[0]+10);t.setAttribute('y',p[1]+21);t.textContent=visualShort(system.id);g.append(t);const sub=document.createElementNS(ns,'text');sub.setAttribute('x',p[0]+10);sub.setAttribute('y',p[1]+40);sub.classList.add('twin-node-sub');sub.textContent=`${system.assembly_count} assemblies · ${system.mission_count} missions`;g.append(sub);g.onclick=()=>selectVisualSystem(system);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectVisualSystem(system)}};svg.append(g)}
function renderVisualTwin(d){window.visualTwinData=d;ensureVisualTwinUI();const svg=$('twin-canvas'),ns='http://www.w3.org/2000/svg';svg.replaceChildren();const defs=document.createElementNS(ns,'defs');defs.innerHTML='<linearGradient id="bodygrad" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#d8e7ef"/><stop offset="1" stop-color="#7d9caf"/></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="8" stdDeviation="9" flood-opacity=".22"/></filter>';svg.append(defs);const body=document.createElementNS(ns,'path');body.setAttribute('d','M80 198 L170 152 L760 152 L910 205 L954 358 L895 431 L140 431 L58 350 Z');body.setAttribute('fill','url(#bodygrad)');body.setAttribute('stroke','#3e6176');body.setAttribute('stroke-width','5');body.setAttribute('filter','url(#shadow)');body.setAttribute('opacity','.63');svg.append(body);const roof=document.createElementNS(ns,'path');roof.setAttribute('d','M280 154 L360 88 L650 88 L760 154 Z');roof.setAttribute('fill','#b8d0dc');roof.setAttribute('stroke','#52788c');roof.setAttribute('stroke-width','4');roof.setAttribute('opacity','.75');svg.append(roof);for(const [cx,cy] of [[170,410],[830,410],[170,210],[830,210]]){const w=document.createElementNS(ns,'ellipse');w.setAttribute('cx',cx);w.setAttribute('cy',cy);w.setAttribute('rx','54');w.setAttribute('ry','30');w.setAttribute('fill','#263a48');w.setAttribute('stroke','#9cb5c2');w.setAttribute('stroke-width','5');svg.append(w)}for(const system of d.systems)twinNode(svg,system);const menu=$('ix3d-system-select');if(menu){menu.replaceChildren(new Option('Choose an iX system',''));for(const system of d.systems)menu.add(new Option(system.label+' · '+system.assembly_count+' assemblies',system.id));menu.onchange=()=>{const match=d.systems.find(x=>x.id===menu.value);if(match){selectVisualSystem(match);if(!$('ix3d-stage')?.offsetParent)loadVisualAssemblies(match,{autoOpen:true});}};}$('twinvisualstatus').textContent=`${d.systems.length} catalog systems mapped · visual reference (not iX CAD)`;$('twin-system-list').replaceChildren(text('p','Choose a system to explore real catalog assemblies.','info'))}
let activeVisualSystem=null;
async function selectVisualSystem(system){activeVisualSystem=system;ensureVisualTwinUI();const systemSelect=$('ix3d-system-select');if(systemSelect)systemSelect.value=system.id;for(const n of $('twin-canvas').querySelectorAll('.twin-node'))n.classList.toggle('selected',n.dataset.system===system.id);window.ixStudio3D?.selectSystem(system.id);const root=$('twin-system-list');root.replaceChildren(text('h3',system.label),text('p',`${system.domain_label} · ${system.priority} · ${system.assembly_count} catalog assemblies`,'info'),text('p',system.mission_count?`${system.mission_count} persistent mission(s) already linked.`:'No persistent mission linked yet.','info'),text('div','Use the catalog and 2D fallback for exact callouts; the 3D view does not assert dimensions or fitment.','risk'));const open=text('button','Open 2D diagram fallback');open.onclick=()=>loadVisualAssemblies(system);root.append(open);const mission=text('button','Open restoration mission');mission.className='light';mission.onclick=()=>{tab('garage');const domain=$('missiondomain');if(domain&&restorationDomains.length){const d=restorationDomains.find(d=>d.groups?.some(g=>g.group_name===system.id));if(d){domain.value=d.id;syncMissionSystems()}}const s=$('missionsystem');if(s)s.value=system.id};root.append(mission)}
async function loadVisualAssemblies(system,{autoOpen=false}={}){
 const panel=$('twin-diagram-panel');panel.hidden=false;
 $('twin-diagram-title').textContent=visualShort(system.id)+' · factory catalog drawings';
 $('twin-diagram-meta').textContent='BMW catalog diagrams and numbered callouts; drawings are illustrative and do not certify installed 325iX fitment.';
 const body=$('twin-diagram-body');body.replaceChildren(text('p','Loading local catalog assemblies…','info'));
 try{
   const d=await api('/api/search?group='+encodeURIComponent(system.id));body.replaceChildren();
   if(!d.results?.length){body.append(text('p','No indexed assembly for this system. Use Parts & drawings for broader search.','risk'));return}
   const list=text('div',null,'visual-assembly-list');
   const detail=text('section',null,'visual-diagram-detail');detail.id='visual-diagram-detail';
   const assemblies=d.results.slice(0,30);
   for(const a of assemblies){
      const card=text('button',visualShort(a.slug||a.title||'Assembly')+' · '+a.part_count+' rows','light');
      card.className='visual-assembly';card.onclick=()=>loadVisualAssembly(a.id||a.assembly_id);
      list.append(card);
   }
   body.append(text('p',`${d.results.length} catalog assemblies. Select one to view its original drawing and OEM callouts.`, 'info'),list,detail);
   if(autoOpen){
      detail.append(text('p','Finding a locally available original drawing…','info'));
      // The RC14 package contains a partial V4 media cache. Prefer an actually present drawing;
      // do not pretend that every catalog figure was bundled.
      let best=assemblies[0],found=false;
      for(const a of assemblies){
        try{const candidate=await api('/api/assembly?id='+encodeURIComponent(a.id||a.assembly_id));
          if(candidate.figures?.some(f=>f.local_available===true)){best=a;found=true;break;}
        }catch(_error){/* Keep working through the other indexed assemblies. */}
      }
      await loadVisualAssembly(best.id||best.assembly_id);
      if(!found)detail.prepend(text('p','No local image cached for this system. Catalog callouts and original-source links remain available.','risk'));
   }else detail.append(text('p','Choose an assembly above to inspect its diagrams and numbered callouts.','info'));
 }catch(e){body.replaceChildren(text('p','2D catalog could not load: '+e.message,'risk'))}
}
async function loadVisualAssembly(id){
 const target=$('visual-diagram-detail')||$('twin-diagram-body');
 target.replaceChildren(text('p','Loading assembly drawing and callouts…','info'));
 try{
  const d=await api('/api/assembly?id='+encodeURIComponent(id));target.replaceChildren();
  const wrap=text('div',null,'visual-diagram-wrap');
  const figure=(d.figures||[]).find(f=>f.local_available===true)||d.figures?.[0];
  const media=text('div',null,'visual-diagram-media');
  if(figure){
    if(figure.local_available===true){
      const img=document.createElement('img');img.className='visual-diagram-image';img.alt='BMW OEM catalog exploded drawing. Callout image coordinates not yet verified.';
      img.src='/api/diagram?asset='+encodeURIComponent(figure.image_asset_id);
      img.onerror=()=>{img.remove();media.prepend(text('p','The image file could not be loaded from the local cache.','risk'))};
      media.append(img);
    }else media.append(text('p','The drawing is indexed but the image file is not in this preview. The numbered parts and original source are still available.','risk'));
    if(figure.figure_url)media.append(link('Open original catalog drawing',figure.figure_url));
  }else media.append(text('p','This assembly has no linked drawing. Use the verified part records below.','risk'));
  const rail=text('div',null,'visual-callout-rail');
  rail.append(text('h4',(d.assembly.slug||d.assembly.title||'Assembly').replaceAll('_',' ')),text('p',d.scope,'info'));
  for(const p of d.parts||[]){
   const b=text('button',`Callout ${p.callout_position||'?'} · ${p.part_number||'number not recorded'} · ${p.description||'description unavailable'}`,'light');
   b.onclick=()=>selectVisualPart(p,d.assembly);rail.append(b);
  }
  wrap.append(media,rail);target.append(wrap);
 }catch(e){target.replaceChildren(text('p','Assembly could not load: '+e.message,'risk'))}
}
async function activate2DFallback(scroll=false,reason=''){
 ensureVisualTwinUI();
 $('ix3d-stage').hidden=true;
 $('twin-canvas').setAttribute('hidden',''); // The old label map is not the fallback.
 $('twin-diagram-panel').hidden=false;
 $('ix-mode-3d').classList.remove('active');$('twin2d').classList.add('active');
 $('ix-stage-heading').textContent='ORIGINAL BMW DRAWINGS';
 const note=$('ix3d-fallback');note.hidden=!reason;note.textContent=reason?('3D is not available on this installation. '+(reason.includes('3D setup')?'Install the 3D asset kit to enable it; showing original catalog drawings.':'Showing original catalog drawings.')):'';
 const d=window.visualTwinData;
 if(!d?.systems?.length){$('twinvisualstatus').textContent='Catalog unavailable';return;}
 const preferred=activeVisualSystem||d.systems.find(s=>s.id==='front_axle'&&s.assembly_count>0)||d.systems.find(s=>s.assembly_count>0)||d.systems[0];
 $('twinvisualstatus').textContent=`OEM drawing mode · ${d.systems.length} catalog systems`;
 await selectVisualSystem(preferred);
 await loadVisualAssemblies(preferred,{autoOpen:true});
 if(scroll)$('visualtwin').scrollIntoView({behavior:'smooth',block:'start'});
}
function selectVisualPart(p,assembly){const root=$('twin-system-list');root.replaceChildren(text('h3',p.description||'Selected catalog part'),text('p',`${p.part_number||'OEM number not recorded'} · callout ${p.callout_position||'?'} · ${assembly.slug||assembly.title}`,'title'),text('p','Catalog identity is linked. Installed identity, variant fitment and condition still require evidence.','risk'));const b=text('button','Open full part dossier');b.onclick=()=>{tab('lookup');openPart(p.id)};root.append(b)}
let ixStudioLoading=null;
window.ixSelectVisualSystemById=id=>{const s=window.visualTwinData?.systems?.find(x=>x.id===id);if(s)selectVisualSystem(s)};
async function loadVisualTwin(){
 ensureVisualTwinUI();
 try{
  const d=await api('/api/visual/twin');renderVisualTwin(d);
  // Check the complete local import graph before importing any Three.js module.
  // A failed nested import otherwise manifests misleadingly as "Failed to fetch viewer3d.js".
  let status;
  try{status=await api('/api/3d/status')}catch(e){status={ready:false,missing:['3D status endpoint: '+e.message]}}
  if(!status.ready){
    const missing=(status.missing||[]).map(s=>s.split('/').pop()).join(', ');
    await activate2DFallback(false,'3D setup incomplete: '+(missing||'required assets not installed')+'. Run python3 scripts/prepare_3d_assets.py in Terminal, then refresh.');
    return;
  }
  if(!ixStudioLoading)ixStudioLoading=import('/viewer3d.js').then(m=>{window.ixStudio3D=m;return m});
  try{const studio=await ixStudioLoading;if(studio)await studio.mount(d)}catch(e){
    ixStudioLoading=null;
    await activate2DFallback(false,'3D module failed to load: '+(e?.message||e));
  }
 }catch(e){
  $('twinvisualstatus').textContent='Visual twin unavailable: '+e.message;
  $('twinvisualstatus').className='risk';
 }
}
