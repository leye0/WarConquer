/* Body-independent humanoid contact landmarks for any held prop.
 * Every position comes from actual joint transforms, never a named unit,
 * global model axis, assumed body height or baked weapon rotation.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="undefined"||!module.exports)root.WCRigContact=api;
  else module.exports=api;
})(typeof globalThis==="object"?globalThis:this,function(){
  "use strict";
  const sub=(a,b)=>a.map((n,i)=>n-b[i]);
  const add=(a,b)=>a.map((n,i)=>n+b[i]);
  const mul=(a,n)=>a.map(v=>v*n);
  const dot=(a,b)=>a.reduce((n,v,i)=>n+v*b[i],0);
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const len=a=>Math.sqrt(dot(a,a));
  const unit=a=>{const n=len(a);return n>1e-6?mul(a,1/n):null;};
  const average=points=>mul(points.reduce(add,[0,0,0]),1/points.length);
  const horizontal=v=>unit([v[0],0,v[2]]);
  const valid=p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite);

  // The foot-to-toe directions reveal the REAL character forward axis, even
  // when the glTF importer rotates/mirrors the model or the avatar turns.
  function bodyFrame(joints){
    const f=[];
    for(const side of ["left","right"]){
      const foot=joints[side+"Foot"],toe=joints[side+"Toe"];
      if(valid(foot)&&valid(toe)){
        const v=horizontal(sub(toe,foot));
        if(v)f.push(v);
      }
    }
    if(!f.length)throw Error("No anatomical foot/toe forward landmarks");
    const forward=horizontal(average(f));
    if(!forward)throw Error("Ambiguous body forward landmarks");
    const right=unit(cross([0,1,0],forward));
    return {forward,right,up:[0,1,0]};
  }

  // Finger knuckles bound the palm: the holding position therefore adapts to
  // different hand sizes, rigs and animations without centimetre offsets.
  function palmFrame(joints,side,fraction=.5){
    if(!["left","right"].includes(side)||!Number.isFinite(fraction)||fraction<0||fraction>1)
      throw Error("Invalid hand side or palm fraction");
    const wrist=joints[side+"Wrist"],elbow=joints[side+"Elbow"];
    const index=joints[side+"Index"],middle=joints[side+"Middle"],pinky=joints[side+"Pinky"];
    if(![wrist,elbow,index,middle,pinky].every(valid))
      throw Error("Missing wrist/elbow/finger landmarks for "+side+" hand");
    const knuckles=average([index,middle,pinky]);
    const fingers=unit(sub(knuckles,wrist));
    const across=unit(sub(index,pinky));
    const normal=fingers&&across&&unit(cross(across,fingers));
    const towardElbow=unit(sub(elbow,wrist));
    if(!normal||!towardElbow)throw Error("Degenerate palm or forearm geometry");
    return {wrist,elbow,knuckles,grip:add(wrist,mul(sub(knuckles,wrist),fraction)),
      fingers,across,normal,towardElbow};
  }

  // Semantic bindings are *data* in an object's grip contract, not hard-coded
  // branches for axes, bows, swords or named characters.
  function resolveDirection(name,hand,body,side){
    const directions={
      toward_elbow:hand.towardElbow,
      toward_fingers:hand.fingers,
      palm_normal:hand.normal,
      back_of_hand:mul(hand.normal,-1),
      across_palm:hand.across,
      opposite_across_palm:mul(hand.across,-1),
      forward:body.forward,backward:mul(body.forward,-1),
      gravity:[0,-1,0],
      up:body.up,down:mul(body.up,-1),
      outward:side==="right"?body.right:mul(body.right,-1),
      inward:side==="right"?mul(body.right,-1):body.right
    };
    const direction=directions[name];
    if(!direction)throw Error("Unknown anatomical attachment direction: "+name);
    return direction;
  }

  function contactFrame(joints,{hand="right",palm_fraction=.5,
      shaft_direction="toward_elbow",working_face="forward"}={}){
    const palm=palmFrame(joints,hand,palm_fraction);
    const body=bodyFrame(joints);
    const shaft=resolveDirection(shaft_direction,palm,body,hand);
    const front=resolveDirection(working_face,palm,body,hand);
    const blade=unit(sub(front,mul(shaft,dot(front,shaft))));
    if(!blade)throw Error("Functional face is parallel to the shaft");
    return {grip:palm.grip,shaft,blade,palm,body};
  }
  return {bodyFrame,palmFrame,contactFrame,resolveDirection};
});
