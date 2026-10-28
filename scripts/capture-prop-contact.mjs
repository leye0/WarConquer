#!/usr/bin/env node
/* Generic browser capture of ANY rigged unit and held prop in the actual Lab.
 * The screenshots, not mathematical assertions, go to the vision GO/NO-GO gate.
 */
import {spawn} from "node:child_process";
import {existsSync,mkdtempSync,readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {join,resolve} from "node:path";
import {tmpdir} from "node:os";

const [unit,prop,out]=process.argv.slice(2);
if(!/^[a-z][a-z0-9_]*$/.test(unit||"") || !/^[a-z][a-z0-9_]*$/.test(prop||"")||!out)
  throw Error("Usage: node scripts/capture-prop-contact.mjs <unit> <prop> <output-directory>");
const output=resolve(out);
mkdirSync(output,{recursive:true});
const profile=mkdtempSync(join(tmpdir(),"wc-contact-chrome-"));
const browser=spawn(process.env.CHROME_BIN||"google-chrome",[
  "--headless=new","--no-sandbox","--enable-unsafe-swiftshader",
  "--disable-dev-shm-usage","--no-first-run","--window-size=1280,800",
  "--remote-debugging-port=0","--user-data-dir="+profile,"about:blank"
],{stdio:"ignore"});
const sleep=ms=>new Promise(done=>setTimeout(done,ms));
let socket,serial=0;
const pending=new Map();
const request=(method,params={})=>new Promise((done,fail)=>{
  const id=++serial;
  const timeout=setTimeout(()=>{pending.delete(id);fail(Error(method+" timeout"));},20000);
  pending.set(id,{done,fail,timeout});
  socket.send(JSON.stringify({id,method,params}));
});
async function debuggerSocket(){
  for(let t=0;t<200;t++){
    if(browser.exitCode!==null)throw Error("Chrome unavailable");
    const portFile=join(profile,"DevToolsActivePort");
    if(existsSync(portFile)){
      try{
        const port=readFileSync(portFile,"utf8").split("\n")[0];
        const tabs=await(await fetch("http://127.0.0.1:"+port+"/json/list")).json();
        const page=tabs.find(x=>x.type==="page");
        if(page?.webSocketDebuggerUrl)return page.webSocketDebuggerUrl;
      }catch{}
    }
    await sleep(100);
  }
  throw Error("Chrome DevTools connection not ready");
}
const js=async expression=>{
  const result=await request("Runtime.evaluate",{expression,returnByValue:true});
  if(result.exceptionDetails)throw Error("Browser evaluation failed: "+expression.slice(0,90));
  return result.result?.value;
};
async function capture(name,{worldOnly=false}={}){
  await sleep(550);
  const options={format:"png",fromSurface:true};
  if(worldOnly){
    const box=await js(`(()=>{const r=document.getElementById('world')
      .getBoundingClientRect();return {x:Math.max(0,Math.floor(r.left)),
        y:Math.max(0,Math.floor(r.top)),
        width:Math.floor(Math.min(r.width,innerWidth-r.left)),
        height:Math.floor(Math.min(r.height,innerHeight-r.top)),scale:1}})()`);
    options.clip=box;
    options.captureBeyondViewport=false;
  }
  const result=await request("Page.captureScreenshot",options);
  const file=join(output,name+".png");
  writeFileSync(file,Buffer.from(result.data,"base64"));
  console.log("CONTACT_CAPTURE",name,file);
}
async function camera(angle){
  await js(`(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;
    const c=e?.scenes?.[0]?.activeCamera;if(!c)throw Error('camera');
    c.alpha=${angle};c.beta=Math.PI/2.12;c.setTarget(new BABYLON.Vector3(0,1.1,0));
    c.lowerRadiusLimit=2.8;c.radius=4.5;
    document.getElementById('world').scrollIntoView({block:'center'});
    return true})()`);
}
async function closeView(name){
  // A whole-page image makes the shaft/hand contacts a few pixels wide.
  // Give vision a genuine HIGHER-SAMPLING Babylon camera projection and the
  // actual 3D canvas crop, not an AI-upscaled or invented annotation.
  await js(`(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;
    const c=e.scenes[0].activeCamera;c.lowerRadiusLimit=1.7;
    c.radius=2.45;return true})()`);
  await capture(name,{worldOnly:true});
  await js(`(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;
    e.scenes[0].activeCamera.radius=4.5;return true})()`);
}
try{
  socket=new WebSocket(await debuggerSocket());
  await new Promise((done,fail)=>{
    socket.addEventListener("open",done,{once:true});
    socket.addEventListener("error",()=>fail(Error("CDP socket failed")),{once:true});
  });
  socket.addEventListener("message",event=>{
    const msg=JSON.parse(event.data),pendingRequest=pending.get(msg.id);
    if(!pendingRequest)return;
    pending.delete(msg.id);clearTimeout(pendingRequest.timeout);
    msg.error?pendingRequest.fail(Error(JSON.stringify(msg.error))):pendingRequest.done(msg.result||{});
  });
  await request("Page.enable");await request("Runtime.enable");
  await request("Emulation.setDeviceMetricsOverride",{width:1280,height:800,
    deviceScaleFactor:1,mobile:false});
  const url="http://127.0.0.1:4173/character-lab.html?unit="+
    encodeURIComponent(unit)+"&prop="+encodeURIComponent(prop);
  await request("Page.navigate",{url});
  let ready=false,last="";
  for(let i=0;i<150;i++){
    await sleep(320);
    const state=await js(`(()=>{const world=document.getElementById('world');
      return {unit:world?.dataset.unitId||'',grip:world?.dataset.weaponGrip||'',
      weapon:document.getElementById('weaponMetric')?.textContent||'',
      attack:!document.getElementById('attackButton')?.disabled}})()`);
    last=JSON.stringify(state);
    if(state.unit===unit && state.grip==="vision-glb-anatomical-landmarks"){
      ready=true;break;
    }
    if(state.weapon.startsWith("Prise refusée"))throw Error(state.weapon);
  }
  if(!ready)throw Error("Rig not ready with generic prop contact: "+last);
  const diagnostics=await js(`(()=>{const d=document.getElementById('world').dataset;
    return {carry:d.weaponCarry||'unknown',tilt:Number(d.weaponCarryTilt||0),
      clearance:Number(d.weaponCarryClearance||0),
      actualClearance:Number(d.weaponActualClearance||0),
      bodyRadius:Number(d.weaponBodyRadius||0),
      balanceY:Number(d.weaponBalanceY||0),
      gripError:Number(d.weaponGripError||0),
      workingFace:Number(d.weaponWorkingFace||0)}})()`);
  writeFileSync(join(output,"contact-state.json"),JSON.stringify({unit,prop,...diagnostics})+"\n");
  console.log("CONTACT_STATE",JSON.stringify({unit,prop,...diagnostics}));
  const motionStates=[];
  const numericFailures=[];
  const checkFrame=async name=>{
    const result=await js("window.WCPropContactDiagnostic?.()||null");
    if(!result)throw Error("No live articulated prop contact diagnostic: "+name);
    motionStates.push({name,...result});
    console.log("CONTACT_FRAME",name,JSON.stringify(result));
    if(result.semanticStatus==="rejected")
      numericFailures.push(name+": "+result.reason);
    if(!Number.isFinite(result.gripError)||result.gripError>.045)
      numericFailures.push(name+": primary vision grip does not touch animated palm");
    if(result.expectedHands===2&&(!Number.isFinite(result.secondaryGripError)||
       result.secondaryGripError>.045||result.ikReachable!==true))
      numericFailures.push(name+": secondary labelled grip not held by real Mixamo arm");
    // A pair of palms touching a rigid object is not a valid held-object pose
    // if the true mesh penetrates the anatomical torso. Record every failing
    // frame and still capture its screenshot for an independent visual judge.
    if(["idle","walk","run"].includes(name)&&Number.isFinite(result.clearance)&&
       result.clearance<-.015)
      numericFailures.push(name+": prop intersects the torso by "+
        (-result.clearance).toFixed(3)+" m");
    if(name.startsWith("action")&&result.semanticStatus==="confirmed"){
      if(result.expectedHands===2&&
         (!Number.isFinite(result.secondaryGripError)||result.secondaryGripError>.045||
          result.ikReachable!==true))
        numericFailures.push(name+": wrong active secondary hand contact");
      if(!Number.isFinite(result.actionForwardError)||result.actionForwardError>.3)
        numericFailures.push(name+": functional action surface points away from target");
    }
    if(diagnostics.carry==="mass-below-hand"&&["idle","walk","run"].includes(name) &&
      (result.balanceY>=0||result.clearance<-.015||result.edgeOutward<-.15))
      numericFailures.push(name+": one-hand carry violates its physical contract");
    return result;
  };
  await checkFrame("idle");
  await camera(Math.PI/2);await capture("front");await closeView("front_grip");
  await camera(0);await capture("side");await closeView("side_grip");
  await camera(-Math.PI/2);await capture("back");await closeView("back_grip");
  const down=(key,code,virtualKey)=>request("Input.dispatchKeyEvent",{
    type:"rawKeyDown",key,code,windowsVirtualKeyCode:virtualKey});
  const up=(key,code,virtualKey)=>request("Input.dispatchKeyEvent",{
    type:"keyUp",key,code,windowsVirtualKeyCode:virtualKey});
  await camera(0);
  await down("w","KeyW",87);await sleep(500);
  await checkFrame("walk");await capture("walk");await closeView("walk_grip");
  await down("Shift","ShiftLeft",16);await sleep(500);
  await checkFrame("run");await capture("run");await closeView("run_grip");
  await up("Shift","ShiftLeft",16);await up("w","KeyW",87);
  await sleep(280);
  if(await js("!document.getElementById('attackButton').disabled")){
    await js("document.getElementById('attackButton').click()");
    // The real Mixamo group is paused and sampled by exact normalized
    // animation frames. Neither snapshots nor verdicts depend on wall-clock
    // timing or an exported video.
    const actionGroup=await js(`(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;
      const name=document.getElementById('activeMotionMetric')?.textContent;
      const g=e?.scenes?.[0]?.animationGroups?.find(x=>x.name===name);
      if(!g)throw Error('Cannot identify live action animation group');
      g.pause();return {name,from:g.from,to:g.to};})()`);
    const frames=[0,.15,.3,.45,.6,.75,.9,1];
    for(let i=0;i<frames.length;i++){
      const fraction=frames[i];
      await js(`(()=>{const e=BABYLON.EngineStore.LastCreatedEngine;
        const g=e.scenes[0].animationGroups.find(x=>x.name===${JSON.stringify(actionGroup.name)});
        if(!g)throw Error('Sampled Mixamo animation disappeared');
        g.goToFrame(g.from+(g.to-g.from)*${fraction});return true})()`);
      await sleep(180);
      const name=i===0?"action":i===4?"action_mid":"action_mid_"+i;
      await checkFrame(name);
      await capture(name);
      if([0,2,4,6].includes(i))await closeView(name+"_grip");
    }
    console.log("CONTACT_ACTION_SAMPLES",JSON.stringify({clip:actionGroup,normalizedFrames:frames}));
  }
  writeFileSync(join(output,"contact-motions.json"),JSON.stringify(motionStates,null,2)+"\n");
  writeFileSync(join(output,"contact-numeric-verdict.json"),JSON.stringify({
    status:numericFailures.length?"rejected":"approved",issues:numericFailures,
    checked_frames:motionStates.map(x=>x.name)},null,2)+"\n");
  if(numericFailures.length)throw Error("Real Mixamo contact/clearance NO-GO: "+
    numericFailures.join("; "));
  console.log("PASS: real animated humanoid holds requested prop in three browser views");
}finally{
  try{socket?.close();}catch{}
  browser.kill("SIGTERM");
}
