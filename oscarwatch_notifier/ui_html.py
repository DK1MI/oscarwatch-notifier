INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>oscarwatch-notifier</title>
<style>
:root{--bg:#0f1720;--card:#18222e;--line:#2a3745;--fg:#e6edf3;--mut:#8b9aab;--acc:#4da3ff;--ok:#3fb950;--bad:#f85149;--warn:#d29922}
@media (prefers-color-scheme:light){:root{--bg:#f4f6f8;--card:#fff;--line:#d8dee4;--fg:#1f2328;--mut:#656d76;--acc:#0969da}}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
header{display:flex;align-items:center;gap:12px;padding:14px 20px;border-bottom:1px solid var(--line)}
h1{font-size:17px;margin:0;flex:1}h2{font-size:14px;margin:0 0 10px}
.pill{padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600;background:var(--line)}
.pill.connected{background:var(--ok);color:#fff}.pill.disconnected{background:var(--bad);color:#fff}.pill.connecting{background:var(--warn);color:#fff}
main{display:grid;grid-template-columns:minmax(320px,430px) 1fr;gap:16px;padding:16px 20px;max-width:1300px;margin:auto}
@media(max-width:850px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:16px}
label{display:block;margin:8px 0 2px;color:var(--mut);font-size:12px}
input[type=text],input[type=password],input[type=number],select{width:100%;padding:7px 9px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg)}
.chk{display:flex;gap:8px;align-items:center;margin:8px 0;color:var(--fg);font-size:14px}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
button{padding:7px 14px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
#msg{margin-top:8px;font-size:13px;min-height:18px}
#log{height:calc(100vh - 150px);min-height:300px;overflow:auto;font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace}
#log div{padding:2px 0;border-bottom:1px solid var(--line)}.t{color:var(--mut)}
.k-alert{color:var(--acc);font-weight:600}.k-error{color:var(--bad)}.k-notify{color:var(--ok)}.k-info{color:var(--mut)}
small{color:var(--mut)}
</style></head><body>
<header><h1>🛰 oscarwatch-notifier <small>v__VERSION__</small></h1><span id="url"></span><span id="pill" class="pill">…</span></header>
<main>
<div>
 <div class="card"><h2>Websocket</h2>
  <label for="ws">URL (default ws://localhost:7373)</label><input type="text" id="ws">
  <div class="chk"><input type="checkbox" id="dedupe"><span>Ignore repeated alerts for the same pass</span></div>
 </div>
 <div class="card"><h2>Pushover</h2>
  <div class="chk"><input type="checkbox" id="po_en"><span>Enabled</span></div>
  <label>App token</label><input type="password" id="po_app" autocomplete="off">
  <label>User key</label><input type="password" id="po_user" autocomplete="off">
  <label>Device (optional)</label><input type="text" id="po_dev">
  <label>Priority</label><select id="po_prio"><option value="-2">-2 lowest</option><option value="-1">-1 low</option><option value="0">0 normal</option><option value="1">1 high</option></select>
  <label>Sound (optional)</label><input type="text" id="po_sound" placeholder="e.g. pushover, siren">
 </div>
 <div class="card"><h2>DAPNET (hampager.de)</h2>
  <div class="chk"><input type="checkbox" id="da_en"><span>Enabled</span></div>
  <label>API URL</label><input type="text" id="da_url">
  <label>Username (callsign)</label><input type="text" id="da_user" autocomplete="off">
  <label>Password</label><input type="password" id="da_pw" autocomplete="off">
  <label>Destination callsigns (comma separated)</label><input type="text" id="da_calls">
  <label>Transmitter groups (comma separated)</label><input type="text" id="da_tx">
  <div class="chk"><input type="checkbox" id="da_emerg"><span>Emergency</span></div>
 </div>
 <div class="row"><button class="primary" id="save">Save settings</button><button id="test">Send test notification</button></div>
 <div id="msg"></div>
</div>
<div class="card"><h2>Activity</h2><div id="log"></div></div>
</main>
<script>
const $=id=>document.getElementById(id);
const list=s=>s.split(",").map(x=>x.trim()).filter(Boolean);
function say(t,bad){const m=$("msg");m.textContent=t;m.style.color=bad?"var(--bad)":"var(--ok)"}
async function api(path,body){
  const r=await fetch(path,body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
async function loadCfg(){
  const c=await api("/api/config"),n=c.notifiers||{},p=n.pushover||{},d=n.dapnet||{};
  $("ws").value=(c.websocket||{}).url||"";$("dedupe").checked=c.dedupe!==false;
  $("po_en").checked=p.enabled!==false&&!!n.pushover;$("po_app").value=p.app_token||"";$("po_user").value=p.user_key||"";
  $("po_dev").value=p.device||"";$("po_prio").value=String(p.priority??0);$("po_sound").value=p.sound||"";
  $("da_en").checked=d.enabled!==false&&!!n.dapnet;$("da_url").value=d.url||"http://hampager.de/api/calls";
  $("da_user").value=d.username||"";$("da_pw").value=d.password||"";
  $("da_calls").value=(d.callsigns||[]).join(", ");$("da_tx").value=(d.transmitter_groups||[]).join(", ");$("da_emerg").checked=!!d.emergency}
function form(){return{websocket:{url:$("ws").value},dedupe:$("dedupe").checked,notifiers:{
  pushover:{enabled:$("po_en").checked,app_token:$("po_app").value,user_key:$("po_user").value,device:$("po_dev").value,priority:+$("po_prio").value,sound:$("po_sound").value},
  dapnet:{enabled:$("da_en").checked,url:$("da_url").value,username:$("da_user").value,password:$("da_pw").value,callsigns:list($("da_calls").value),transmitter_groups:list($("da_tx").value),emergency:$("da_emerg").checked}}}}
$("save").onclick=async()=>{try{await api("/api/config",form());say("Saved.");loadCfg()}catch(e){say(e.message,true)}};
$("test").onclick=async()=>{say("Sending…");try{const r=await api("/api/test",{});
  if(!r.results.length)return say("No notifier is enabled (save settings first).",true);
  const bad=r.results.filter(x=>!x.ok);say(r.results.map(x=>x.name+": "+(x.ok?"OK":"FAILED - "+x.error)).join("  |  "),bad.length>0)}catch(e){say(e.message,true)}};
let last="";
async function poll(){try{const s=await api("/api/status");
  const p=$("pill");p.textContent=s.status;p.className="pill "+s.status;$("url").textContent=s.url;$("url").style.color="var(--mut)";
  const sig=JSON.stringify(s.events);if(sig!==last){last=sig;const l=$("log");const atBot=l.scrollTop+l.clientHeight>=l.scrollHeight-20;l.textContent="";
   s.events.forEach(e=>{const d=document.createElement("div"),t=document.createElement("span"),x=document.createElement("span");
    t.className="t";t.textContent=e.t+"  ";x.className="k-"+e.kind;x.textContent=e.text;d.append(t,x);l.append(d)});
   if(atBot)l.scrollTop=l.scrollHeight}}catch(e){$("pill").textContent="app offline";$("pill").className="pill disconnected"}}
loadCfg().catch(e=>say(e.message,true));poll();setInterval(poll,2000);
</script></body></html>"""
