// Freeze the visible ancestor prefix when a branch is created. Later parent
// turns and sibling work must never become implicit context for that branch.
export function branchSeed(nodes, parentId, quote = '') {
  const parent=nodes.find(n=>n.id===parentId);
  if(!parent)return [];
  let prefix=parent.seedContext;
  if(!prefix) {
    const chain=[],seen=new Set([parent.id]);let current=parent;
    while(current.parentId) {
      current=nodes.find(n=>n.id===current.parentId);
      if(!current || seen.has(current.id))break;
      seen.add(current.id);chain.unshift(current);
    }
    prefix=chain.flatMap(n=>n.messages || []);
  }
  let messages=(parent.messages || []).filter(m=>!m.relate);
  const normalize=value=>String(value || '').replace(/\s+/g,' ').trim();
  if(quote) {
    const index=messages.findIndex(m=>normalize(m.content).includes(normalize(quote)) || Object.values(m.tabs || {}).some(v=>normalize(v).includes(normalize(quote))));
    if(index>=0)messages=messages.slice(0,index+1);
  }
  return JSON.parse(JSON.stringify([...prefix,...messages]));
}
