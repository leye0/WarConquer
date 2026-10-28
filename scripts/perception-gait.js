/* WarConquer: animation-cadence calibration in world metres.
 * One animation cycle covers an estimated stride scaled to avatar height.
 * Browser/GLB-independent so gameplay and tests share the same contract.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.WCGait=api;
})(typeof globalThis==="object"?globalThis:this,function(){
  "use strict";
  const FACTOR={walk:.9,run:1.5};
  function duration(clip){
    const fps=clip?.targetedAnimations?.find(t=>t.animation?.framePerSecond>0)
      ?.animation?.framePerSecond||30;
    const frames=(clip?.to??NaN)-(clip?.from??NaN);
    return Number.isFinite(frames)&&frames>0?frames/fps:null;
  }
  function stride(kind,{height=1.9,scale=1}={}){
    if(!Object.hasOwn(FACTOR,kind))return null;
    if(!Number.isFinite(height)||height<=0||!Number.isFinite(scale)||scale<=0)
      return null;
    return height*FACTOR[kind]*scale;
  }
  function nominalSpeed(kind,clip,settings){
    const metres=stride(kind,settings),seconds=duration(clip);
    return metres&&seconds?metres/seconds:null;
  }
  function playbackRatio(kind,clip,actualSpeed,settings){
    const nominal=nominalSpeed(kind,clip,settings);
    return nominal&&Number.isFinite(actualSpeed)&&actualSpeed>=0?
      Math.min(3,Math.max(.05,actualSpeed/nominal)):1;
  }
  return {duration,stride,nominalSpeed,playbackRatio};
});
