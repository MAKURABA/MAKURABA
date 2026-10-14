/* Hub view: draws the index lists from window.HUB (written by hub.py between the hub:data markers). */
const H=window.HUB||{menu:[]};
if(H.title)document.title=H.title;
const HUES=[355,222,275,150,32,190];
const panel=t=>{const s=el("section","glass");if(t)s.append(el("h2","",t));return s};
const count=n=>n+(n===1?" item":" items");
const hash=ids=>"#"+ids.map(encodeURIComponent).join("/");
function groupRow(n,path,hue){const a=el("a","row");a.href=hash(path);
  const g=el("span","gem");g.style.setProperty("--h",hue);g.style.setProperty("--d",(hue%7)*.7+"s");
  const tx=el("span","tx");tx.append(el("div","n",n.title));if(n.summary)tx.append(el("div","d",n.summary));
  a.append(g,tx,el("span","c",count(n.items.length)));a.insertAdjacentHTML("beforeend","<svg viewBox='0 0 16 16'><path d='M5 2l6 6-6 6'/></svg>");return a}
function leafRow(n){const r=el(n.href?"a":"div","entry");
  if(n.href){r.href=n.href;if(n.external){r.target="_blank";r.rel="noopener"}}
  const l=el("div"),t=el("div","n",n.title);t.style.cssText="font:500 18px/1.2 Jost,sans-serif;letter-spacing:.06em";l.append(t);
  if(n.summary){const d=el("div","d",n.summary);d.style.cssText="color:var(--mute);font-size:15px";l.append(d)}
  r.append(l);if(n.status)r.append(el("span","tag",n.status));return r}
function render(){
  const p=decodeURIComponent(location.hash.replace(/^#\/?/,"")).split("/").filter(Boolean),v=$("view");v.innerHTML="";
  const sec=H.menu.find(m=>m.id===p[0]&&m.type==="index"),home=!sec;
  $("stage").classList.toggle("dim",!home);
  document.querySelectorAll("#nav a").forEach(a=>a.setAttribute("aria-current",a.dataset.id===(home?"home":sec.id)));
  if(home){const c=el("div","cap");c.append(el("b"));v.append(c);return}
  let list=sec.items,trail=[];
  for(const id of p.slice(1)){const n=list.find(x=>x.id===id&&x.items);if(!n)break;trail.push(n);list=n.items}
  const ids=[sec.id,...trail.map(t=>t.id)],ti=trail.length?sec.items.indexOf(trail[0]):-1;
  if(trail.length){const b=el("a","crumb","\u2039 "+(trail.length>1?trail[trail.length-2].title:sec.label));b.href=hash(ids.slice(0,-1));v.append(b)}
  const cur=trail[trail.length-1],s=panel(cur?cur.title:sec.label);
  if(cur&&cur.summary){const d=el("div","pad");d.append(el("p","",cur.summary));s.append(d)}
  if(!list.length)s.append(el("div","pad","Nothing here yet."));
  list.forEach((n,i)=>{if(n.items){const hue=n.hue??(trail.length?(trail[0].hue??HUES[ti%6]):HUES[i%6]);s.append(groupRow(n,[...ids,n.id],hue))}else s.append(leafRow(n))});
  v.append(s);v.scrollTop=0}
addEventListener("hashchange",render);render();
