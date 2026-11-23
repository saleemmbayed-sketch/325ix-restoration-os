'use strict';
const $=id=>document.getElementById(id);
let activeAssembly=null, currentJob=null, allGroups=[], restorationDomains=[], livingMission=null, lastMissionAI=null;
let uiLanguage=localStorage.getItem('325ix-ui-language')||'en';
const text=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==undefined&&value!==null)e.textContent=String(value);if(cls)e.className=cls;return e};
const link=(label,url)=>{const a=text('a',label);if(url&&(/^https:\/\//.test(url)||/^\/api\/job\/\d+\.md$/.test(url))){a.href=url;a.target='_blank';a.rel='noopener noreferrer'}return a};
async function api(path,opts={}){const next={...opts};if((opts.method||'GET').toUpperCase()!=='GET')next.headers={...(opts.headers||{}),'X-Workbench-Request':'same-origin'};const r=await fetch(path,next);const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function fail(e){alert('Workbench: '+(e.message||e))}
const workspaces={
 garage:['Overview','Your restoration workspace','One place to pick up any repair','+ New mission'],
 twin:['Vehicle explorer','Explore the car','Select a system to see its assemblies and evidence','Find a system'],
 lookup:['Parts & drawings','Find the correct component','Search OEM numbers, drawings and verified catalog references','Search parts'],
 guide:['Diagnostics','Understand the problem','Start with what you can observe; document every test','Start inspection'],
 jobs:['Work orders','Document workshop work','Inspections, evidence, checkpoints and repair status','New inspection'],
 chat:['AI mechanic','Ask the mechanic','Answers require sourced evidence and physical verification','Ask a question'],
 mission:['Restoration mission','Continue your restoration','Keep the selected component and all recorded evidence together','← Overview'],
 expert:['Front axle pilot','Guided front-axle inspection','Structured workshop evidence from one specialist workflow','Start inspection'],
 manuals:['Evidence library','Find technical evidence','Trace procedures to authorized documents and actual pages','Search evidence'],
 program:['Research operations','Catalog research','Monitor exact-number reviews and unresolved conflicts','View batch'],
 sources:['Source registry','Source and license register','Separate actual examined evidence from discovery leads','Overview']
};
const VISUAL_CONTEXT_KEY='325ix-visual-context-v1';
const VISUAL_MODES=new Set(['hosted','local-3d','oem','personal','mechanical']);
const MECHANICAL_SCENES=new Set(['ix_m20_engine_bay','ix_front_axle_workshop','ix_awd_driveline_workshop']);
function safeContextId(value){const id=String(value??'');return /^[A-Za-z0-9_-]{1,96}$/.test(id)?id:''}
function defaultVisualContext(){return {version:1,workspace:'garage',mode:'',system_id:'',assembly_id:'',part_id:'',scene:'',component_id:'',candidate_id:'',candidate_assembly_id:'',slot:'',mission_job_id:'',front_play_job_id:''}}
function readVisualContext(){
 const defaults=defaultVisualContext();
 try{
  const raw=JSON.parse(localStorage.getItem(VISUAL_CONTEXT_KEY)||'null');if(!raw||raw.version!==1)return defaults;
  if(Object.prototype.hasOwnProperty.call(workspaces,raw.workspace))defaults.workspace=raw.workspace;
  if(VISUAL_MODES.has(raw.mode))defaults.mode=raw.mode;
  for(const key of ['system_id','assembly_id','part_id','component_id','candidate_id','candidate_assembly_id','slot'])defaults[key]=safeContextId(raw[key]);
  if(MECHANICAL_SCENES.has(raw.scene))defaults.scene=raw.scene;
  for(const key of ['mission_job_id','front_play_job_id']){const value=String(raw[key]??'');defaults[key]=value.length>0&&value.length<=10&&Array.from(value).every(ch=>ch>='0'&&ch<='9')?value:'';}
 }catch(_){/* Browser storage is optional; server-side jobs remain authoritative. */}
 return defaults;
}
let visualContext=readVisualContext();
function saveVisualContext(patch={}){
 const next={...visualContext,...patch,version:1};
 if(!Object.prototype.hasOwnProperty.call(workspaces,next.workspace))next.workspace=visualContext.workspace||'garage';
 if(!VISUAL_MODES.has(next.mode))next.mode='';
 for(const key of ['system_id','assembly_id','part_id','component_id','candidate_id','candidate_assembly_id','slot'])next[key]=safeContextId(next[key]);
 if(!MECHANICAL_SCENES.has(next.scene))next.scene='';
 for(const key of ['mission_job_id','front_play_job_id']){const value=String(next[key]??'');next[key]=value.length>0&&value.length<=10&&Array.from(value).every(ch=>ch>='0'&&ch<='9')?value:'';}
 visualContext=next;
 try{localStorage.setItem(VISUAL_CONTEXT_KEY,JSON.stringify(next))}catch(_){/* Private browsing may deny persistence. */}
 return next;
}
let activeWorkspace='garage';
function tab(name,{fromHistory=false}={}){
 if(!document.getElementById(name)?.classList.contains('page'))return;
 activeWorkspace=name;saveVisualContext({workspace:name});
 for(const b of document.querySelectorAll('.tab')){
  const current=b.dataset.tab===name;
  b.classList.toggle('active',current);
  if(current)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
 }
 for(const page of document.querySelectorAll('.page'))page.hidden=page.id!==name;
 const info=workspaces[name]||workspaces.garage;
 $('workspace-breadcrumb').textContent='325iX / '+info[0];
 $('workspace-title').textContent=info[1];
 $('workspace-subtitle').textContent=info[2];
 $('context-quick-action').textContent=info[3];
 document.title=info[1]+' · BMW 325iX Restoration OS';
 const advanced=document.querySelector('.ix-nav-more');
 if(advanced?.querySelector('.tab.active'))advanced.open=true;
 document.body.classList.remove('ix-nav-open');$('nav-toggle')?.setAttribute('aria-expanded','false');
 if(/^https?:$/.test(location.protocol)&&location.hash.slice(1)!==name){
  const url=location.pathname+location.search+'#'+name;
  if(fromHistory)history.replaceState({workspace:name},'',url);else history.pushState({workspace:name},'',url);
 }
 if(name==='garage')loadGarage();if(name==='jobs')loadJobs();if(name==='sources')loadSources();if(name==='chat')loadAIStatus();if(name==='twin'){loadTwin();loadVisualTwin()}
 window.scrollTo({top:0,behavior:'instant'});
}
window.addEventListener('popstate',()=>{const name=location.hash.slice(1);if(Object.prototype.hasOwnProperty.call(workspaces,name))tab(name,{fromHistory:true})});
for(const b of document.querySelectorAll('.tab'))b.addEventListener('click',()=>tab(b.dataset.tab));
function openMissionCreate(){tab('garage');const panel=$('mission-create');panel.open=true;panel.scrollIntoView({block:'center',behavior:'smooth'});$('missionsymptom').focus({preventScroll:true})}
for(const button of document.querySelectorAll('[data-route]'))button.addEventListener('click',()=>tab(button.dataset.route));
$('open-new-mission').addEventListener('click',openMissionCreate);
$('nav-toggle').addEventListener('click',()=>{document.body.classList.toggle('ix-nav-open');$('nav-toggle').setAttribute('aria-expanded',String(document.body.classList.contains('ix-nav-open')))});
$('context-quick-action').addEventListener('click',()=>{
 switch(activeWorkspace){
  case 'garage':openMissionCreate();break;
  case 'lookup':$('search').focus();break;
  case 'twin':$('ix-system-finder')?.focus();break;
  case 'guide':$('guidesymptom').focus();break;
  case 'jobs':$('symptom').focus();break;
  case 'chat':$('aiquestion').focus();break;
  case 'mission':tab('garage');break;
  case 'expert':$('expertsymptom').focus();break;
  case 'manuals':$('manualq').focus();break;
  case 'program':$('loadbatch').click();break;
  default:tab('garage');
 }
});
$('quick-find').addEventListener('submit',e=>{
 e.preventDefault();const query=$('quick-query').value.trim();
 if(!query)return;$('search').value=query;$('group').value='';tab('lookup');search();
});
document.addEventListener('keydown',e=>{
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('quick-query').focus();$('quick-query').select()}
 if(e.key==='Escape'){document.body.classList.remove('ix-nav-open');$('nav-toggle').setAttribute('aria-expanded','false');if(document.activeElement===$('quick-query'))$('quick-query').blur()}
});

function applyUiLanguage(){document.documentElement.dir=uiLanguage==='ar'?'rtl':'ltr';document.documentElement.lang=uiLanguage;$('uilang').textContent=uiLanguage==='ar'?'AR':'EN';$('language-toggle').setAttribute('aria-pressed',uiLanguage==='ar'?'true':'false')}
if($('language-toggle')){$('language-toggle').addEventListener('click',()=>{uiLanguage=uiLanguage==='ar'?'en':'ar';localStorage.setItem('325ix-ui-language',uiLanguage);applyUiLanguage()});applyUiLanguage()}
function syncMissionSystems(){const domain=restorationDomains.find(x=>x.id===$('missiondomain').value),select=$('missionsystem');select.replaceChildren();for(const g of domain?.groups||[]){const o=document.createElement('option');o.value=g.group_name;o.textContent=g.group_name.replaceAll('_',' ')+' · '+g.assemblies+' assemblies';select.append(o)}if(domain?.default_system)select.value=domain.default_system}
async function loadGarage(){
 try{
  const [coverage,missions]=await Promise.all([api('/api/restoration/domains'),api('/api/missions')]);
  restorationDomains=coverage.domains||[];
  const domainSelect=$('missiondomain'),selected=domainSelect.value;
  domainSelect.replaceChildren();
  for(const d of restorationDomains){const option=new Option(d.priority+' · '+d.label,d.id);domainSelect.add(option)}
  if(selected&&restorationDomains.some(d=>d.id===selected))domainSelect.value=selected;
  syncMissionSystems();
  const systems=new Set(restorationDomains.flatMap(d=>(d.groups||[]).map(g=>g.group_name)));
  const assemblies=allGroups.length?allGroups.reduce((sum,g)=>sum+Number(g.assemblies||0),0):restorationDomains.reduce((sum,d)=>sum+Number(d.assembly_count||0),0);
  const missionsList=missions.missions||[];
  $('garage-metrics').replaceChildren(...[
   [systems.size||21,'Mapped systems'],
   [assemblies.toLocaleString(),'Indexed assemblies'],
   [missionsList.length,'Documented missions'],
   ['Not approved','Road clearance']
  ].map(([number,label])=>{const tile=text('div',null,'ix-metric');tile.append(text('strong',number),text('span',label));return tile}));
  const cards=$('domaincards');cards.replaceChildren();
  for(const d of restorationDomains){
   const card=text('button',null,'domaincard');card.type='button';
   card.append(text('div',d.priority+' · '+d.label,'title'),text('p',d.promise),
    text('div',`${d.assembly_count} assemblies · ${d.mission_count} missions`,'code'));
   card.addEventListener('click',()=>{
    tab('lookup');const group=$('group');
    if(d.default_system)group.value=d.default_system;
    $('search').value='';search();
   });cards.append(card)
  }
  const list=$('missionlist');list.replaceChildren();
  if(!missionsList.length){
   const empty=text('div',null,'ix-empty-mission');
   empty.append(text('strong','No restoration missions started'),text('p','Your first documented repair will appear here, with its history and next steps.'));
   const b=text('button','Start a mission','light');b.onclick=openMissionCreate;empty.append(b);list.append(empty)
  }
  for(const m of missionsList){
   const row=text('article',null,'ix-mission-row');
   const top=text('div',null,'ix-mission-head');top.append(text('strong','IX-'+String(m.job_id).padStart(4,'0')+' · '+m.domain_label),text('span',m.mission_status||'ACTIVE','ix-mission-status'));
   row.append(top,text('p',m.symptom),text('div',`${m.system.replaceAll('_',' ')} · ${m.risk} · safety ${m.clearance}`,'info'));
   const resume=text('button','Resume →','light');resume.onclick=()=>resumeMission(m);row.append(resume);list.append(row)
  }
 }catch(e){$('missionlist').replaceChildren(text('p','Garage unavailable: '+e.message,'risk'))}
}
async function resumeMission(m){currentJob=m.job_id;livingMission=m;saveVisualContext({mission_job_id:m.job_id,workspace:'mission'});tab('mission');await loadLivingMission(m)}
async function loadLivingMission(m){
 const jobId=m.job_id;saveVisualContext({mission_job_id:jobId});const root=$('livingmissionevidence');root.replaceChildren(text('p','Loading connected mission evidence…','info'));
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
function presentResult(x){
 const c=text('article',null,'item ix-part-result');
 c.append(text('div',x.group_name?.replaceAll('_',' '),'group'));
 if(x.part_number)c.append(text('div',x.part_number,'partnum'));
 c.append(text('div',x.description||x.slug?.replaceAll('_',' ')||'Assembly','desc'));
 if(x.callout_position)c.append(text('div',`Callout ${x.callout_position} · Qty ${x.quantity_raw||'?'} · ${x.date_condition_raw||'Date not stated'}`,'info'));
 if(x.part_count!==undefined)c.append(text('div',`${x.part_count} catalog rows`,'info'));
 const actions=text('div',null,'actions');const btn=text('button','Open parts & diagram');btn.addEventListener('click',()=>openAssembly(x.assembly_id||x.id));actions.append(btn);
 if(x.anchor)actions.append(document.createTextNode('  '),link('Catalog row',x.anchor));c.append(actions);
 const variants=x.occurrences||[];
 if(variants.length>1){
  const details=document.createElement('details');details.className='ix-occurrences';
  const summary=document.createElement('summary');summary.textContent=variants.length+' catalog occurrences — review applicability';details.append(summary);
  const list=text('div',null,'ix-occurrence-list');
  for(const row of variants){
   const item=text('button',null,'ix-occurrence');item.type='button';
   item.append(text('span',(row.slug||'Assembly').replaceAll('_',' ')),text('small',`#${row.callout_position||'?'} · ${row.date_condition_raw||'no date condition'}`));
   item.onclick=()=>openAssembly(row.assembly_id||row.id);list.append(item)
  }
  details.append(list);c.append(details)
 }
 return c;
}
async function search(){
 const q=$('search').value.trim(),g=$('group').value;
 if(!q&&!g){$('results').replaceChildren();$('searchmeta').textContent='Enter a term or select a system.';return}
 $('searchmeta').textContent='Searching local catalog…';
 try{
  const d=await api('/api/search?q='+encodeURIComponent(q)+'&group='+encodeURIComponent(g));
  const rows=d.results||[],unique=new Map();
  for(const row of rows){
   // Preserve every exact catalog occurrence; group visually by BMW part number only.
   const key=row.part_number||row.assembly_id||row.id;
   if(!unique.has(key))unique.set(key,{...row,occurrences:[]});
   unique.get(key).occurrences.push(row)
  }
  $('searchmeta').textContent=rows.length===unique.size?`${rows.length} matches · ${d.scope||''}`:`${unique.size} distinct results across ${rows.length} catalog occurrences · expand a result to inspect dates and variants`;
  const frag=document.createDocumentFragment();for(const row of unique.values())frag.append(presentResult(row));$('results').replaceChildren(frag);
  if(!rows.length)$('results').append(text('p','No matching records. Try a broader keyword or change system.'));
 }catch(e){fail(e)}
}
$('searchbtn').addEventListener('click',search);$('search').addEventListener('keydown',e=>{if(e.key==='Enter')search()});$('group').addEventListener('change',search);
function addPartsTable(parts){const tbody=$('partstable').querySelector('tbody');tbody.replaceChildren();for(const p of parts){const tr=text('tr');tr.className='partrow';tr.title='Click to inspect this component';tr.tabIndex=0;tr.addEventListener('click',e=>{if(e.target.tagName!=='A')openPart(p.id)});tr.addEventListener('keydown',e=>{if(e.key==='Enter')openPart(p.id)});for(const v of [p.callout_position,p.part_number,p.description,p.quantity_raw,p.date_condition_raw]){const td=text('td',v||'—');tr.append(td)}if(p.anchor){const a=link('Catalog',p.anchor);tr.lastChild.append(' ',a)}tbody.append(tr)}}
async function openAssembly(id){try{const d=await api('/api/assembly?id='+encodeURIComponent(id));activeAssembly=d.assembly;saveVisualContext({system_id:d.assembly.group_name,assembly_id:d.assembly.id,part_id:''});
 $('workspace-subtitle').textContent='Selected assembly: '+d.assembly.slug.replaceAll('_',' ')+' · '+d.parts.length+' catalog rows';
 $('detailtitle').textContent=d.assembly.slug.replaceAll('_',' ');$('detailmeta').replaceChildren(text('span',`${d.assembly.group_name} · ${d.parts.length} table rows · `),link('Original catalog page',d.assembly.source_url));
 const target=$('diagrams');target.replaceChildren();for(const f of d.figures){const fig=text('div',null,'diagram');const img=document.createElement('img');img.alt='Exploded diagram (unverified diagram pixel positions)';img.loading='lazy';img.src='/api/diagram?asset='+encodeURIComponent(f.image_asset_id);img.onerror=()=>{
  if(/^https:\/\/ills\.bmwfans\.info\/[a-z0-9-]+\.webp(?:\?.*)?$/.test(f.figure_url||'')){
    img.onerror=()=>{img.remove();fig.append(text('span','Drawing unavailable locally and from the original source.','info'))};
    img.src=f.figure_url;fig.append(text('div','Online source drawing (not an offline file).','info'));
  }else{img.remove();fig.append(text('span','Local drawing missing and remote reference unverified.','info'))}
};fig.append(img);const refs=text('div',null,'links');refs.append(text('div','Figure asset: '+f.image_asset_id,'info'),link('View original source image',f.figure_url));fig.append(refs);target.append(fig)}
 addPartsTable(d.parts);$('detailpanel').hidden=false;window.scrollTo({top:$('detailpanel').offsetTop-10,behavior:'smooth'});
}catch(e){fail(e)}}
$('clearassembly').addEventListener('click',()=>{$('detailpanel').hidden=true;activeAssembly=null;activePart=null;saveVisualContext({assembly_id:'',part_id:''})});
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
function v4StatusSummary(s){
 if(!s.connected)return s.catalog_assets?`V4 catalog references ${s.catalog_assets} image assets, but no local manifest/media root is connected. No binaries are assumed present.`:'V4 data is not connected locally. No diagram binaries are assumed present.';
 const verified=s.images_hash_verified??0,total=s.manifest_assets??s.assets_in_manifest??0,notes=[];
 if(s.images_missing_locally)notes.push(s.images_missing_locally+' reported downloads missing locally');
 if(s.images_sha256_mismatches)notes.push(s.images_sha256_mismatches+' SHA-256 mismatches');
 if(s.images_size_mismatches)notes.push(s.images_size_mismatches+' size mismatches');
 if(s.images_mime_mismatches)notes.push(s.images_mime_mismatches+' MIME/content mismatches');
 if(s.images_mime_unverifiable)notes.push(s.images_mime_unverifiable+' files with unverified MIME/content');
 if(s.images_size_unverifiable)notes.push(s.images_size_unverifiable+' files without expected byte counts');
 if(s.images_hash_unverifiable)notes.push(s.images_hash_unverifiable+' files without verifiable SHA-256');
 if(s.images_invalid_local_files)notes.push(s.images_invalid_local_files+' invalid local files');
 if(s.images_unsafe_paths)notes.push(s.images_unsafe_paths+' unsafe manifest paths');
 if(s.images_missing_manifest_paths)notes.push(s.images_missing_manifest_paths+' missing manifest paths');
 if(s.not_reported_downloaded_assets)notes.push(s.not_reported_downloaded_assets+' assets not reported downloaded');
 if(s.catalog_integrity==='MANIFEST_MISSING')notes.push('image manifest missing; '+(s.catalog_assets??0)+' catalog assets not reconciled');
 else if(['SCHEMA_MISMATCH','ERROR'].includes(s.catalog_integrity))notes.push('catalog/manifest reconciliation failed');
 else if(['NOT_CHECKED','NOT_CONNECTED'].includes(s.catalog_integrity))notes.push('catalog/manifest reconciliation not completed');
 else if(s.catalog_integrity==='MISMATCH')notes.push('catalog/manifest mismatch');
 if(s.catalog_asset_ids_missing_from_manifest)notes.push(s.catalog_asset_ids_missing_from_manifest+' catalog assets absent from manifest');
 if(s.manifest_asset_ids_missing_from_catalog)notes.push(s.manifest_asset_ids_missing_from_catalog+' manifest assets absent from catalog');
 if(s.catalog_metadata_mismatches)notes.push(s.catalog_metadata_mismatches+' catalog metadata mismatches');
 return `V4 image integrity ${s.integrity_status||'UNKNOWN'}: ${verified}/${total} files verified by expected size, SHA-256 and MIME/content${notes.length?' · '+notes.join(' · '):''}.`;
}
api('/api/v4/status').then(s=>{$('v4status').textContent=v4StatusSummary(s)}).catch(()=>{});

// V0.4 part-detail workspace: strictly separate drawing, photographed physical part, and evidence.
let activePart=null;
function fieldRow(k,v,status){const row=text('div',null,'factrow');const lab=text('div',k,'factlabel');const value=text('div',v===null||v===undefined||v===''?'Not verified / not supplied':v,'factvalue');const badge=text('span',status||'UNKNOWN','factstatus');row.append(lab,value,badge);return row}
async function openPart(id){
 try{
  const d=await api('/api/part-dossier?id='+encodeURIComponent(id));
  // Opening a part from the 3D viewer must also reveal its parent assembly.
  if(d.part.assembly_id&&($('detailpanel').hidden||activeAssembly?.id!==d.part.assembly_id))await openAssembly(d.part.assembly_id);
  activePart=d.part;saveVisualContext({system_id:d.part.group_name,assembly_id:d.part.assembly_id,part_id:d.part.id}); $('workspace-subtitle').textContent='Selected BMW part: '+(d.part.part_number||'number unknown')+' · '+(d.part.description||'Component')+' · verify variant before fitment';
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
    const badge=text('div','PART CALLOUT: '+(d.part.callout_position||'?')+' — exact pixel hotspot not verified · local drawing '+(fig.local_available?'verified':'not verified')+' ('+(fig.local_integrity_state||'unknown')+')','info');
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
  let actions=$('partworkflowactions');if(!actions){actions=text('div',null,'ix-part-workflow');actions.id='partworkflowactions';$('partscope').after(actions)}
  actions.replaceChildren();
  const work=text('button','Create inspection for this part');work.type='button';work.onclick=()=>{
   tab('jobs');$('jobgroup').value=d.part.group_name;
   $('symptom').value='Inspect '+(d.part.description||'component')+' (BMW '+(d.part.part_number||'unknown')+'); confirm actual condition and fitment';
   $('context').value='Catalog reference '+(d.part.slug||'')+'; part identity and installed geometry unverified.';
   $('jobassembly').textContent='Catalog assembly: '+(d.part.slug||'')+' · not yet verified on vehicle';$('symptom').focus();
  };
  const ask=text('button','Ask mechanic about this part','light');ask.type='button';ask.onclick=()=>{
   tab('chat');$('aigroup').value=d.part.group_name;
   $('aiquestion').value='For BMW part '+(d.part.part_number||'?')+' ('+(d.part.description||'component')+'), list verified facts, applicability uncertainties, inspection evidence required, and repair-first options. Do not assume fitment.';
   $('aiquestion').focus();
  };
  actions.append(work,ask);
  $('partdossier').hidden=false;$('partdossier').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){fail(e)}
}
$('closepart').addEventListener('click',()=>{$('partdossier').hidden=true;activePart=null});
$('partphoto-add').addEventListener('click',async()=>{
 const f=$('partphoto-file').files[0];const label=$('partphoto-source').value.trim();
 if(!activePart||!activePart.part_number)return alert('Choose a part with a catalog number first');
 if(!f||!label)return alert('Select a file and enter who supplied the photograph');
 if(f.size>2800000)return alert('Please reduce photo size to 2.8 MB or less');
 const upload=$('partphoto-add');upload.disabled=true;$('partphoto-result').textContent='Saving owner-provided image locally…';
 try{
  const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Cannot read photo'));reader.readAsDataURL(f)});
  await api('/api/part-photo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({part_number:activePart.part_number,kind:$('partphoto-type').value,source_label:label,source_url:$('partphoto-url').value.trim(),filename:f.name,image_base64:encoded})});
  $('partphoto-result').textContent='Image saved locally with provenance. Image identity and vehicle fitment remain unverified.';
  const id=activePart.id;await openPart(id);
 }catch(e){$('partphoto-result').textContent=e.message}finally{upload.disabled=false}
});

api('/api/evidence/coverage').then(s=>{const el=document.createElement('div');el.className='meta';el.textContent=`Live source-reviewed exact-number records: ${s.researched_exact_part_numbers} (VIN fitment not approved); ${s.supplier_image_reference_count} external supplier image references (not installed-part photos); ${s.alternative_photo_reference_count} alternative image references; ${s.owner_uploaded_workshop_actual_part_photo_count} owner-uploaded workshop actual-part photos (identity unverified). `+$('v4status').textContent;$('v4status').replaceWith(el);el.id='v4status'}).catch(()=>{});

// V0.6 full catalog research program; independent from parts catalog and job DB.
let lastProgramBatch=0;
async function loadProgramCoverage(){
 try{
  const s=await api('/api/catalog/coverage');
  $('catalogcoverage').textContent=`Catalog: ${s.unique_part_numbers} distinct OEM numbers / ${s.catalog_rows} ETK rows / ${s.assemblies} assemblies / ${s.unique_diagram_assets} drawings. `+
   `Source-reviewed (fitment unverified): ${s.researched_exact_number_records}. Pending source review: ${s.unique_part_numbers-s.researched_exact_number_records}. `+
   `External supplier image references (not installed-part photos): ${s.supplier_image_reference_count}. Offline independently verified product photos: ${s.offline_individual_product_photos_verified}. `+
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
  $('expertv4').textContent=v4StatusSummary(expertDefinition.v4);
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
  for(const p of expertDefinition.parts){
   const card=text('div',null,'source');card.append(text('strong',p.number+' · '+p.label),
    text('p',p.source_reviewed?'Source-reviewed exact-number record; fitment still unverified':'Original catalog only; source review pending','info'),
    text('p','Raw catalog wording and callout are candidate evidence only. Verify variant, side, installed markings and actual hardware independently.','risk'));
   if(p.rows.length){
    for(const occurrence of p.rows){
     card.append(text('p',`Catalog wording: ${occurrence.description||'not supplied'} · assembly ${occurrence.assembly_id} · callout ${occurrence.callout_position||'?'} · applicability ${occurrence.applicability||'not supplied'} · VIN fitment unverified.`,'meta'));
     const btn=text('button','Open this catalog occurrence','light');btn.addEventListener('click',async()=>{tab('lookup');await openAssembly(occurrence.assembly_id);await openPart(occurrence.id)});card.append(btn)
    }
   }else card.append(text('p','No matching catalog occurrence found; do not treat this number as a part match.','risk'));
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
  expertJobId=jobId;saveVisualContext({front_play_job_id:jobId,mission_job_id:jobId,workspace:'expert'});$('expertcasepanel').hidden=false;$('expertoverview').hidden=false;
  const overview=await api('/api/job/'+jobId+'/overview');const ov=$('expertoverview');ov.replaceChildren(text('h3','Case cockpit'),text('p',`Evidence items: ${overview.readiness.evidence_count} · Twin events: ${overview.twin_events.length} · Clearance: ${overview.readiness.clearance}`,'code'));
  const intake=overview.twin_events.find(x=>x.event_type==='CASE_CREATED')?.payload||{};
  const visual=intake.visual_reference,candidate=intake.catalog_candidate,assembly=intake.catalog_assembly;
  if(visual||candidate||assembly){
   const linked=text('section',null,'notice muted');linked.append(text('strong','Visual workshop handoff · reference only'));
   if(visual)linked.append(text('p',`3D locator: ${visual.component_label} · ${visual.system.replaceAll('_',' ')}. This is orientation geometry, not proof of the installed component.`,'info'));
   if(candidate)linked.append(text('p',`Catalog occurrence: ${candidate.part_number} · ${candidate.description}. ${candidate.source_reviewed_exact_number?'Exact-number source review exists;':'Source review not confirmed.'} Fitment and as-installed identity remain unverified.`,'info'));
   else if(assembly)linked.append(text('p',`Catalog assembly candidate: ${assembly.label}. Applicability and installed fitment remain unverified.`,'info'));
   const assemblyId=candidate?.assembly_id||assembly?.id||overview.job.assembly_id;
   if(assemblyId){const open=text('button',candidate?.id?'Open BMW drawing & part dossier':'Open BMW assembly drawing','light');open.type='button';open.addEventListener('click',async()=>{try{tab('lookup');await openAssembly(assemblyId);if(candidate?.id)await openPart(candidate.id)}catch(e){fail(e)}});linked.append(open)}
   ov.append(linked);
  }
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
 <div class="ix-mech-journey" id="ix-mech-journey" aria-label="Mechanical explorer">
  <div class="ix-mech-journey-title"><b>INSPECTION STUDIO</b><span>Open an assembly → choose a component → verify BMW evidence → save the repair</span></div>
  <div class="ix-scene-actions" id="ix-scene-actions">
   <button class="ix-scene-btn" data-mech-scene="ix_m20_engine_bay" type="button"><strong>01</strong> Open bonnet <small>M20 engine</small></button>
   <button class="ix-scene-btn" data-mech-scene="ix_front_axle_workshop" type="button"><strong>02</strong> Front axle <small>AWD / steering</small></button>
   <button class="ix-scene-btn" data-mech-scene="ix_awd_driveline_workshop" type="button"><strong>03</strong> AWD driveline <small>Transfer case</small></button>
  </div>
 </div>
 <div class="ix-studio-toolbar">
  <div class="ix-mode-tabs"><button id="ix-preview-sedan" class="ix-mode-btn" type="button">◈ E30 sedan 3D</button><button id="ix-mode-3d" class="ix-mode-btn active" type="button">Local 3D</button><button id="twin2d" class="ix-mode-btn" type="button">▤ OEM drawings</button></div>
  <div class="ix-studio-tools"><button type="button" id="ix-fullscreen" class="light">⛶ Full screen</button><button type="button" id="twinreset" class="light">Reset camera</button><label class="ix3d-explode-label" title="Deterministic, reversible hierarchical explosion driven by 0–1 factor">Explode assemblies <input type="range" id="ix3d-explode" min="0" max="100" step="1" value="0"><output id="ix3d-explode-value">0%</output></label>
   <select id="ix-explode-scope" aria-label="Assembly explosion target"><option value="">Whole vehicle</option></select>
   <button id="ix-explode-isolate" class="light" type="button" aria-pressed="false">Isolate</button>
   <button id="ix-explode-reset" class="light" type="button">Assemble</button>
   <button id="ix-alert-demo" class="light" type="button" title="Demonstrates programmatic alert control; not live telemetry">Demo alert</button>
   <select id="ix-view-select" aria-label="Camera angle"><option value="iso">3/4 angle</option><option value="front">Front</option><option value="side">Side</option><option value="top">Top</option></select>
   <label class="ix3d-inline ix-wire">Wireframe <input id="ix3d-wireframe" type="checkbox"></label></div>
 </div>
 <div class="twin-layout ix-studio-layout">
 <div id="ix-studio-stage" class="twin-stage ix-studio-stage">
   <div class="ix3d-hud"><span class="ix3d-kicker">BMW E30 · INTERACTIVE REFERENCE</span><strong id="ix-stage-heading">3D VIEW</strong><span id="ix3d-status">Checking reference assets…</span></div>
   <div id="ix3d-stage" class="ix3d-stage" aria-label="Interactive 3D viewer"></div>
   <div id="ix-mech-static" class="ix-mech-static" hidden><img id="ix-mech-preview" alt="Original rendered mechanical reference" /><div class="ix-mech-static-text">Full 3D engine, axle and AWD models are included. Install the free local Three.js kit to rotate and select their meshes.<br><strong>Run INSTALL_3D_ASSETS.command</strong></div></div>
   <div class="ix-mech-stage-controls" id="ix-mech-stage-controls" hidden>
    <span id="ix-mech-stage-label">ENGINE BAY</span>
    <button id="ix-bonnet-action" type="button">Close bonnet</button>
    <button id="ix-mech-exit" type="button">Back to car</button>
   </div>
   <div id="ix3d-hosted" class="ix3d-hosted" hidden>
     <div class="ix-hosted-banner"><strong>4-door E30 · FREE ONLINE REFERENCE</strong><a href="https://sketchfab.com/3d-models/bmw-3-series-e30-sedan-bd0925e21c934a9cbfdb30ccf5584e86" target="_blank" rel="noopener noreferrer">Open source model ↗</a></div>
     <iframe id="ix3d-hosted-frame" title="BMW E30 four-door 3D reference via Sketchfab" loading="lazy" allow="fullscreen; xr-spatial-tracking" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
     <p>Hosted public viewer requires internet. If the embed is blocked, use the source link. The local OEM catalog remains independent.</p>
   </div>
   <nav id="ix3d-regions" class="ix3d-regions" aria-label="3D inspection regions">
    <button type="button" data-ix-region="chassis" class="active">Chassis</button>
    <button type="button" data-ix-region="drivetrain">AWD / Drive</button>
    <button type="button" data-ix-region="engine">Engine</button>
    <button type="button" data-ix-region="electrical">Electrical / Cabin</button>
   </nav>
   <p id="ix3d-fallback" class="ix3d-fallback" hidden></p>
   <svg id="twin-canvas" viewBox="0 0 1000 560" hidden aria-hidden="true"></svg>
   <section id="twin-diagram-panel" class="twin-diagram-panel ix-oem-instage" hidden>
      <div class="ix-drawing-head"><div><div class="ix-eyebrow">BMW ORIGINAL PARTS CATALOG</div><h3 id="twin-diagram-title">OEM drawing</h3><p id="twin-diagram-meta" class="small">Exploded parts and original identifiers</p></div><span class="ix-drawing-chip">2D · DOCUMENTED</span></div>
      <div id="twin-diagram-body"></div>
   </section>
   <div class="ix-stage-foot"><span id="twinvisualstatus">Preparing model…</span><span>Approximate 3D zones · OEM numbers require catalog evidence</span></div>
 </div>
 <aside id="twin-inspector" class="twin-inspector ix-studio-inspector">
   <div class="ix-eyebrow">INSPECTION / NAVIGATION</div><h3>Systems & assemblies</h3>
   <section id="ix-mech-browser" class="ix-mech-browser" hidden>
    <span class="ix-eyebrow">SELECTABLE GEOMETRY</span>
    <h3 id="ix-mech-system-name">Mechanical assembly</h3>
    <p class="ix-mech-help">Select a modeled part to find matching catalog records. Dimensions and fitment come from evidence, not geometry.</p>
    <input id="ix-mech-part-filter" type="search" placeholder="Filter modeled components…" aria-label="Filter mechanical components">
    <div id="ix-mech-part-list" class="ix-mech-part-list"></div>
    <div id="ix-mech-component-detail" class="ix-mech-component-detail" aria-live="polite"></div>
   </section>
   <label class="ix3d-system-field">Active system<select id="ix3d-system-select"><option value="">Choose a system</option></select></label>
   <label class="ix-system-search-label" for="ix-system-finder">Explore all 21 systems</label>
   <input id="ix-system-finder" type="search" placeholder="Search engine, front axle, brakes…" autocomplete="off">
   <span id="ix-system-count" class="ix-system-count"></span>
   <div id="ix-system-results" class="ix-system-results" aria-label="Available vehicle systems"></div>
   <p class="info">3D markers locate reference zones; choose any system for its indexed OEM assemblies. Physical part identity and fitment require evidence.</p>
   <div id="ix3d-selection-info" hidden class="ix-mesh-selection"><strong>Selected reference mesh</strong><p id="ix3d-mesh-name"></p></div>
   <div id="twin-system-list" class="ix-system-details"></div>
   <section class="ix-personal-vault"><div class="ix-eyebrow">PERSONAL 3D ASSET LIBRARY</div>
    <p class="small">Attach a downloaded GLB or binary STL to the whole car or any of the 21 systems. Files remain local to this installation, never published.</p>
    <div id="ix-vault-status" class="info">Checking local models…</div>
    <button id="ix-view-system-model" type="button" class="light">Inspect saved model for this system</button>
    <label for="ix-model-slot">Assign model to</label><select id="ix-model-slot"><option value="body">Whole vehicle</option></select>
    <label for="ix3d-local-model">Select downloaded model · max 30 MB</label><input id="ix3d-local-model" type="file" accept=".glb,.stl">
    <label for="ix-model-source">Source or author (recommended)</label><input id="ix-model-source" placeholder="Original source link / author">
    <button id="ix-save-model" type="button">Save privately & inspect</button><p id="ix-model-message" class="info" role="status"></p>
   </section>
   <details class="ix3d-advanced"><summary>Free mechanical 3D references</summary>
      <p><a href="https://sketchfab.com/OsamaMaddani/collections/bmw-e30-5eea3c5286de4c58b7de7c2eb48597a5" target="_blank" rel="noopener noreferrer">1989 325iX strut / spindle scan · E30 collection</a></p>
      <p><a href="https://renn.design/products/e30-front-strut-3d-scan" target="_blank" rel="noopener noreferrer">Free E30 front strut sample · check availability and iX applicability</a></p>
      <p><a href="https://automeshclub.com/parts" target="_blank" rel="noopener noreferrer">Free E30 suspension STEP references · check variants</a></p>
      <p><a href="https://sketchfab.com/3d-models/bmw-e30-410-lsd-rear-differential-v1-09dec653aa4b4c0eb45f3f3159b9a77a" target="_blank" rel="noopener noreferrer">E30 rear diff · online scan reference</a></p>
   </details>
 </aside>
 </div>`;
 $('twin').prepend(panel);
 $('twinreset').onclick=()=>window.ixStudio3D?.reset();
 $('ix-fullscreen').onclick=async()=>{try{await $('ix-studio-stage').requestFullscreen()}catch(e){$('twinvisualstatus').textContent='Fullscreen unavailable: '+e.message}};
 $('twin2d').onclick=()=>{markVisualUserChoice();activate2DFallback(false)};
 $('ix-preview-sedan').onclick=()=>{markVisualUserChoice();showHosted3D()};
 $('ix-save-model').onclick=()=>{markVisualUserChoice();savePersonalModel()};
 $('ix-view-system-model').onclick=()=>{markVisualUserChoice();showPersonalModel(activeVisualSystem?.id)};
 setupMechanicalControls(); 
 $('ix-mode-3d').onclick=()=>{markVisualUserChoice();showLocal3D()};
 $('ix-view-select').onchange=e=>document.querySelector(`[data-ix3d-view="${e.target.value}"]`)?.click()||window.ixStudio3D?.positionView?.(e.target.value);
}
function visualShort(s){return s.replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function renderVisualTwin(d){
 window.visualTwinData=d;ensureVisualTwinUI();
 const menu=$('ix3d-system-select');menu.replaceChildren(new Option('Choose a system',''));
 for(const system of d.systems)menu.add(new Option(`${system.label} · ${system.assembly_count} assemblies`,system.id));
 menu.onchange=()=>{const system=d.systems.find(s=>s.id===menu.value);if(system)chooseVisualSystem(system)};
 $('twinvisualstatus').textContent=`${d.systems.length} indexed systems · reference geometry only`;
 $('twin-system-list').replaceChildren(text('p','Choose a vehicle zone or search for a system to open indexed assemblies.','info'));
 renderVisualSystemFinder(d.systems);
 const slots=$('ix-model-slot');if(slots){const value=slots.value;slots.replaceChildren(new Option('Whole vehicle','body'));for(const s of d.systems)slots.add(new Option(s.label,s.id));if([...slots.options].some(o=>o.value===value))slots.value=value;}
}
function renderVisualSystemFinder(systems){
 const finder=$('ix-system-finder'),list=$('ix-system-results');
 const show=()=>{
  const query=finder.value.trim().toLowerCase();const matches=systems.filter(s=>`${s.label} ${s.domain_label} ${s.id}`.toLowerCase().includes(query));
  list.replaceChildren();
  for(const system of matches){
   const b=text('button',null,'ix-zone-item');b.type='button';b.dataset.system=system.id;
   b.append(text('strong',system.label),text('small',`${system.assembly_count} assemblies · ${personalModels[system.id]?'3D+2D':'2D'}`));
   b.onclick=()=>chooseVisualSystem(system);list.append(b);
  }
  $('ix-system-count').textContent=`${matches.length} / ${systems.length} systems`;
 };
 finder.oninput=show;show();
}
let activeVisualSystem=null,activePersonalSlot=null;
let visualUserChoiceVersion=0;
function markVisualUserChoice(){return ++visualUserChoiceVersion}
function chooseVisualSystem(system){
 markVisualUserChoice();
 const previous=activePersonalSlot;
 if(activeVisualSystem&&activeVisualSystem.id!==system.id)saveVisualContext({assembly_id:'',part_id:'',candidate_id:'',candidate_assembly_id:''});
 selectVisualSystem(system);
 // Changing systems must not present old assembly geometry as the new system.
 if(previous&&previous!=='body'&&previous!==system.id){
   if(personalModels[system.id])showPersonalModel(system.id);
   else activate2DFallback(false);
 }else if($('twin2d')?.classList.contains('active'))loadVisualAssemblies(system,{autoOpen:true});
}
async function openSystemMission(system){
 markVisualUserChoice();
 try{
  const data=await api('/api/missions');
  const existing=(data.missions||[]).find(m=>m.system===system.id&&m.mission_status==='ACTIVE');
  if(existing){await resumeMission(existing);return;}
  tab('garage');
  const domain=$('missiondomain');const matched=restorationDomains.find(d=>d.groups?.some(g=>g.group_name===system.id));
  if(domain&&matched){domain.value=matched.id;syncMissionSystems();}
  const selected=$('missionsystem');if(selected)selected.value=system.id;
  openMissionCreate();
 }catch(e){fail(e)}
}
async function selectVisualSystem(system){activeVisualSystem=system;saveVisualContext({system_id:system.id}); $('workspace-subtitle').textContent=system.label+' · '+system.assembly_count+' indexed assemblies · catalog fitment unverified';updatePersonalModelButton();ensureVisualTwinUI();if($('ix-model-slot'))$('ix-model-slot').value=system.id;const systemSelect=$('ix3d-system-select');if(systemSelect)systemSelect.value=system.id;for(const n of $('twin-canvas').querySelectorAll('.twin-node'))n.classList.toggle('selected',n.dataset.system===system.id);window.ixStudio3D?.selectSystem(system.id);const root=$('twin-system-list');for(const b of $('ix-system-results').querySelectorAll('button'))b.classList.toggle('active',b.dataset.system===system.id);root.replaceChildren(text('h3',system.label),text('p',`${system.domain_label} · ${system.priority} · ${system.assembly_count} catalog assemblies`,'info'),text('p',system.mission_count?`${system.mission_count} persistent mission(s) already linked.`:'No persistent mission linked yet.','info'),text('div','Use the catalog and 2D fallback for exact callouts; the 3D view does not assert dimensions or fitment.','risk'));const open=text('button','Inspect OEM assemblies');open.onclick=()=>loadVisualAssemblies(system);root.append(open);const mission=text('button','Open or start restoration mission');mission.className='light';mission.onclick=()=>openSystemMission(system);root.append(mission);
 const parts=text('button','Find these parts','light');parts.onclick=()=>{tab('lookup');$('group').value=system.id;$('search').value='';search()};root.append(parts);
 const inspect=text('button','Create inspection job','light');inspect.onclick=()=>{tab('jobs');$('jobgroup').value=system.id;$('symptom').focus()};root.append(inspect)
}
let visualSearchToken=0;
async function loadVisualAssemblies(system,{autoOpen=false}={}){
 saveVisualContext({mode:'oem',system_id:system.id});
 deactivateMechanicalMode();hideHosted3D();
 const token=++visualSearchToken;
 // An OEM drawing replaces the 3D canvas; it is not appended below the model.
 const model=$('ix3d-stage');if(model)model.hidden=true;
 $('twin-canvas')?.setAttribute('hidden','');
 $('ix-mode-3d')?.classList.remove('active');$('twin2d')?.classList.add('active');
 if($('ix-stage-heading'))$('ix-stage-heading').textContent='ORIGINAL BMW DRAWINGS';
 const panel=$('twin-diagram-panel');panel.hidden=false;
 $('twin-diagram-title').textContent=visualShort(system.id)+' · factory catalog drawings';
 $('twin-diagram-meta').textContent='BMW catalog diagrams and numbered callouts; drawings are illustrative and do not certify installed 325iX fitment.';
 const body=$('twin-diagram-body');body.replaceChildren(text('p','Loading local catalog assemblies…','info'));
 try{
   const d=await api('/api/search?group='+encodeURIComponent(system.id));if(token!==visualSearchToken)return;body.replaceChildren();
   if(!d.results?.length){body.append(text('p','No indexed assembly for this system. Use Parts & drawings for broader search.','risk'));return}
   const search=document.createElement('input');search.type='search';search.className='ix-assembly-search';
   search.placeholder='Filter assemblies by name…';search.setAttribute('aria-label','Filter assemblies');
   const list=text('div',null,'visual-assembly-list');
   const count=text('p',`${d.results.length} indexed assemblies · ${d.results.filter(a=>a.has_local_drawing).length} drawings verified locally`,'info');
   const detail=text('section',null,'visual-diagram-detail');detail.id='visual-diagram-detail';
   function filterAssemblies(){
     const q=search.value.trim().toLowerCase();const matches=d.results.filter(a=>(a.slug||a.title||'').toLowerCase().includes(q));
     list.replaceChildren();
     for(const a of matches){
       const card=text('button',null,'visual-assembly');card.type='button';card.dataset.assembly=a.id||a.assembly_id;
       card.append(text('strong',visualShort(a.slug||a.title||'Assembly')),
          text('small',`${a.part_count} parts · ${a.has_local_drawing?'Drawing verified locally':'Diagram indexed, local image unverified or missing'}`));
       card.onclick=()=>loadVisualAssembly(a.id||a.assembly_id);list.append(card);
     }
     count.textContent=`${matches.length} of ${d.results.length} assemblies · ${d.results.filter(a=>a.has_local_drawing).length} drawings verified locally`;
   }
   search.oninput=filterAssemblies;filterAssemblies();body.append(search,count,list,detail);
   if(autoOpen){
     const best=d.results.find(a=>a.has_local_drawing)||d.results[0];
     await loadVisualAssembly(best.id||best.assembly_id);
     if(!best.has_local_drawing)detail.prepend(text('p','No local drawing cached in this system. Indexed source links and part records remain available.','risk'));
   }else detail.append(text('p','Choose an assembly to inspect its drawings and OEM records.','info'));
 }catch(e){if(token===visualSearchToken)body.replaceChildren(text('p','2D catalog could not load: '+e.message,'risk'))}
}
let visualAssemblyToken=0;
async function loadVisualAssembly(id){
 const target=$('visual-diagram-detail')||$('twin-diagram-body');
 const token=++visualAssemblyToken;
 target.replaceChildren(text('p','Loading assembly drawing and callouts…','info'));
 try{
  const d=await api('/api/assembly?id='+encodeURIComponent(id));if(token!==visualAssemblyToken)return;
  const restorePart=visualContext.assembly_id===d.assembly.id?visualContext.part_id:'';
  saveVisualContext({mode:'oem',system_id:d.assembly.group_name||visualContext.system_id,assembly_id:d.assembly.id,part_id:restorePart});
  target.replaceChildren();
  for(const b of document.querySelectorAll('.visual-assembly'))b.classList.toggle('active',b.dataset.assembly===id);
  const wrap=text('div',null,'visual-diagram-wrap');
  const figure=(d.figures||[]).find(f=>f.local_available===true)||d.figures?.[0];
  const media=text('div',null,'visual-diagram-media');
  if(figure){
    if(figure.local_available===true){
      const img=document.createElement('img');img.className='visual-diagram-image';img.alt='BMW OEM catalog exploded drawing. Callout image coordinates not yet verified.';
      img.src='/api/diagram?asset='+encodeURIComponent(figure.image_asset_id);
      img.onerror=()=>{img.remove();media.prepend(text('p','The image file could not be loaded from the local cache.','risk'))};
      media.append(img);
    }else media.append(text('p',`The drawing is indexed, but its local image is not verified (${figure.local_integrity_state||'unknown'}). No unverified local copy is displayed; catalog parts and the original source remain available.`,'risk'));
    if(figure.figure_url)media.append(link('Open original catalog drawing',figure.figure_url));
  }else media.append(text('p','This assembly has no linked drawing. Use the verified part records below.','risk'));
  const rail=text('div',null,'visual-callout-rail');
  rail.append(text('h4',(d.assembly.slug||d.assembly.title||'Assembly').replaceAll('_',' ')),text('p',d.scope,'info'));
  for(const p of d.parts||[]){
   const b=text('button',`Callout ${p.callout_position||'?'} · ${p.part_number||'number not recorded'} · ${p.description||'description unavailable'}`,'light');
   b.onclick=()=>selectVisualPart(p,d.assembly);rail.append(b);
  }
  wrap.append(media,rail);target.append(wrap);
  if(restorePart){const selected=(d.parts||[]).find(p=>String(p.id)===String(restorePart));if(selected)selectVisualPart(selected,d.assembly);else saveVisualContext({part_id:''})}
 }catch(e){target.replaceChildren(text('p','Assembly could not load: '+e.message,'risk'))}
}
async function activate2DFallback(scroll=false,reason=''){
 saveVisualContext({mode:'oem',system_id:activeVisualSystem?.id||visualContext.system_id});
 deactivateMechanicalMode();activePersonalSlot=null;hideHosted3D();
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
 const saved=readVisualContext();await selectVisualSystem(preferred);
 if(saved.system_id===preferred.id&&saved.assembly_id){await loadVisualAssemblies(preferred,{autoOpen:false});await loadVisualAssembly(saved.assembly_id)}
 else await loadVisualAssemblies(preferred,{autoOpen:true});
 if(scroll)$('visualtwin').scrollIntoView({behavior:'smooth',block:'start'});
}
function selectVisualPart(p,assembly){saveVisualContext({mode:'oem',system_id:assembly.group_name||visualContext.system_id,assembly_id:assembly.id||visualContext.assembly_id,part_id:p.id});const root=$('twin-system-list');root.replaceChildren(text('h3',p.description||'Selected catalog part'),text('p',`${p.part_number||'OEM number not recorded'} · callout ${p.callout_position||'?'} · ${assembly.slug||assembly.title}`,'title'),text('p','Catalog identity is linked. Installed identity, variant fitment and condition still require evidence.','risk'));const b=text('button','Open full part dossier');b.onclick=()=>{tab('lookup');openPart(p.id)};root.append(b);const system=window.visualTwinData?.systems?.find(s=>s.id===(assembly.group_name||visualContext.system_id))||activeVisualSystem;if(system){const mission=text('button','Open or start restoration mission','light');mission.onclick=()=>openSystemMission(system);root.append(mission)}}

// Ponytail: private local model slots; the server stores them outside Git, not in the catalog.
let personalModels={};
function hideHosted3D(){const e=$('ix3d-hosted');if(e)e.hidden=true;$('ix-preview-sedan')?.classList.remove('active');}
function showHosted3D(){
 if(window.ixLocalDemo){activate2DFallback(false);return;}
 saveVisualContext({mode:'hosted',scene:'',component_id:'',candidate_id:'',candidate_assembly_id:''});
 deactivateMechanicalMode();activePersonalSlot=null;ensureVisualTwinUI();
 const panel=$('ix3d-hosted');panel.hidden=false;
 const iframe=$('ix3d-hosted-frame');
 if(!iframe.src || iframe.src==='about:blank')iframe.src='https://sketchfab.com/models/bd0925e21c934a9cbfdb30ccf5584e86/embed?autostart=1&ui_infos=0&ui_controls=1';
 $('twin-diagram-panel').hidden=true;$('ix3d-stage').hidden=true;$('ix3d-fallback').hidden=true;$('ix-preview-sedan').classList.add('active');
 $('ix-mode-3d').classList.remove('active');$('twin2d').classList.remove('active');
 $('twinvisualstatus').textContent='4-door E30 online reference · geometry and installed fitment unverified';
}
async function showLocal3D(){
 if(window.ixLocalDemo){await openMechanicalScene('ix_front_axle_workshop');return;}
 saveVisualContext({mode:'local-3d',scene:'',component_id:'',candidate_id:'',candidate_assembly_id:''});
 hideHosted3D();
 const status=await api('/api/3d/status');
 if(!status.ready){const note=$('ix3d-fallback');note.hidden=false;note.textContent='Local 3D kit missing. Use the free online sedan or original BMW drawings.';await activate2DFallback(false);return;}
 $('twin-diagram-panel').hidden=true;$('ix3d-stage').hidden=false;$('ix-mode-3d').classList.add('active');$('twin2d').classList.remove('active');
 if(!window.ixStudio3D)window.ixStudio3D=await import('/viewer3d.js');
 if(window.visualTwinData){
  if(personalModels.body){await window.ixStudio3D.openPersonal('/api/3d/model?slot=body',personalModels.body.format,window.visualTwinData,true);activePersonalSlot='body';}
  else{await window.ixStudio3D.mount(window.visualTwinData);activePersonalSlot=null;}
  const selected=window.visualTwinData.systems.find(s=>s.id===visualContext.system_id);if(selected)await selectVisualSystem(selected);
 }
}
async function refreshPersonalModels(){
 try{personalModels=(await api('/api/3d/models')).models||{};}catch(_){personalModels={}}
 updatePersonalModelButton();
 if(window.visualTwinData?.systems)renderVisualSystemFinder(window.visualTwinData.systems);
}
function updatePersonalModelButton(){
 const id=activeVisualSystem?.id;const b=$('ix-view-system-model');if(!b)return;
 b.disabled=!(id&&personalModels[id]);
 b.textContent=b.disabled?'No saved 3D for selected system':'Inspect saved '+activeVisualSystem.label+' 3D';
 const n=Object.keys(personalModels).length;
 $('ix-vault-status').textContent=n+' private model slot'+(n===1?'':'s')+' available · '+(personalModels[id]?.label||'no model for this system');
}
async function savePersonalModel(){
 const file=$('ix3d-local-model').files?.[0],message=$('ix-model-message'),slot=$('ix-model-slot').value;
 if(!file){message.textContent='Choose a GLB or binary STL first.';return;}
 const format=file.name.split('.').at(-1).toLowerCase();
 if(!['glb','stl'].includes(format)||file.size>30000000){message.textContent='Only GLB/binary STL, max 30 MB.';return;}
 const button=$('ix-save-model');button.disabled=true;message.textContent='Saving to private workshop library…';
 try{
  const data=new Uint8Array(await file.arrayBuffer());let binary='';
  for(let i=0;i<data.length;i+=32768)binary+=String.fromCharCode(...data.subarray(i,i+32768));
  const saved=await api('/api/3d/model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slot,format,base64:btoa(binary),label:file.name,source:$('ix-model-source').value})});
  await refreshPersonalModels();message.textContent='Saved '+file.name+' · checksum '+saved.sha256.slice(0,12)+' · no fitment assertion.';
  await showPersonalModel(slot);
 }catch(e){message.textContent='Import failed: '+e.message}finally{button.disabled=false}
}
async function showPersonalModel(slot){
 if(!slot||!personalModels[slot])return;
 saveVisualContext({mode:'personal',slot});
 deactivateMechanicalMode();
 hideHosted3D();const message=$('ix-model-message');
 try{
  const status=await api('/api/3d/status');
  if(!status.ready){message.textContent='Local 3D runtime missing; install the verified kit. Saved model stays available.';return;}
  if(!window.ixStudio3D)window.ixStudio3D=await import('/viewer3d.js');
  await window.ixStudio3D.openPersonal('/api/3d/model?slot='+encodeURIComponent(slot),personalModels[slot].format,window.visualTwinData,slot==='body');
  activePersonalSlot=slot;
  $('ix3d-stage').hidden=false;$('twin-diagram-panel').hidden=true;
  $('ix-mode-3d').classList.add('active');$('twin2d').classList.remove('active');
  $('twinvisualstatus').textContent='Private '+personalModels[slot].format.toUpperCase()+' reference · source '+(personalModels[slot].source||'not supplied');
 }catch(e){activePersonalSlot=null;message.textContent='Cannot open saved model: '+e.message}
}


// RC19: three actual local GLB assembly scenes, selected mesh -> catalog -> reviewable inspection job.
let mechanicalInventory=null,mechanicalScene=null,mechanicalComponent=null,mechanicalCandidate=null;
let mechanicalSelectionToken=0,mechanicalSetup=false;
function deactivateMechanicalMode(){
 if($('ix-mech-static'))$('ix-mech-static').hidden=true;
 mechanicalScene=null;mechanicalComponent=null;mechanicalCandidate=null;++mechanicalSelectionToken;
 $('visualtwin')?.classList.remove('ix-inspect-mode');
 if($('ix-mech-browser'))$('ix-mech-browser').hidden=true;
 if($('ix-mech-stage-controls'))$('ix-mech-stage-controls').hidden=true;
 for(const b of document.querySelectorAll('[data-mech-scene]'))b.classList.remove('active');
}
function setupMechanicalControls(){
 if(mechanicalSetup)return;mechanicalSetup=true;
 for(const button of document.querySelectorAll('[data-mech-scene]'))button.onclick=()=>openMechanicalScene(button.dataset.mechScene,markVisualUserChoice());
 $('ix-bonnet-action').onclick=()=>window.ixStudio3D?.toggleBonnet();
 $('ix-mech-exit').onclick=()=>{markVisualUserChoice();showHosted3D()};
 $('ix-mech-part-filter').oninput=()=>renderMechanicalComponentList();
}
async function getMechanicalInventory(){
 if(!mechanicalInventory)mechanicalInventory=await api('/mechanical_index.json');
 return mechanicalInventory;
}
async function openMechanicalScene(slug,expectedChoiceVersion=null){
 const choiceIsStale=()=>expectedChoiceVersion!==null&&expectedChoiceVersion!==visualUserChoiceVersion;
 ensureVisualTwinUI();setupMechanicalControls();
 if(!window.visualTwinData){window.visualTwinData=await api('/api/visual/twin');if(choiceIsStale())return;}
 const inventory=await getMechanicalInventory();if(choiceIsStale())return;
 const scene=inventory.scenes.find(s=>s.slug===slug);
 if(!scene){$('twinvisualstatus').textContent='Unknown 3D assembly';return;}
 const status=await api('/api/3d/status');if(choiceIsStale())return;
 saveVisualContext({mode:'mechanical',scene:slug,component_id:'',candidate_id:'',candidate_assembly_id:''});mechanicalScene=scene;mechanicalComponent=null;mechanicalCandidate=null;
 $('visualtwin').classList.add('ix-inspect-mode');$('ix-mech-browser').hidden=false;
 $('ix-mech-system-name').textContent=scene.description;
 $('ix-mech-part-filter').value='';$('ix-mech-component-detail').replaceChildren();renderMechanicalComponentList();
 for(const b of document.querySelectorAll('[data-mech-scene]'))b.classList.toggle('active',b.dataset.mechScene===slug);
 $('ix-mech-stage-controls').hidden=false;
 $('ix-mech-stage-label').textContent=slug.includes('engine')?'M20 ENGINE BAY':slug.includes('front_axle')?'325iX FRONT AXLE':'325iX AWD DRIVELINE';
 $('ix-bonnet-action').hidden=!slug.includes('engine');$('ix-bonnet-action').textContent='Close bonnet';
 $('ix3d-hosted').hidden=true;$('ix-preview-sedan').classList.remove('active');
 $('ix3d-stage').hidden=false;$('twin-diagram-panel').hidden=true;$('ix3d-fallback').hidden=true;
 $('ix-mech-static').hidden=true;
 $('ix-mode-3d').classList.add('active');$('twin2d').classList.remove('active');
 $('ix-stage-heading').textContent='3D MECHANICAL STUDIO';
 if(window.matchMedia('(max-width: 760px)').matches)requestAnimationFrame(()=>$('ix-studio-stage').scrollIntoView({behavior:'smooth',block:'start'}));
 $('twinvisualstatus').textContent='Loading '+scene.components.length+' interactive mechanical components';
 if(!status.ready){
   const missing=status.missing?.join(', ')||'Three.js runtime';
   $('twinvisualstatus').textContent='Offline preview · '+scene.components.length+' selectable components in the inspector';$('ix3d-status').textContent='Component geometry included · renderer kit available';
   $('ix3d-stage').hidden=true;$('ix-mech-static').hidden=false;$('ix-mech-preview').src='/'+scene.preview;
   $('ix3d-fallback').hidden=true;
   return;
 }
 try{
   if(!window.ixStudio3D)window.ixStudio3D=await import('/viewer3d.js');
   if(choiceIsStale())return;
   const result=await window.ixStudio3D.openMechanical(scene,window.visualTwinData);
   if(choiceIsStale())return;
   $('twinvisualstatus').textContent=scene.components.length+' modeled components · '+result.pickable+' selectable 3D segments · source model generated locally';
 }catch(e){
   if(choiceIsStale())return;
   $('ix3d-stage').hidden=true;$('ix-mech-static').hidden=false;$('ix-mech-preview').src='/'+scene.preview;
   $('ix3d-fallback').hidden=true;
   $('twinvisualstatus').textContent='Assembly geometry present; renderer error: '+e.message;
 }
}
function renderMechanicalComponentList(){
 if(!mechanicalScene)return;
 const q=$('ix-mech-part-filter').value.trim().toLowerCase(),root=$('ix-mech-part-list');root.replaceChildren();
 const matches=mechanicalScene.components.filter(c=>(c.label+' '+c.search_terms).toLowerCase().includes(q));
 for(const c of matches){
  const b=text('button',null,'ix-mech-component');b.type='button';b.dataset.component=c.id;
  b.classList.toggle('selected',mechanicalComponent?.id===c.id);
  b.append(text('span',c.label),text('small',c.system.replaceAll('_',' ')));
  b.onclick=()=>selectMechanicalComponent(c.id,true);root.append(b);
 }
 if(!matches.length)root.append(text('p','No modeled component matches. Clear the filter to show all.','info'));
}
window.ixOnMechanicalComponent=(sceneSlug,key)=>{
 if(mechanicalScene?.slug===sceneSlug)selectMechanicalComponent(key,false);
};
async function selectMechanicalComponent(key,focus){
 if(!mechanicalScene)return;
 const c=mechanicalScene.components.find(x=>x.id===key);if(!c)return;
 const restoreCandidate=visualContext.scene===mechanicalScene.slug&&visualContext.component_id===c.id?visualContext.candidate_id:'';
 const restoreCandidateAssembly=restoreCandidate?visualContext.candidate_assembly_id:'';
 mechanicalComponent=c;mechanicalCandidate=null;saveVisualContext({mode:'mechanical',scene:mechanicalScene.slug,component_id:c.id,system_id:c.system,candidate_id:restoreCandidate,candidate_assembly_id:restoreCandidateAssembly});
 if(focus)window.ixStudio3D?.focusMechanicalComponent(key);
 else window.ixStudio3D?.selectMechanicalComponent(key,false);
 renderMechanicalComponentList();
 const token=++mechanicalSelectionToken,root=$('ix-mech-component-detail');
 root.replaceChildren(text('span','STEP 02 / COMPONENT','ix-eyebrow'),text('h3',c.label),text('p',c.notes,'ix-mech-help'));
 const actions=text('div',null,'ix-mech-detail-actions');
 const oem=text('button','See OEM drawings','light');oem.onclick=()=>openMechanicalDrawings(c.system);
 const isolate=text('button','Isolate in 3D','light');isolate.onclick=()=>{const active=window.ixStudio3D?.isolateMechanicalComponent(key);isolate.textContent=active?'Show all parts':'Isolate in 3D'};
 actions.append(isolate,oem);root.append(actions);
 const searchLabel=text('p','Looking up BMW catalog matches…','ix-mech-catalog-state');root.append(searchLabel);
 const resultArea=text('div',null,'ix-mech-matches');root.append(resultArea);
 const jobPanel=text('section',null,'ix-mech-job-panel');root.append(jobPanel);
 renderMechanicalJobForm(jobPanel,c);
 try{
  const base='/api/search?group='+encodeURIComponent(c.system)+'&q=';
  let response=await api(base+encodeURIComponent(c.search_terms));
  let used=c.search_terms;
  // Some E30 descriptions use period-specific terminology; try one shorter term.
  if(!response.results?.length){
   const tokenWord=c.search_terms.split(/\s+/).find(w=>w.length>=4&&!['front','rear','engine','six','with','hose'].includes(w.toLowerCase()));
   if(tokenWord){used=tokenWord;response=await api(base+encodeURIComponent(used));}
  }
  if(token!==mechanicalSelectionToken)return;
  const matches=(response.results||[]).slice(0,9);
  searchLabel.textContent=matches.length?`${response.results.length} catalog hits for “${used}” · select an OEM occurrence`:'No matching description. Open the system assembly catalog for part identification.';
  for(const result of matches){
   const b=text('button',null,'ix-mech-catalog-result');b.type='button';b.dataset.candidate=String(result.id||'');b.dataset.assembly=String(result.assembly_id||'');
   b.append(text('strong',result.part_number||'Assembly — BMW catalog'),text('span',result.description||result.slug||result.title||'Catalog record'),
    text('small',`${(result.slug||result.title||'').replaceAll('_',' ')} · ${result.date_condition_raw||'date condition not recorded'}`));
   b.onclick=()=>{
    mechanicalCandidate=result;saveVisualContext({candidate_id:result.id||'',candidate_assembly_id:result.assembly_id||''});
    for(const other of resultArea.querySelectorAll('.ix-mech-catalog-result'))other.classList.toggle('selected',other===b);
    $('ix-mech-job-part').textContent=result.part_number||'catalog occurrence selected';
    $('ix-mech-catalog-choice').textContent='Selected BMW catalog occurrence; installed fitment still requires verification';
   };
   resultArea.append(b);
   const dossier=text('button','Open BMW drawing & part evidence','light');dossier.type='button';
   dossier.addEventListener('click',async()=>{try{mechanicalCandidate=result;saveVisualContext({candidate_id:result.id||'',candidate_assembly_id:result.assembly_id||''});b.classList.add('selected');$('ix-mech-job-part').textContent=result.part_number||'catalog occurrence selected';$('ix-mech-catalog-choice').textContent='Selected BMW catalog occurrence; installed fitment still requires verification';tab('lookup');await openAssembly(result.assembly_id);if(result.id)await openPart(result.id)}catch(e){fail(e)}});
   resultArea.append(dossier);
  }
  if(restoreCandidate){const candidate=[...resultArea.querySelectorAll('.ix-mech-catalog-result')].find(b=>b.dataset.candidate===restoreCandidate);if(candidate)candidate.click();else saveVisualContext({candidate_id:'',candidate_assembly_id:''})}
  const more=text('button','Browse all system assemblies','light');more.onclick=()=>openMechanicalDrawings(c.system);resultArea.append(more);
 }catch(e){if(token===mechanicalSelectionToken)searchLabel.textContent='Catalog lookup failed: '+e.message}
}
async function openMechanicalDrawings(group){
 const system=window.visualTwinData?.systems?.find(s=>s.id===group);
 if(!system){tab('lookup');$('search').value=mechanicalComponent?.search_terms||'';search();return;}
 await selectVisualSystem(system);
 await loadVisualAssemblies(system,{autoOpen:true});
}
function renderMechanicalJobForm(root,c){
 const frontPlay=c.system==='front_axle'||c.system==='steering';
 root.replaceChildren(text('span',frontPlay?'STEP 03 / FRONT-WHEEL-PLAY WORKFLOW':'STEP 03 / REPAIR WORKFLOW','ix-eyebrow'),
  text('h4',frontPlay?'Start guided front-wheel-play inspection':'Create an inspection'),
  text('p',frontPlay?'Continue into the existing seven-step front-axle/steering workflow. The 3D part is an orientation reference, not installed-part identification.':'A real saved job starts here. Only observed evidence is recorded; never generated from the model.','ix-mech-help'));
 const choice=text('div','No BMW catalog occurrence selected','ix-mech-selection-status');choice.id='ix-mech-job-part';
 const state=text('div','','ix-mech-selection-state');state.id='ix-mech-catalog-choice';root.append(choice,state);
 const form=document.createElement('form');form.className='ix-mech-job-form';
 let sideSelect=null;
 if(frontPlay){
  const sideLabel=text('label','Affected front corner');sideSelect=document.createElement('select');sideSelect.required=true;
  for(const [value,label] of [['UNKNOWN','Not known yet'],['LEFT','Front left'],['RIGHT','Front right'],['BOTH','Both front sides']]){const option=document.createElement('option');option.value=value;option.textContent=label;sideSelect.append(option)}
  sideLabel.append(sideSelect);form.append(sideLabel);
 }
 const symptom=document.createElement('textarea');symptom.id='ix-mech-job-symptom';symptom.rows=2;symptom.required=true;symptom.minLength=frontPlay?8:4;
 symptom.placeholder=frontPlay?'Describe only the observed play or looseness; cause unknown.':'What needs inspection? Describe the real symptom or objective…';
 const evidence=document.createElement('textarea');evidence.id='ix-mech-job-evidence';evidence.rows=2;
 evidence.placeholder=frontPlay?'Optional observation only; enter numeric measurements with units and tool in the case evidence ledger.':'Optional observed condition / measurement (not a guess)';
 const source=document.createElement('input');source.id='ix-mech-job-source';source.placeholder='Evidence source / mechanic (required if adding evidence)';
 const button=text('button',frontPlay?'Save & open seven-step inspection':'Save inspection & open mission');button.type='submit';button.className='ix-mech-save';
 const status=text('div','','ix-mech-job-status');status.setAttribute('role','status');
 form.append(symptom,evidence,source,button,status);root.append(form);
 form.onsubmit=async ev=>{
  ev.preventDefault();if(mechanicalComponent!==c)return;
  if(evidence.value.trim()&&!source.value.trim()){status.textContent='Enter who observed the condition or the evidence source.';source.focus();return;}
  button.disabled=true;status.textContent='Saving inspection in local workshop database…';
  let savedJob=null;
  try{
   let job;
   if(frontPlay){
    job=await api('/api/expert/front-play/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
     side:sideSelect.value,system:c.system,symptom:symptom.value.trim(),
     context:'Started from the interactive front-axle visual workshop; selected geometry is orientation-only.',
     visual_scene:mechanicalScene.slug,visual_component_id:c.id,
     assembly_id:mechanicalCandidate?.assembly_id||'',candidate_id:mechanicalCandidate?.id||'',part_number:mechanicalCandidate?.part_number||''
    })});
   }else{
    job=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({system:c.system,assembly_id:mechanicalCandidate?.assembly_id||'',symptom:symptom.value.trim(),context:`Visual inspection: ${mechanicalScene.description}; component: ${c.label}; keyword: ${c.search_terms}; candidate OEM ${mechanicalCandidate?.part_number||'not yet verified'}`})});
   }
   savedJob=job;
   if(evidence.value.trim())await api('/api/job/'+job.job_id+'/observation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'inspection',value:evidence.value.trim(),unit:'',tool:'',source:source.value.trim()})});
   currentJob=job.job_id;
   if(frontPlay){
    status.textContent='Case saved; opening its persistent seven-step inspection…';
    tab('expert');await expertInit();await expertOpen(job.job_id);
   }else{
    const domain=restorationDomains.find(d=>d.groups?.some(g=>g.group_name===c.system));
    const mission={job_id:job.job_id,domain_id:domain?.id||'other',domain_label:domain?.label||c.system.replaceAll('_',' '),system:c.system,mission_status:'ACTIVE'};
    await resumeMission(mission);
   }
  }catch(err){
   status.textContent=savedJob?'Inspection IX-'+String(savedJob.job_id).padStart(4,'0')+' was saved, but follow-up failed: '+err.message+' Refresh the saved-case list; do not submit a duplicate.':'Could not save inspection: '+err.message;
   button.disabled=Boolean(savedJob);
  }
 };
}

let ixStudioLoading=null;
async function restoreCatalogContext(){
 const saved=readVisualContext();if(!saved.part_id&&!saved.assembly_id)return false;
 try{if(saved.part_id)await openPart(saved.part_id);else await openAssembly(saved.assembly_id);return true}
 catch(e){return false}
}
async function restoreMissionContext(){
 const jobId=readVisualContext().mission_job_id;if(!jobId)return false;
 try{const data=await api('/api/missions');const mission=(data.missions||[]).find(m=>String(m.job_id)===String(jobId));
  if(!mission){saveVisualContext({mission_job_id:''});return false;}
  await resumeMission(mission);return true;
 }catch(e){$('livingmissionevidence')?.replaceChildren(text('p','Saved mission could not be reopened: '+e.message,'risk'));return false;}
}
async function restoreExpertContext(jobId){
 if(!jobId)return false;
 try{await expertInit();await expertOpen(jobId);return true}catch(_){return false}
}
async function restoreVisualContext(expectedChoiceVersion=visualUserChoiceVersion){
 const choiceIsStale=()=>expectedChoiceVersion!==visualUserChoiceVersion;
 const saved=readVisualContext();
 const system=window.visualTwinData?.systems?.find(s=>s.id===saved.system_id);
 try{
  if(system)await selectVisualSystem(system);
  if(choiceIsStale())return true;
  if(saved.mode==='mechanical'&&saved.scene){
   await openMechanicalScene(saved.scene,expectedChoiceVersion);
   if(choiceIsStale())return true;
   if(saved.component_id){saveVisualContext({component_id:saved.component_id,candidate_id:saved.candidate_id,candidate_assembly_id:saved.candidate_assembly_id});await selectMechanicalComponent(saved.component_id,false);if(choiceIsStale())return true;}
   return true;
  }
  if(saved.mode==='oem'&&system){
   await selectVisualSystem(system);if(choiceIsStale())return true;
   await loadVisualAssemblies(system,{autoOpen:false});if(choiceIsStale())return true;
   const context=readVisualContext();if(context.assembly_id)await loadVisualAssembly(context.assembly_id);
   return true;
  }
  if(saved.mode==='personal'&&saved.slot&&personalModels[saved.slot]){await showPersonalModel(saved.slot);if(choiceIsStale())return true;if(system)await selectVisualSystem(system);return true;}
  if(saved.mode==='local-3d'){await showLocal3D();if(choiceIsStale())return true;if(system)await selectVisualSystem(system);return true;}
  if(saved.mode==='hosted'){if(choiceIsStale())return true;showHosted3D();if(system)await selectVisualSystem(system);return true;}
 }catch(e){if(choiceIsStale())return true;$('twinvisualstatus').textContent='Could not restore visual context: '+e.message;$('twinvisualstatus').className='risk';return true;}
 return false;
}
window.ixSelectVisualSystemById=id=>{const s=window.visualTwinData?.systems?.find(x=>x.id===id);if(s){if(activeVisualSystem&&activeVisualSystem.id!==id)saveVisualContext({assembly_id:'',part_id:'',candidate_id:'',candidate_assembly_id:''});selectVisualSystem(s)}};
function applyRuntimeMode(status){
 window.ixLocalDemo=Boolean(status?.demo_mode);
 if(!window.ixLocalDemo)return;
 const main=$('workbench-main');
 if(main&&!$('local-demo-banner')){
  const banner=text('aside','LOCAL SYNTHETIC DEMO — catalog rows are fabricated test data. No OEM drawings, real part numbers, repair procedures, fitment evidence or road-use approval are included.','local-demo-banner');
  banner.id='local-demo-banner';main.prepend(banner);
 }
 // The synthetic package includes three selectable mechanical GLBs. The M3
 // exterior and hosted sedan are excluded, so label this action accurately.
 if($('ix-mode-3d')){$('ix-mode-3d').hidden=false;$('ix-mode-3d').textContent='3D assemblies';}
 if($('ix-preview-sedan'))$('ix-preview-sedan').hidden=true;
}
async function loadVisualTwin(){
 const choiceVersion=visualUserChoiceVersion;
 const choiceIsStale=()=>choiceVersion!==visualUserChoiceVersion;
 ensureVisualTwinUI();
 try{
  const d=await api('/api/visual/twin');if(choiceIsStale())return;renderVisualTwin(d);await refreshPersonalModels();
  if(choiceIsStale())return;
  // Check the complete local import graph before importing any Three.js module.
  // A failed nested import otherwise manifests misleadingly as "Failed to fetch viewer3d.js".
  let status;
  try{status=await api('/api/3d/status')}catch(e){status={ready:false,missing:['3D status endpoint: '+e.message]}}
  if(choiceIsStale())return;
  applyRuntimeMode(status);
  if(await restoreVisualContext(choiceVersion))return;
  if(choiceIsStale())return;
  if(status.demo_mode){await openMechanicalScene('ix_front_axle_workshop',choiceVersion);return;}
  if(status.ready&&personalModels.body){
    if(!ixStudioLoading)ixStudioLoading=import('/viewer3d.js').then(m=>{window.ixStudio3D=m;return m});
    try{const studio=await ixStudioLoading;if(choiceIsStale())return;await studio.openPersonal('/api/3d/model?slot=body',personalModels.body.format,d,true);if(choiceIsStale())return;activePersonalSlot='body';saveVisualContext({mode:'personal',slot:'body'});}
    catch(e){ixStudioLoading=null;if(!choiceIsStale())showHosted3D();}
  }else if(!choiceIsStale())await openMechanicalScene('ix_front_axle_workshop',choiceVersion);

 }catch(e){
  if(choiceIsStale())return;
  $('twinvisualstatus').textContent='Visual twin unavailable: '+e.message;
  $('twinvisualstatus').className='risk';
 }
}

// Restore the last workspace and evidence context on refresh/reopen. The SQLite
// job remains authoritative; this browser key stores only local UI locators/IDs.
const startupContext=readVisualContext();
const requestedWorkspace=location.hash.slice(1);
const initialWorkspace=Object.prototype.hasOwnProperty.call(workspaces,requestedWorkspace)?requestedWorkspace:startupContext.workspace;
if(initialWorkspace&&workspaces[initialWorkspace]){
 tab(initialWorkspace);
 if(initialWorkspace==='lookup')restoreCatalogContext();
 if(initialWorkspace==='mission')restoreMissionContext();
 if(initialWorkspace==='expert'&&startupContext.front_play_job_id)restoreExpertContext(startupContext.front_play_job_id);
}
api('/api/3d/status').then(applyRuntimeMode).catch(()=>{});
