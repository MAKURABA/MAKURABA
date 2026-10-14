/* Shared by the hub and every page: drawer behaviour and glass light. */
const $=id=>document.getElementById(id);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
function setOpen(o){document.body.classList.toggle("open",o);$("burger").setAttribute("aria-expanded",o)}
$("burger").onclick=$("tab").onclick=()=>setOpen(!document.body.classList.contains("open"));
$("scrim").onclick=()=>setOpen(false);
addEventListener("keydown",e=>{if(e.key==="Escape")setOpen(false)});
$("nav").addEventListener("click",e=>{if(e.target.closest("a")&&innerWidth<900)setOpen(false)});
setOpen(innerWidth>=900);
addEventListener("pointermove",e=>{const g=e.target.closest&&e.target.closest(".glass");if(!g)return;const r=g.getBoundingClientRect();
  g.style.setProperty("--mx",(e.clientX-r.left)+"px");g.style.setProperty("--my",(e.clientY-r.top)+"px")},{passive:true});
