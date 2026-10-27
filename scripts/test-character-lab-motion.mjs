#!/usr/bin/env node
// Browser-level integration test: actual imported Mixamo clips must respond to
// idle / held W / held Shift+W / attack, with a live Babylon canvas.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";

const sleep=ms=>new Promise(ok=>setTimeout(ok,ms));
const profile=mkdtempSync(join(tmpdir(),"warconquer-chrome-motion-"));
const browser=spawn(process.env.CHROME_BIN||"/usr/bin/google-chrome",[
  "--headless=new","--no-sandbox","--enable-unsafe-swiftshader",
  "--disable-dev-shm-usage","--no-first-run","--no-default-browser-check",
  "--hide-scrollbars","--window-size=1280,800",
  "--remote-debugging-port=0","--user-data-dir="+profile,"about:blank"
],{stdio:"ignore"});
let socket,serial=0;
const pending=new Map();
function request(method,params={}) {
  return new Promise((done,fail)=>{
    const id=++serial;
    const timeout=setTimeout(()=>{pending.delete(id);fail(new Error(method+" timed out"));},15000);
    pending.set(id,{done,fail,timeout});
    socket.send(JSON.stringify({id,method,params}));
  });
}
async function getSocket() {
  const portFile=join(profile,"DevToolsActivePort");
  for(let t=0;t<250;t++){
    if(browser.exitCode!==null)throw Error("Chrome exited before CDP setup");
    if(existsSync(portFile)){
      try{
        const port=readFileSync(portFile,"utf8").split("\n")[0];
        const targets=await (await fetch("http://127.0.0.1:"+port+"/json/list")).json();
        const page=targets.find(x=>x.type==="page");
        if(page?.webSocketDebuggerUrl)return page.webSocketDebuggerUrl;
      }catch{}
    }
    await sleep(100);
  }
  throw Error("Chrome CDP port never became ready");
}
async function js(expression) {
  const answer=await request("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:false});
  if(answer.exceptionDetails)throw Error("Browser JS evaluation failed");
  return answer.result?.value;
}
async function state() {
  return js(`(()=>{const t=id=>document.getElementById(id)?.textContent?.trim()||"";
  return {motion:t("activeMotionMetric"),clips:t("clipMetric"),walk:t("walkMetric"),
  movement:t("movementMetric"),position:t("positionMetric"),status:t("statusText"),
  canvas:!!document.getElementById("world")}})()`);
}
async function until(check,label,timeout=30000) {
  const end=Date.now()+timeout;let last;
  while(Date.now()<end){
    last=await state();
    if(check(last))return last;
    await sleep(330);
  }
  throw Error("Timed out waiting for "+label+"; last="+JSON.stringify(last));
}
async function down(key,code,virtualKey){
  await request("Input.dispatchKeyEvent",{type:"rawKeyDown",key,code,windowsVirtualKeyCode:virtualKey});
}
async function up(key,code,virtualKey){
  await request("Input.dispatchKeyEvent",{type:"keyUp",key,code,windowsVirtualKeyCode:virtualKey});
}
async function screenshot(name) {
  const result=await request("Page.captureScreenshot",{format:"png",fromSurface:true});
  const output=resolve("assets/experiments/character-lab-qa/"+name+".png");
  mkdirSync(dirname(output),{recursive:true});
  writeFileSync(output,Buffer.from(result.data,"base64"));
  console.log("CAPTURE",name,output);
}
try {
  socket=new WebSocket(await getSocket());
  await new Promise((ok,fail)=>{
    socket.addEventListener("open",ok,{once:true});
    socket.addEventListener("error",()=>fail(Error("WebSocket CDP connection failed")),{once:true});
  });
  socket.addEventListener("message",event=>{
    const m=JSON.parse(event.data);
    const p=pending.get(m.id);
    if(!p)return;
    pending.delete(m.id);clearTimeout(p.timeout);
    m.error?p.fail(Error(JSON.stringify(m.error))):p.done(m.result||{});
  });
  await request("Page.enable");
  await request("Runtime.enable");
  await request("Emulation.setDeviceMetricsOverride",{
    width:1280,height:800,deviceScaleFactor:1,mobile:false
  });
  await request("Page.navigate",{url:"http://127.0.0.1:4173/character-lab.html"});
  const initial=await until(s=>s.motion.startsWith("Idle_")&&
    s.clips.includes("Walk_Mixamo")&&s.clips.includes("Run_Mixamo")&&
    s.clips.includes("Attack_Mixamo")&&s.walk.includes("Marche ET course"),
    "four genuine Mixamo clips and active Idle",40000);
  assert(initial.canvas);
  console.log("IDLE_PASS",JSON.stringify(initial));
  const before=initial.position;
  await down("w","KeyW",87);
  const walking=await until(s=>s.motion.startsWith("Walk_Mixamo")&&
    s.movement==="EN DÉPLACEMENT"&&s.position!==before,
    "walk motion + actual WASD displacement",10000);
  console.log("WALK_PASS",JSON.stringify(walking));
  await sleep(750);
  await screenshot("walk-live");
  await down("Shift","ShiftLeft",16);
  const running=await until(s=>s.motion.startsWith("Run_Mixamo"),
    "genuine running motion with Shift+W",10000);
  console.log("RUN_PASS",JSON.stringify(running));
  await sleep(550);
  await screenshot("run-live");
  await up("Shift","ShiftLeft",16);
  await up("w","KeyW",87);
  await until(s=>s.motion.startsWith("Idle_Mixamo")&&s.movement==="IMMOBILE",
    "return to Idle on release",10000);
  await js("document.getElementById('attackButton').click()");
  const attacking=await until(s=>s.motion.startsWith("Attack_Mixamo"),
    "real Mixamo axe attack",10000);
  console.log("ATTACK_PASS",JSON.stringify(attacking));
  await sleep(300);
  await screenshot("attack-live");
  const falUrl=await js("(()=>{const d=document.getElementById('modelSelect');const o=Array.from(d.options).find(x=>x.textContent.includes('fal.ai'));if(!o)return '';d.value=o.value;d.dispatchEvent(new Event('change',{bubbles:true}));return d.value;})()");
  assert(falUrl.includes("fal-textured.glb"),"fal pilot missing from selector");
  const fal=await until(s=>s.status.startsWith("Prêt")&&
    s.walk.startsWith("Marche absente")&&s.motion==="Aucune animation",
    "separate fal UV-textured unrigged pilot in Babylon",45000);
  console.log("FAL_PILOT_PASS",JSON.stringify(fal));
  await sleep(1000);
  await screenshot("fal-textured-isometric-live");
  for(const [label,angle] of [["front",Math.PI/2],["back",-Math.PI/2]]) {
    await js("(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;const c=e.scenes[0].activeCamera;const aspect=e.getRenderWidth()/e.getRenderHeight();c.alpha="+angle+";c.beta=Math.PI/2.12;c.orthoTop=1.6;c.orthoBottom=-1.6;c.orthoLeft=-1.6*aspect;c.orthoRight=1.6*aspect;return true})()");
    await sleep(650);
    await screenshot("fal-textured-"+label+"-live");
  }
  console.log("PASS: Mixamo WASD/attack + separate fal.ai textured-GLB render captures");
} finally {
  try{socket?.close();}catch{}
  browser.kill("SIGTERM");
}
