#!/usr/bin/env node
// Live integration: the Perception Lab must load a combat-capable GLB, advance
// distance at its Mixamo gait cadence, visibly swing and apply melee damage.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {existsSync,mkdtempSync,readFileSync,mkdirSync,writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join,resolve,dirname} from "node:path";

const sleep=ms=>new Promise(ok=>setTimeout(ok,ms));
const profile=mkdtempSync(join(tmpdir(),"warconquer-perception-cdp-"));
const browser=spawn(process.env.CHROME_BIN||"/usr/bin/google-chrome",[
  "--headless=new","--no-sandbox","--enable-unsafe-swiftshader",
  "--disable-dev-shm-usage","--no-first-run","--no-default-browser-check",
  "--hide-scrollbars","--window-size=1280,800","--remote-debugging-port=0",
  "--user-data-dir="+profile,"about:blank"
],{stdio:"ignore"});
let socket,serial=0;
const pending=new Map();
async function socketUrl(){
  for(let i=0;i<250;i++){
    if(browser.exitCode!==null)throw Error("Chrome stopped");
    const file=join(profile,"DevToolsActivePort");
    if(existsSync(file)){
      try{
        const port=readFileSync(file,"utf8").split("\n")[0];
        const response=await fetch("http://127.0.0.1:"+port+"/json/list");
        const tabs=await response.json();
        const page=tabs.find(t=>t.type==="page");
        if(page?.webSocketDebuggerUrl)return page.webSocketDebuggerUrl;
      }catch{}
    }
    await sleep(100);
  }
  throw Error("Chrome CDP unavailable");
}
function request(method,params={}){
  return new Promise((done,fail)=>{
    const id=++serial;
    const timeout=setTimeout(()=>{pending.delete(id);fail(Error(method+" timeout"));},20000);
    pending.set(id,{done,fail,timeout});
    socket.send(JSON.stringify({id,method,params}));
  });
}
async function js(expression){
  const result=await request("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:false});
  if(result.exceptionDetails)throw Error("Browser JS error: "+JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}
async function status(){
  return js(`(()=>{
    const t=id=>document.getElementById(id)?.textContent?.trim()||"";
    const scene=window.BABYLON?.EngineStore.LastCreatedEngine?.scenes[0];
    const pose=scene?.getTransformNodeByName("scout-root")?.position;
    const walk=scene?.animationGroups?.find(g=>/^Walk[_ -]/i.test(g.name));
    return {badge:t("engineBadge"),unit:t("avatarInfo"),motion:t("animationState"),
      status:t("status"),hits:t("attackStatus"),events:t("eventList"),
      gait:t("gaitInfo"),position:pose?[pose.x,pose.z]:null,
      walkRatio:walk?.speedRatio||null,
      attackEnabled:!document.querySelector('[data-order="attack"]')?.disabled};
  })()`);
}
async function until(check,label,limit=20000){
  const end=Date.now()+limit;let last;
  while(Date.now()<end){
    last=await status();
    if(check(last))return last;
    await sleep(220);
  }
  throw Error("Timeout waiting for "+label+"; last="+JSON.stringify(last));
}
async function screenshot(name){
  const result=await request("Page.captureScreenshot",{format:"png",fromSurface:true});
  const file=resolve("assets/experiments/character-lab-qa/"+name+".png");
  mkdirSync(dirname(file),{recursive:true});
  writeFileSync(file,Buffer.from(result.data,"base64"));
  console.log("CAPTURE",name);
}
try{
  socket=new WebSocket(await socketUrl());
  await new Promise((ok,fail)=>{
    socket.addEventListener("open",ok,{once:true});
    socket.addEventListener("error",()=>fail(Error("CDP socket failed")),{once:true});
  });
  socket.addEventListener("message",e=>{
    const msg=JSON.parse(e.data),item=pending.get(msg.id);
    if(!item)return;
    pending.delete(msg.id);clearTimeout(item.timeout);
    msg.error?item.fail(Error(JSON.stringify(msg.error))):item.done(msg.result||{});
  });
  await request("Page.enable");await request("Runtime.enable");
  await request("Emulation.setDeviceMetricsOverride",
    {width:1280,height:800,deviceScaleFactor:1,mobile:false});
  await request("Page.navigate",{url:"http://127.0.0.1:4173/perception-lab.html"});
  const ready=await until(s=>s.badge.startsWith("GLB réel")&&
    s.unit.includes("Attack_Mixamo")&&s.attackEnabled,"combat-ready real Mixamo GLB",50000);
  assert(ready.unit.includes("Attack_Mixamo"),
    "Default avatar must expose a genuine melee clip: "+ready.unit);
  await screenshot("perception-real-idle-live");
  await js("document.getElementById('attackNearest').click()");
  await until(s=>s.status.includes("Ordre d'attaque"),"attack order accepted",6000);
  const walking=await until(s=>s.motion.includes("Walk_Mixamo")&&
    s.position?.some(n=>Math.abs(n)>.15),"real Mixamo walking to enemy",10000);
  const initial=walking.position;
  await sleep(680);
  const after=await status();
  const delta=Math.hypot(after.position[0]-initial[0],after.position[1]-initial[1]);
  assert(delta>.35&&delta<1.5,"World movement must be continuous and human-paced: "+delta);
  assert(after.walkRatio>.6&&after.walkRatio<1.5,
    "Walk playback should match distance: "+after.walkRatio);
  console.log("GAIT_PASS",JSON.stringify({delta,ratio:after.walkRatio,gait:after.gait}));
  await screenshot("perception-real-walk-live");
  const swinging=await until(s=>s.motion.startsWith("Attack_Mixamo"),
    "genuine Mixamo melee strike after approach",15000);
  assert(swinging.badge.startsWith("GLB réel"));
  console.log("ATTACK_CLIP_PASS",JSON.stringify(swinging));
  await sleep(350);
  await screenshot("perception-real-attack-live");
  const hit=await until(s=>s.events.includes("Coup porté")&&
    !s.hits.startsWith("0 "),"real attack deals health damage",10000);
  console.log("MELEE_DAMAGE_PASS",JSON.stringify(hit));
  await screenshot("perception-real-damage-live");
}catch(error){
  console.error("Perception live integration failed:",error?.stack||error);
  process.exitCode=1;
}finally{
  try{socket?.close();}catch{}
  browser.kill("SIGTERM");
}
