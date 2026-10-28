(() => {
  "use strict";
  const cfg = window.SJA_CONFIG || {};
  const configured = cfg.SUPABASE_URL && cfg.SUPABASE_ANON_KEY &&
    cfg.SUPABASE_URL.startsWith("https://") && !cfg.SUPABASE_URL.includes("PASTE_") &&
    !cfg.SUPABASE_ANON_KEY.includes("PASTE_");
  const supabase = configured && window.supabase ? window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY) : null;
  const $ = (s, root=document) => root.querySelector(s);
  const grid = $("#jobGrid"), notice = $("#setupNotice"), count = $("#resultCount");
  const detailDialog = $("#detailDialog"), adminDialog = $("#adminDialog");
  let allJobs = [], activeCategory = "All", searchTerm = "", currentUser = null, editingId = null;
  $("#year").textContent = new Date().getFullYear();

  const escapeHtml = (value="") => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const formatDate = value => value ? new Date(value + (String(value).length===10 ? "T00:00:00" : "")).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "As per notification";
  const isExpired = job => job.last_date && new Date(job.last_date + "T23:59:59") < new Date();
  const isNewJob = job => { if(!job.created_at) return false; const created = new Date(job.created_at).getTime(); return Number.isFinite(created) && (Date.now()-created)>=0 && (Date.now()-created)<3*24*60*60*1000; };
  const demoJobs = [
    {id:"demo-1",title:"Sample: Junior Assistant Recruitment",department:"Sample Department (Demo only)",category:"Latest Jobs",vacancies:"—",qualification:"As per official notice",last_date:null,status:"published",description:"Yeh sirf design preview ke liye sample entry hai. Isse real vacancy na samjhein. Live website par verified official details add karein.",notification_url:"",apply_url:""},
    {id:"demo-2",title:"Sample: Admit Card Update",department:"Sample Exam Board (Demo only)",category:"Admit Card",vacancies:"—",qualification:"Registered candidates",last_date:null,status:"published",description:"Demo card only. Actual admit card link publish karne se pehle official source verify karein.",notification_url:"",apply_url:""},
    {id:"demo-3",title:"Sample: Examination Result",department:"Sample Recruitment Board (Demo only)",category:"Results",vacancies:"—",qualification:"Exam candidates",last_date:null,status:"published",description:"Demo card only. Real result details yahan verified source ke saath add honge.",notification_url:"",apply_url:""}
  ];
  function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2600);}
  async function loadJobs(){
    if(!supabase){notice.hidden=false;allJobs=demoJobs;renderJobs();return;}
    const {data,error}=await supabase.from("jobs").select("*").eq("status","published").order("created_at",{ascending:false});
    if(error){notice.hidden=false;notice.textContent="Live database se connect nahi ho paya. SETUP.md ke steps aur Supabase policies check karein.";allJobs=[];renderJobs();return;}
    notice.hidden=true;allJobs=data||[];renderJobs();
  }
  function renderJobs(){
    const filtered=allJobs.filter(j=>(activeCategory==="All"||j.category===activeCategory)&&(`${j.title} ${j.department} ${j.qualification||""}`.toLowerCase().includes(searchTerm)));
    count.textContent=`${filtered.length} update${filtered.length===1?"":"s"}`;
    $("#listingHeading").textContent=activeCategory==="All"?"Latest Government Jobs":activeCategory;
    if(!filtered.length){grid.innerHTML='<div class="empty-state"><strong>Abhi koi matching update nahi mila.</strong><br><span>Search badal kar dekhein ya baad mein check karein.</span></div>';return;}
    grid.innerHTML=filtered.map(j=>`<article class="job-card">
      <div class="card-top"><span class="tag">${escapeHtml(j.category||"Latest Jobs")}</span><span class="status-tag">${isExpired(j)?"Date passed":"Check details"}</span></div>
      <h3>${escapeHtml(j.title)}${isNewJob(j)?' <span class="new-badge">NEW</span>':""}</h3><p class="department">${escapeHtml(j.department||"Department not specified")}</p>
      <div class="card-meta"><div class="meta-item"><small>Vacancies / Update</small><strong>${escapeHtml(j.vacancies||"See notice")}</strong></div><div class="meta-item"><small>Last date</small><strong>${escapeHtml(formatDate(j.last_date))}</strong></div></div>
      <div class="card-actions"><button class="details-btn" data-detail="${escapeHtml(j.id)}">View Details</button>${j.apply_url?`<a class="apply-btn" href="${escapeHtml(j.apply_url)}" target="_blank" rel="noopener noreferrer">Official Link ↗</a>`:`<button class="apply-btn" data-detail="${escapeHtml(j.id)}">Read Update</button>`}</div>
    </article>`).join("");
  }
  function showDetails(id){
    const j=allJobs.find(x=>String(x.id)===String(id));if(!j)return;
    $("#detailContent").innerHTML=`<span class="tag">${escapeHtml(j.category||"Latest Jobs")}</span><h2 class="detail-title">${escapeHtml(j.title)}</h2><p class="detail-dept">${escapeHtml(j.department||"Department not specified")}</p>
      <table class="detail-table"><tbody><tr><th>Vacancies</th><td>${escapeHtml(j.vacancies||"See notification")}</td></tr><tr><th>Qualification</th><td>${escapeHtml(j.qualification||"See official notification")}</td></tr><tr><th>Notification Date</th><td>${escapeHtml(formatDate(j.notification_date))}</td></tr><tr><th>Last Date</th><td>${escapeHtml(formatDate(j.last_date))}</td></tr><tr><th>DOB Eligibility</th><td>${escapeHtml(j.dob_from||j.dob_to ? (j.dob_from?formatDate(j.dob_from):'Any')+' to '+(j.dob_to?formatDate(j.dob_to):'Any') : 'See official notification')}</td></tr><tr><th>Fees</th><td>${escapeHtml(j.fees||"See official notification")}</td></tr><tr><th>Age Limit</th><td>${escapeHtml(j.age_limit||"See official notification")}</td></tr><tr><th>Selection</th><td>${escapeHtml(j.selection_process||"See official notification")}</td></tr></tbody></table>
      <h3>Important Information</h3><div class="detail-copy">${escapeHtml(j.description||"Please read the official notification carefully.")}</div>
      <div class="card-actions">${j.notification_url?`<a class="details-btn" href="${escapeHtml(j.notification_url)}" target="_blank" rel="noopener noreferrer">Official Notification ↗</a>`:""}${j.apply_url?`<a class="apply-btn" href="${escapeHtml(j.apply_url)}" target="_blank" rel="noopener noreferrer">Apply Online ↗</a>`:""}</div>
      <p class="tiny-note">Dates, eligibility, fees aur links ko apply karne se pehle official website par verify karein.</p>`;
    detailDialog.showModal();
  }
  document.addEventListener("click",e=>{const d=e.target.closest("[data-detail]");if(d)showDetails(d.dataset.detail);});
  $("#detailClose").addEventListener("click",()=>detailDialog.close());
  $("#searchBtn").addEventListener("click",()=>{searchTerm=$("#searchInput").value.trim().toLowerCase();renderJobs();});
  $("#searchInput").addEventListener("input",()=>{searchTerm=$("#searchInput").value.trim().toLowerCase();renderJobs();});
  document.querySelectorAll(".cat").forEach(btn=>btn.addEventListener("click",()=>{document.querySelectorAll(".cat").forEach(x=>x.classList.remove("active"));btn.classList.add("active");activeCategory=btn.dataset.category;renderJobs();}));
  $("#adminOpen").addEventListener("click",()=>{adminDialog.showModal();});
  $("#adminClose").addEventListener("click",()=>adminDialog.close());
  $("#loginForm").addEventListener("submit",async e=>{
    e.preventDefault();const msg=$("#loginMessage");msg.textContent="";
    if(!supabase){msg.textContent="Pehle config.js mein Supabase URL aur anon key set karein. SETUP.md dekhein.";return;}
    const email=$("#adminEmail").value.trim(),password=$("#adminPassword").value;
    const {data,error}=await supabase.auth.signInWithPassword({email,password});
    if(error){msg.textContent="Login nahi hua. Email/password aur Supabase user check karein.";return;}
    currentUser=data.user;renderAdmin();
  });
  async function renderAdmin(){
    const {data,error}=await supabase.from("jobs").select("*").order("created_at",{ascending:false});
    if(error){$("#adminRoot").innerHTML=`<button class="dialog-close" id="adminLogout">×</button><h2>Dashboard load nahi hua</h2><p>Database schema/RLS policy check karein. ${escapeHtml(error.message)}</p>`;return;}
    const jobs=data||[];
    $("#adminRoot").innerHTML=`<div class="admin-panel-head"><div><p class="eyebrow">SARKARI JOB ALERT • CONTENT CONTROL</p><h2>Admin Control Center</h2><p class="tiny-note">Add job details, save drafts, and publish after checking. Logged in: ${escapeHtml(currentUser?.email||"Admin")}</p></div><div class="admin-actions"><button class="small-btn primary" id="newJob">+ Add Update</button><button class="small-btn" id="logoutBtn">Logout</button></div></div>
      <div class="admin-stats"><div class="stat"><strong>${jobs.length}</strong><span>Total posts</span></div><div class="stat"><strong>${jobs.filter(j=>j.status==="published").length}</strong><span>Published</span></div><div class="stat"><strong>${jobs.filter(j=>j.status==="draft").length}</strong><span>Drafts</span></div></div>
      <form id="jobForm" class="editor-form" hidden>
        <input type="hidden" id="jobId">
        <label>Post title *<input id="jobTitle" required maxlength="180" placeholder="e.g. Recruitment / Admit Card title"></label>
        <label>Department<input id="jobDepartment" maxlength="180" placeholder="Department / Board name"></label>
        <label>Category *<select id="jobCategory"><option>Latest Jobs</option><option>Admit Card</option><option>Results</option><option>Answer Key</option><option>Admission</option><option>Syllabus</option></select></label>
        <label>Vacancies / update<input id="jobVacancies" maxlength="80" placeholder="e.g. 250 posts"></label>
        <label>Notification date<input id="jobNotificationDate" type="date"></label>
        <label>Last date to apply<input id="jobLastDate" type="date"></label>
        <label>DOB eligibility — From<input id="jobDobFrom" type="date"></label>
        <label>DOB eligibility — To<input id="jobDobTo" type="date"></label>
        <label>Qualification<input id="jobQualification" maxlength="180" placeholder="Eligibility summary"></label>
        <label>Application fees<input id="jobFees" maxlength="180" placeholder="As per official notice"></label>
        <label>Age limit<input id="jobAge" maxlength="180" placeholder="As per official notice"></label>
        <label>Selection process<input id="jobSelection" maxlength="180" placeholder="Exam / Interview etc."></label>
        <label>Official notification PDF / URL<input id="jobNotification" type="url" placeholder="Official notification link"></label>
        <label>Apply online URL<input id="jobApply" type="url" placeholder="https://official-site.gov.in/..."></label>
        <label class="full">Complete job details (copy-paste)<textarea id="jobDescription" maxlength="10000" placeholder="Yahan job ki poori details copy-paste karein. Publish se pehle official notification, dates aur apply link verify karein."></textarea></label>
        <label>Status<select id="jobStatus"><option value="draft">Draft (not public)</option><option value="published">Published (public)</option></select></label>
        <div class="editor-actions full"><button class="small-btn primary" type="submit">Save Update</button><button class="small-btn" type="button" id="cancelEdit">Cancel</button></div>
        <p id="saveMessage" class="form-message full"></p>
      </form>
      <div class="admin-tools"><input id="adminSearch" type="search" placeholder="Search job title / department..." aria-label="Search jobs"><select id="adminFilter" aria-label="Filter posts"><option value="all">All posts</option><option value="draft">Drafts only</option><option value="published">Published only</option></select></div>
      <div class="admin-list" id="adminList">${jobs.length?jobs.map(j=>`<div class="admin-item"><div><h4>${escapeHtml(j.title)}</h4><p>${escapeHtml(j.category)} • ${escapeHtml(j.status)} • ${escapeHtml(j.department||"No department")} • Notification: ${escapeHtml(formatDate(j.notification_date))} • Last date: ${escapeHtml(formatDate(j.last_date))}</p></div><div class="admin-item-actions"><button class="small-btn" data-edit="${escapeHtml(j.id)}">Edit</button><button class="small-btn" data-toggle="${escapeHtml(j.id)}" data-status="${escapeHtml(j.status)}">${j.status==="published"?"Unpublish":"Publish"}</button><button class="small-btn" data-delete="${escapeHtml(j.id)}">Delete</button></div></div>`).join(""):'<div class="empty-state">Abhi posts nahi hain. “Add Update” se pehli post banayein.</div>'}</div>`;
    $("#newJob").onclick=()=>openEditor();
    $("#cancelEdit").onclick=()=>{$("#jobForm").hidden=true;editingId=null;};
    $("#logoutBtn").onclick=async()=>{await supabase.auth.signOut();currentUser=null;$("#adminRoot").innerHTML=loginMarkup();};
    $("#jobForm").onsubmit=saveJob;
    $("#adminRoot").querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>openEditor(jobs.find(j=>String(j.id)===b.dataset.edit)));
    $("#adminRoot").querySelectorAll("[data-toggle]").forEach(b=>b.onclick=()=>changeStatus(b.dataset.toggle,b.dataset.status==="published"?"draft":"published"));
    $("#adminRoot").querySelectorAll("[data-delete]").forEach(b=>b.onclick=()=>deleteJob(b.dataset.delete));
    const filterAdminList=()=>{const term=( $("#adminSearch")?.value||"").trim().toLowerCase();const state=$("#adminFilter")?.value||"all";$("#adminList")?.querySelectorAll(".admin-item").forEach(item=>{const hay=item.textContent.toLowerCase();const okText=!term||hay.includes(term);const okState=state==="all"||hay.includes("• "+state+" •");item.style.display=okText&&okState?"":"none";});};
    $("#adminSearch")?.addEventListener("input",filterAdminList);$("#adminFilter")?.addEventListener("change",filterAdminList);
  }
  function loginMarkup(){return `<div class="admin-login-head"><span class="brand-mark">SA</span><h2>Admin Dashboard</h2><p>Private access for site owner</p></div><form id="loginForm" class="admin-form"><label>Email<input id="adminEmail" type="email" autocomplete="username" required placeholder="Admin email"></label><label>Password<input id="adminPassword" type="password" autocomplete="current-password" required placeholder="Password"></label><button type="submit" class="primary-btn">Secure Login</button><p id="loginMessage" class="form-message"></p></form><p class="tiny-note">Admin account Supabase Dashboard mein create karein. Public sign-up yahan disabled hai.</p>`;}
  function openEditor(j=null){
    editingId=j?.id||null;const f=$("#jobForm");f.hidden=false;
    const values={jobId:j?.id||"",jobTitle:j?.title||"",jobDepartment:j?.department||"",jobCategory:j?.category||"Latest Jobs",jobVacancies:j?.vacancies||"",jobNotificationDate:j?.notification_date||"",jobLastDate:j?.last_date||"",jobDobFrom:j?.dob_from||"",jobDobTo:j?.dob_to||"",jobQualification:j?.qualification||"",jobFees:j?.fees||"",jobAge:j?.age_limit||"",jobSelection:j?.selection_process||"",jobNotification:j?.notification_url||"",jobApply:j?.apply_url||"",jobDescription:j?.description||"",jobStatus:j?.status||"draft"};
    Object.entries(values).forEach(([id,v])=>{const el=$("#"+id);if(el)el.value=v;});
    f.scrollIntoView({behavior:"smooth",block:"start"});
  }
  async function saveJob(e){
    e.preventDefault();const msg=$("#saveMessage");msg.textContent="";
    const data={title:$("#jobTitle").value.trim(),department:$("#jobDepartment").value.trim(),category:$("#jobCategory").value,vacancies:$("#jobVacancies").value.trim(),notification_date:$("#jobNotificationDate").value||null,last_date:$("#jobLastDate").value||null,dob_from:$("#jobDobFrom").value||null,dob_to:$("#jobDobTo").value||null,qualification:$("#jobQualification").value.trim(),fees:$("#jobFees").value.trim(),age_limit:$("#jobAge").value.trim(),selection_process:$("#jobSelection").value.trim(),notification_url:$("#jobNotification").value.trim()||null,apply_url:$("#jobApply").value.trim()||null,description:$("#jobDescription").value.trim(),status:$("#jobStatus").value,updated_at:new Date().toISOString()};
    const result=editingId?await supabase.from("jobs").update(data).eq("id",editingId).select().single():await supabase.from("jobs").insert({...data,created_by:currentUser.id}).select().single();
    if(result.error){msg.textContent="Save failed: "+result.error.message+". Agar column missing bataye, SQL_MIGRATION.sql Supabase SQL Editor mein run karein.";return;}
    toast("Update saved successfully");await loadJobs();await renderAdmin();
  }
  async function changeStatus(id,status){const {error}=await supabase.from("jobs").update({status,updated_at:new Date().toISOString()}).eq("id",id);if(error){toast("Status update nahi hua");return;}toast(status==="published"?"Post published":"Post draft mein chali gayi");await loadJobs();await renderAdmin();}
  async function deleteJob(id){if(!confirm("Kya aap is post ko permanently delete karna chahte hain?"))return;const {error}=await supabase.from("jobs").delete().eq("id",id);if(error){toast("Delete nahi hua. Permissions check karein.");return;}toast("Post deleted");await loadJobs();await renderAdmin();}
  loadJobs();
})();
