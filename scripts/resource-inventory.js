/* WarConquer resource transaction: independent of 3D animation and of the LLM.
 * This module owns the gameplay effect, while the renderer may play a clip.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  else root.WCResources=api;
})(typeof globalThis==="object"?globalThis:this,function(){
  "use strict";
  const TYPES=["wood","ore","food"];
  function inventory(){return {wood:0,ore:0,food:0};}
  function collect({items,bag,entityId,actor,reach=1.2}){
    const index=items.findIndex(item=>item.id===entityId);
    if(index<0)return {ok:false,reason:"not_found"};
    const item=items[index];
    if(item.kind!=="resource")return {ok:false,reason:"not_a_resource"};
    if(!actor||!Number.isFinite(actor.x)||!Number.isFinite(actor.z))
      return {ok:false,reason:"invalid_actor"};
    if(!Number.isFinite(reach)||reach<=0)return {ok:false,reason:"invalid_reach"};
    if(Math.hypot(actor.x-item.x,actor.z-item.z)>reach+1e-6)
      return {ok:false,reason:"out_of_range"};
    const type=item.resourceType;
    if(!TYPES.includes(type))return {ok:false,reason:"unknown_resource_type"};
    const amount=item.quantity??1;
    if(!Number.isInteger(amount)||amount<1||amount>99)
      return {ok:false,reason:"invalid_quantity"};
    const previous=bag[type]??0;
    if(!Number.isSafeInteger(previous)||previous<0||previous>Number.MAX_SAFE_INTEGER-amount)
      return {ok:false,reason:"inventory_overflow"};
    // The inventory update and world removal are committed exactly once.
    bag[type]=previous+amount;
    items.splice(index,1);
    return {ok:true,id:item.id,name:item.name||type,type,amount,total:bag[type],item};
  }
  return {TYPES,inventory,collect};
});
