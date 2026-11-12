/* Pure conversion helpers shared by the browser and Node tests. */
(function(root){
  function convert(amount, from, to, rates){
    if(from===to)return Number(amount);
    const source=rates?.[from]?.cad_per_unit, target=rates?.[to]?.cad_per_unit;
    if(!Number.isFinite(source)||source<=0||!Number.isFinite(target)||target<=0||!Number.isFinite(Number(amount)))return null;
    return Number(amount)*source/target;
  }
  const api={convert};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.FareScoutCurrency=api;
})(typeof window!=='undefined'?window:globalThis);
