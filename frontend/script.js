const API="http://127.0.0.1:5000/api";
let current=null;

const $=id=>document.getElementById(id);
function showError(msg){$("error").textContent=msg;$("error").classList.remove("d-none")}
function clearError(){$("error").classList.add("d-none")}
function chips(items){return items.map(x=>`<span class="chip">${escapeHtml(x)}</span>`).join("")}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}

async function api(path,opts={}){
 const r=await fetch(API+path,opts);
 const data=await r.json().catch(()=>({error:"Invalid server response"}));
 if(!r.ok)throw new Error(data.error||"Request failed");
 return data;
}

async function checkApi(){
 try{const x=await api("/health");$("apiStatus").textContent=x.database?"API + PostgreSQL":"API online, database offline";$("apiStatus").className="badge "+(x.database?"text-bg-success":"text-bg-warning")}
 catch{$("apiStatus").textContent="Backend offline";$("apiStatus").className="badge text-bg-danger"}
}
checkApi();

$("dropZone").onclick=()=>$("resumeFile").click();
$("resumeFile").onchange=()=>{const f=$("resumeFile").files[0];$("fileName").textContent=f?f.name:"Maximum 8 MB"};
$("dropZone").ondragover=e=>{e.preventDefault()};
$("dropZone").ondrop=e=>{e.preventDefault();$("resumeFile").files=e.dataTransfer.files;$("fileName").textContent=e.dataTransfer.files[0]?.name||""};

$("analyzeBtn").onclick=async()=>{
 clearError(); const f=$("resumeFile").files[0];
 if(!f)return showError("Please choose a PDF or DOCX resume.");
 const fd=new FormData();fd.append("resume",f);fd.append("name",$("resumeName").value);fd.append("job_description",$("jobDescription").value);
 $("analyzeBtn").disabled=true;$("analyzeBtn").textContent="Analyzing...";
 try{current=await api("/resumes/analyze",{method:"POST",body:fd});render(current);await loadSaved()}
 catch(e){showError(e.message)}
 finally{$("analyzeBtn").disabled=false;$("analyzeBtn").textContent="Analyze Resume"}
};

function render(d){
 $("results").classList.remove("d-none");
 $("resumeScore").textContent=(d.analysis.score??0)+"/100";
 $("matchScore").textContent=d.match?d.match.score+"%":"—";
 $("wordCount").textContent=d.analysis.word_count??"—";
 $("skills").innerHTML=chips(d.analysis.skills||[]);
 $("checks").innerHTML=(d.analysis.checks||[]).map(c=>`<div class="check">${c.type==="warning"?"⚠️":"ℹ️"} ${escapeHtml(c.message)}</div>`).join("")||"<div class='text-success'>No basic issues detected.</div>";
 $("suggestions").innerHTML=(d.suggestions||[]).map(x=>`<li>${escapeHtml(x)}</li>`).join("");
 if(d.match){
  $("jobPanel").innerHTML=`
  <div class="mb-3"><strong>${d.match.score}%</strong> overall match</div>
  <p class="mb-1 fw-semibold">Matched skills</p><div class="chips mb-3">${chips(d.match.matched_skills||[])}</div>
  <p class="mb-1 fw-semibold">Missing skills</p><div class="chips mb-3">${chips(d.match.missing_skills||[])}</div>
  <p class="mb-1 fw-semibold">Missing keywords</p><div class="chips">${chips(d.match.missing_keywords||[])}</div>`;
 }else $("jobPanel").innerHTML="<p class='text-secondary'>No job description supplied.</p>";
 $("chat").innerHTML="";
}

function formatAiText(text){
  // basic readable formatting
  let t = escapeHtml(text);
  t = t.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");   // **bold**
  t = t.replace(/\*(.*?)\*/g, "<em>$1</em>");               // *italic*
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");           // `code`
  t = t.replace(/\n/g, "<br>");                             // line breaks
  return t;
}

function addMsg(type, text){
  const content = type === "ai" ? formatAiText(text) : escapeHtml(text);
  $("chat").insertAdjacentHTML("beforeend", `<div class="msg ${type}">${content}</div>`);
  $("chat").scrollTop = $("chat").scrollHeight;
}
$("sendBtn").onclick=async()=>{
 if(!current)return;
 const q=$("question").value.trim();if(!q)return;
 addMsg("user",q);$("question").value="";$("aiError").textContent="Thinking...";
 try{const x=await api("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({resume:current.text,job_description:current.job_description,analysis:current.analysis,match:current.match,question:q})});addMsg("ai",x.answer);$("aiError").textContent=""}
 catch(e){$("aiError").textContent=e.message}
};

document.querySelectorAll(".rewrite").forEach(btn=>btn.onclick=async()=>{
 if(!current)return;
 $("aiError").textContent="Rewriting...";
 try{const x=await api("/rewrite",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({resume:current.text,job_description:current.job_description,analysis:current.analysis,match:current.match,section:btn.dataset.section})});addMsg("ai",x.answer);$("aiError").textContent=""}
 catch(e){$("aiError").textContent=e.message}
});

async function loadSaved(){
 try{
  const data=await api("/resumes");
  $("saved").innerHTML=data.length?data.map(d=>`<div class="saved-item d-flex justify-content-between align-items-center"><div><strong>${escapeHtml(d.name)}</strong><div class="small text-secondary">${escapeHtml(d.filename)} · Resume ${d.analysis?.score??0}/100 ${d.match?`· Match ${d.match.score}%`:""}</div></div><button class="btn btn-sm btn-outline-danger" onclick="removeResume('${d.id}')">Delete</button></div>`).join(""):"<span class='text-secondary'>No saved resumes yet.</span>";
 }catch(e){$("saved").innerHTML=`<span class='text-danger'>${escapeHtml(e.message)}</span>`}
}
window.removeResume=async id=>{if(!confirm("Delete this resume?"))return;try{await api("/resumes/"+id,{method:"DELETE"});loadSaved()}catch(e){alert(e.message)}};
$("refreshBtn").onclick=loadSaved;
loadSaved();
