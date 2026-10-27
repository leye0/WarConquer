/* WarConquer equipment semantics -> compatible genuine animation groups.
 * A missing motion never silently falls back to an incompatible clip.
 * The catalog is preparation for an extensible Mixamo collection, not a
 * claim that these source FBX files already exist in this repository.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object" && module.exports)module.exports=api;
  else root.WCEquipmentActions=api;
})(typeof globalThis==="object"?globalThis:this,function(){
  "use strict";
  const profiles={
    axe:{family:"melee",mount:"hand",grip:"shaft",action:"axe_chop",
      queries:["downward axe attack","two handed axe swing","axe combat idle"],
      patterns:["^Attack_Mixamo_WithAxe$","^Axe_(Attack|Chop|Swing)(_|$)"],
      needsSecondaryHandIK:true,geometryReady:true},
    sword:{family:"melee",mount:"hand",grip:"flat_handle",action:"sword_slash",
      queries:["one handed sword slash","sword thrust","sword combat idle"],
      patterns:["^Sword_(Attack|Slash|Thrust)(_|$)","^Attack_Mixamo_WithSword$"],
      needsSecondaryHandIK:false,geometryReady:false},
    dagger:{family:"melee",mount:"hand",grip:"flat_handle",action:"dagger_stab",
      queries:["dagger stab","knife attack"],
      patterns:["^Dagger_(Stab|Attack)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    spear:{family:"melee",mount:"hand",grip:"shaft",action:"spear_thrust",
      queries:["spear thrust","polearm attack","spear combat idle"],
      patterns:["^Spear_(Thrust|Attack)(_|$)"],needsSecondaryHandIK:true,geometryReady:false},
    hammer:{family:"melee",mount:"hand",grip:"shaft",action:"hammer_strike",
      queries:["hammer strike","warhammer overhead swing"],
      patterns:["^Hammer_(Strike|Attack)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    bow:{family:"ranged",mount:"left_hand",grip:"frame",action:"bow_shot",
      queries:["bow aim","draw bow string","release arrow","archer idle"],
      patterns:["^Bow_(Aim|DrawAndRelease|Shoot)(_|$)","^Archery_Shoot(_|$)"],
      needsSecondaryHandIK:true,requiresEvent:"arrow_release",geometryReady:false},
    crossbow:{family:"ranged",mount:"hand",grip:"body",action:"crossbow_shot",
      queries:["crossbow aim and shoot","crossbow reload"],
      patterns:["^Crossbow_(Shoot|Fire)(_|$)"],
      needsSecondaryHandIK:false,requiresEvent:"bolt_release",geometryReady:false},
    staff:{family:"magic",mount:"hand",grip:"shaft",action:"staff_cast",
      queries:["staff spell cast","wizard staff idle"],
      patterns:["^Staff_(Cast|Spell)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    wand:{family:"magic",mount:"hand",grip:"flat_handle",action:"wand_cast",
      queries:["wand spell cast","wizard one hand cast"],
      patterns:["^Wand_(Cast|Spell)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    shield:{family:"defense",mount:"forearm",grip:"body",action:"shield_block",
      queries:["shield block","shield bash","shield idle"],
      patterns:["^Shield_(Block|Bash)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    tool:{family:"work",mount:"hand",grip:"shaft",action:"tool_use",
      queries:["chop wood","mining pickaxe","dig with shovel"],
      patterns:["^Tool_(Use|Chop|Mine|Dig)(_|$)"],needsSecondaryHandIK:false,geometryReady:false},
    other:{family:"unknown",mount:"unresolved",grip:"unsupported",action:null,
      queries:[],patterns:[],needsSecondaryHandIK:false,geometryReady:false}
  };
  function normalizeKind(kind){return Object.prototype.hasOwnProperty.call(profiles,kind)?kind:"other";}
  function resolve(spec,groups,events=[]){
    const kind=normalizeKind(spec?.object_kind);
    const profile=profiles[kind];
    const names=(groups||[]).map(x=>typeof x==="string"?x:x?.name)
      .filter(x=>typeof x==="string");
    const found=names.find(name=>profile.patterns.some(pattern=>new RegExp(pattern,"i").test(name)))||null;
    const missing=[];
    if(!profile.geometryReady)missing.push("geometry_adapter");
    if(!found && profile.action)missing.push("compatible_animation");
    if(profile.requiresEvent && !events.includes(profile.requiresEvent))
      missing.push(profile.requiresEvent);
    if(profile.needsSecondaryHandIK && kind!=="axe")missing.push("secondary_hand_ik");
    const secondaryHandUnsolved=!!profile.needsSecondaryHandIK;
    return {
      kind,family:profile.family,mount:profile.mount,grip:profile.grip,
      action:profile.action,motion:found,ready:missing.length===0,
      missing,needsSecondaryHandIK:secondaryHandUnsolved,
      motionQueries:[...profile.queries],
      // The current axe attaches only the primary hand; two-hand contact is
      // explicitly a known limitation even when the attack is playable.
      qualityWarning:kind==="axe" && spec?.hold_mode==="two_hands"
        ?"secondary_hand_not_constrained":null
    };
  }
  return {profiles,normalizeKind,resolve};
});