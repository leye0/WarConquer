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
  // The original Character Lab runs this Mixamo warrior at 2.7 m/s on walk
  // and 2.7 * 1.75 m/s on run, with unmodified animation playback.
  // Preserve that observed visual cadence: at 1.9 m height and a 1.233 s
  // walk cycle this is ~3.33 m per animation cycle, not the former 1.71 m.
  const FACTOR={walk:1.75,run:2};
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
