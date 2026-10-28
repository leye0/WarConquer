/* WarConquer melee combat transaction, driven by a real attack animation.
 * The controller decides WHEN the hit lands; this module applies it once.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.WCCombat=api;
})(typeof globalThis==="object"?globalThis:this,function(){
  "use strict";
  function hit({items,entityId,actor,team="blue",reach=1.6,damage=34}){
    const index=items.findIndex(o=>o.id===entityId);
    if(index<0)return {ok:false,reason:"not_found"};
    const item=items[index];
    if(item.kind!=="unit"||item.team===team)return {ok:false,reason:"not_enemy"};
    if(!actor||![actor.x,actor.z,item.x,item.z,reach,damage].every(Number.isFinite)
        ||reach<=0||!Number.isInteger(damage)||damage<=0)
      return {ok:false,reason:"invalid_hit"};
    const distance=Math.hypot(actor.x-item.x,actor.z-item.z);
    if(distance>reach+1e-7)return {ok:false,reason:"out_of_range"};
    const before=Math.max(0,Number.isFinite(item.health)?item.health:100);
    if(before<=0)return {ok:false,reason:"already_defeated"};
    item.health=Math.max(0,before-damage);
    const defeated=item.health===0;
    if(defeated)items.splice(index,1);
    return {ok:true,id:item.id,name:item.name||"Ennemi",damage:before-item.health,
      health:item.health,defeated,item};
  }
  return {hit};
});
