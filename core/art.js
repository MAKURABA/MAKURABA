/* Background: gold-spark glints + WebGL cloud/gold shader. Needs core/hub.js loaded first. */
const PK=[[0.1678, 0.2901, "217,68,255"], [0.4959, 0.372, "255,225,165"], [0.5033, 0.5078, "255,242,186"], [0.2622, 0.5935, "255,191,138"], [0.2565, 0.3901, "255,199,87"], [0.7394, 0.5961, "255,189,108"], [0.7394, 0.3901, "243,255,209"], [0.4984, 0.2884, "255,160,101"], [0.8339, 0.2974, "255,197,103"], [0.5008, 0.675, "59,149,255"], [0.4992, 0.2147, "255,229,139"], [0.4984, 0.3302, "255,71,228"], [0.6327, 0.4651, "98,133,255"], [0.5, 0.4668, "255,181,103"], [0.8339, 0.6711, "255,195,95"], [0.7972, 0.4974, "162,53,255"], [0.3371, 0.5953, "255,141,108"], [0.8559, 0.4302, "255,66,52"]],AW=1228,AH=2320;
function sparks(){const s=$("spk"),w=s.clientWidth,h=s.clientHeight;s.innerHTML="";
  const land=matchMedia("(min-aspect-ratio:1/1)").matches,k=land?h/AH:Math.max(w/AW,h/AH),ox=(w-AW*k)/2,oy=(h-AH*k)/2;
  PK.forEach((p,i)=>{const e=el("b","sp");e.style.left=(ox+p[0]*AW*k)+"px";e.style.top=(oy+p[1]*AH*k)+"px";
    e.style.setProperty("--c","rgba("+p[2]+",.55)");e.style.setProperty("--d",((i*1.37)%6).toFixed(2)+"s");s.append(e)})}
addEventListener("resize",sparks);sparks();



/* Living background: the artwork drawn by a WebGL shader. Cloud brightness drifts in noise;
   a mask of the gold linework gets travelling light. Falls back to the still image. */
(function(){
  const cv=document.querySelector("#art canvas"),AW0=1228,AH0=2320;
  const gl=cv.getContext("webgl",{antialias:false,alpha:false,powerPreference:"low-power"});if(!gl){cv.remove();return}
  const still=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fs=`#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform sampler2D img,msk;uniform vec2 res,off;uniform float k,t;
vec2 hs(vec2 p){vec3 q=fract(vec3(p.xyx)*vec3(.1031,.1030,.0973));q+=dot(q,q.yzx+33.33);return fract((q.xx+q.yz)*q.zy)*2.-1.;}
float gn(vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*f*(f*(f*6.-15.)+10.);
  return mix(mix(dot(hs(i),f),dot(hs(i+vec2(1.,0.)),f-vec2(1.,0.)),u.x),mix(dot(hs(i+vec2(0.,1.)),f-vec2(0.,1.)),dot(hs(i+vec2(1.,1.)),f-vec2(1.)),u.x),u.y);}
const mat2 R=mat2(.8,.6,-.6,.8);
float fbm(vec2 p,float t){float v=0.,a=.5;
  for(int i=0;i<5;i++){float fi=float(i);v+=a*gn(p+vec2(cos(fi*2.1),sin(fi*2.1))*t*(.03+.018*fi));p=R*p*2.03+vec2(17.1,9.7);a*=.5;}
  return v;}
void main(){
  vec2 a=vec2(gl_FragCoord.x-off.x,res.y-gl_FragCoord.y-off.y)/k;
  vec2 uv=a/vec2(${AW0}.,${AH0}.);
  if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.){gl_FragColor=vec4(0.,0.,0.,1.);return;}
  vec3 c=texture2D(img,uv).rgb;float m=texture2D(msk,uv).r;
  vec2 p=uv*vec2(2.1,3.9);
  vec2 w=vec2(gn(p*.6+vec2(t*.02,t*.016)),gn(p*.6+vec2(5.2-t*.017,1.3+t*.022)));
  float q=fbm(p+w*1.1,t)*1.45+.5;
  float f=mix(.42,1.45,smoothstep(.12,.88,q));
  c*=mix(f,1.,m*.85);
  vec2 d=(uv-.5)*vec2(1.,${(AH0/AW0).toFixed(5)});float R=length(d),An=atan(d.y,d.x);
  float w1=pow(.5+.5*sin(An*2.-t*.8),4.),w2=pow(.5+.5*sin(R*15.-t*1.2),3.);
  float g=m*(.3+1.0*w1+.55*w2+.3*(.5+.5*sin(t*.9)));
  c+=vec3(1.,.78,.36)*g*.7;
  c+=(fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453)-.5)/160.;gl_FragColor=vec4(c,1.);}`;
  function sh(ty,s){const o=gl.createShader(ty);gl.shaderSource(o,s);gl.compileShader(o);return o}
  const pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,"attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}"));
  gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);
  if(!gl.getProgramParameter(pr,gl.LINK_STATUS)){cv.remove();return}
  gl.useProgram(pr);gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const lc=gl.getAttribLocation(pr,"a");gl.enableVertexAttribArray(lc);gl.vertexAttribPointer(lc,2,gl.FLOAT,false,0,0);
  const U=n=>gl.getUniformLocation(pr,n);
  function tex(src,unit,name){const i=new Image(),T=gl.createTexture();
    return new Promise(ok=>{i.onload=()=>{try{gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,T);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,i);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.uniform1i(U(name),unit);ok(true)}catch(e){ok(false)}};i.onerror=()=>ok(false);i.src=src})}
  const cosSrc="core/assets/cosmos.jpg";
  function size(){const dpr=Math.min(devicePixelRatio||1,1.5),w=Math.max(2,Math.round(cv.clientWidth*dpr)),h=Math.max(2,Math.round(cv.clientHeight*dpr));
    cv.width=w;cv.height=h;gl.viewport(0,0,w,h);
    const land=matchMedia("(min-aspect-ratio:1/1)").matches,k=land?h/AH0:Math.max(w/AW0,h/AH0);
    gl.uniform2f(U("res"),w,h);gl.uniform2f(U("off"),(w-AW0*k)/2,(h-AH0*k)/2);gl.uniform1f(U("k"),k);}
  const ut=U("t");let last=0;
  function frame(ms){gl.uniform1f(ut,still?3:ms/1000+3);gl.drawArrays(gl.TRIANGLES,0,3);
    if(!still&&!document.hidden)requestAnimationFrame(frame);else if(!still)document.addEventListener("visibilitychange",()=>requestAnimationFrame(frame),{once:true})}
  Promise.all([tex(cosSrc,0,"img"),tex("core/assets/mask.jpg",1,"msk")]).then(r=>{
    if(!r[0]||!r[1]){cv.remove();return}
    size();new ResizeObserver(()=>{size();gl.drawArrays(gl.TRIANGLES,0,3)}).observe(cv);requestAnimationFrame(frame)});
  cv.addEventListener("webglcontextlost",e=>{e.preventDefault();cv.style.display="none"});
})();

