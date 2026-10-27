/* Shared WarConquer arena: Character Lab and Perception Lab use the same scene.
 * Babylon is supplied by the HTML page; no npm packages or AI calls.
 */
(function(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.WCArena = api;
})(typeof globalThis === "object" ? globalThis : this, function() {
  "use strict";
  const STONES = Object.freeze([
    {id:"rock-1",x:-6,z:-4,radius:.7},
    {id:"rock-2",x:6,z:4,radius:.5},
    {id:"rock-3",x:-4,z:7,radius:.8},
    {id:"rock-4",x:7,z:-6,radius:.65},
    {id:"rock-5",x:-8,z:5,radius:.5},
    {id:"rock-6",x:3,z:9,radius:.45}
  ]);
  function create(canvas, B) {
    if (!canvas || !B) throw new Error("Arena requires a canvas and Babylon.js");
    const engine = new B.Engine(canvas, true, {preserveDrawingBuffer:true,stencil:true});
    const scene = new B.Scene(engine);
    scene.clearColor = B.Color4.FromHexString("#141b24ff");
    scene.ambientColor = new B.Color3(.43,.47,.53);
    const camera = new B.ArcRotateCamera("isometric", -Math.PI/4, Math.PI/3.25,
      13, new B.Vector3(0,.9,0),scene);
    camera.mode = B.Camera.ORTHOGRAPHIC_CAMERA;
    camera.lowerBetaLimit=.45;camera.upperBetaLimit=1.37;
    camera.lowerRadiusLimit=6;camera.upperRadiusLimit=23;
    camera.wheelPrecision=60;
    camera.panningSensibility=0;
    camera.attachControl(canvas,true);
    scene.activeCamera=camera;
    const sun=new B.DirectionalLight("sun",new B.Vector3(-.6,-1,-.5),scene);
    sun.position=new B.Vector3(9,13,7);sun.intensity=1.8;
    const sky=new B.HemisphericLight("ambient",new B.Vector3(0,1,0),scene);
    sky.intensity=.85;
    sky.groundColor=new B.Color3(.28,.31,.32);
    const ground=B.MeshBuilder.CreateGround("terrain",{width:32,height:32},scene);
    const groundMat=new B.StandardMaterial("groundMaterial",scene);
    groundMat.diffuseColor=new B.Color3(.23,.30,.27);
    groundMat.specularColor=B.Color3.Black();
    ground.material=groundMat;ground.receiveShadows=true;
    const lines=[];
    for(let i=-16;i<=16;i++){
      lines.push([new B.Vector3(-16,.009,i),new B.Vector3(16,.009,i)]);
      lines.push([new B.Vector3(i,.009,-16),new B.Vector3(i,.009,16)]);
    }
    const grid=B.MeshBuilder.CreateLineSystem("terrainGrid",{lines},scene);
    grid.color=new B.Color3(.33,.41,.36);grid.alpha=.52;
    const shadow=new B.ShadowGenerator(1024,sun);
    shadow.useBlurExponentialShadowMap=true;shadow.blurKernel=12;
    for(const p of STONES){
      const stone=B.MeshBuilder.CreateSphere(p.id,{diameter:1,segments:6},scene);
      stone.position=new B.Vector3(p.x,p.radius*.33,p.z);
      stone.scaling=new B.Vector3(p.radius*1.2,p.radius*.52,p.radius*.8);
      const mat=new B.StandardMaterial("stoneGray",scene);
      mat.diffuseColor=new B.Color3(.36,.42,.40);
      mat.specularColor=B.Color3.Black();
      stone.material=mat;stone.receiveShadows=true;
      stone.metadata={arenaObjectId:p.id,kind:"obstacle"};
    }
    const markers=[
      [[-2.6,0,0],[-1.3,0,0]],[[1.3,0,0],[2.6,0,0]],
      [[0,0,-2.6],[0,0,-1.3]],[[0,0,1.3],[0,0,2.6]]
    ];
    const accent=B.MeshBuilder.CreateLineSystem("spawnMarks",{
      lines:markers.map(pair=>pair.map(v=>new B.Vector3(v[0],.022,v[2])))
    },scene);
    accent.color=new B.Color3(.83,.65,.35);
    return {engine,scene,camera,shadow,ground,bounds:{min:-16,max:16},
      obstacles:STONES.map(p=>({...p,kind:"obstacle",blocking:true,opaque:true}))};
  }
  function fitCamera(camera, engine, B, target, narrow=false) {
    const aspect=engine.getRenderWidth()/Math.max(1,engine.getRenderHeight());
    camera.alpha=-Math.PI/4;camera.beta=Math.PI/3.25;
    camera.radius=narrow?10.5:13;
    camera.orthoTop=2.7;camera.orthoBottom=-2.7;
    camera.orthoLeft=-2.7*aspect;camera.orthoRight=2.7*aspect;
    camera.setTarget(new B.Vector3(target?.x||0,.85,target?.z||0));
  }
  function refreshCameraScale(camera,engine,halfAtRadius13=2.7) {
    const half=halfAtRadius13*camera.radius/13;
    const aspect=engine.getRenderWidth()/Math.max(1,engine.getRenderHeight());
    camera.orthoTop=half;camera.orthoBottom=-half;
    camera.orthoLeft=-half*aspect;camera.orthoRight=half*aspect;
  }
  return {create,fitCamera,refreshCameraScale,STONES};
});
