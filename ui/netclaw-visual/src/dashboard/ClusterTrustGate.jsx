import React, { useEffect, useState } from 'react';
import { verifyClusterDescriptor, clusterCanonical, clusterLabPrincipal, clusterStatusText } from '../shared/cluster-binding.js';
/** Explicit public-anchor pin. Origin storage never follows another Border automatically. */
export default function ClusterTrustGate({ cluster, installationId, principal, children }) {
 const [binding,setBinding]=useState(null),[candidate,setCandidate]=useState(null),[error,setError]=useState('');
 const key=`netclaw.cluster.${cluster.cluster_id}.pin.v1`;
 useEffect(()=>{setBinding(null);setCandidate(null);setError('');let active=true;const run=async()=>{try{
  if(location.protocol!=='https:')throw Error('Cluster onboarding requires verified HTTPS.');
  const raw=sessionStorage.getItem(key),pin=raw?JSON.parse(raw):undefined;
  const result=await verifyClusterDescriptor(cluster,{pin,acceptedAnchor:pin?undefined:cluster.anchor_key_id,origin:location.origin,installationId});
  if(clusterCanonical(principal)!==clusterCanonical(await clusterLabPrincipal(cluster.cluster_id)))throw Error('Cluster operator identity changed.');
  if(!active)return;
  if(pin){sessionStorage.setItem(key,JSON.stringify(result.pin));setBinding(result.descriptor);}else setCandidate(result);
 }catch(e){if(active){setBinding(null);setError(e.message);}}};run();return()=>{active=false;};},[cluster,installationId,key,principal]);
 if(error)return <p role="alert">Cluster verification refused: {error}. Saved references are preserved.</p>;
 if(!binding)return <section className="panel" aria-label="Cluster trust review"><h2>Trust this HA cluster</h2><p>The selected HTTPS Border advertises a separate cluster enrollment anchor. Check this fingerprint with the operator before accepting.</p><dl className="facts"><div><dt>Cluster</dt><dd>{cluster.cluster_id}</dd></div><div><dt>Generation</dt><dd>{cluster.generation}</dd></div><div><dt>Enrollment anchor</dt><dd>{cluster.anchor_key_id}</dd></div></dl><p>Node installations remain separate. This choice stores public identity only and submits no operation.</p><button disabled={!candidate} onClick={()=>{try{sessionStorage.setItem(key,JSON.stringify(candidate.pin));setBinding(candidate.descriptor);}catch(e){setError(e.message);}}}>Trust cluster</button></section>;
 return children(binding);
}
export function ClusterStatus({ cluster }) {return cluster?<section className="panel" aria-label="Cluster authority"><h2>Cluster authority</h2><p role="status">{clusterStatusText(cluster)}</p><dl className="facts"><div><dt>Cluster</dt><dd>{cluster.cluster_id}</dd></div><div><dt>Serving node</dt><dd>{cluster.node_id}</dd></div><div><dt>Authority epoch</dt><dd>{cluster.authority.epoch??'Unknown'}</dd></div><div><dt>Observed</dt><dd>{new Date(cluster.authority.observed_at_ms).toISOString()}</dd></div></dl><p>Status is an observation. The member checks authority before execution.</p><details><summary>Enrolled cluster endpoints</summary><p>Select an endpoint explicitly. Browser references stay with this origin; copy an operation ID or nonce and import it for status-only recovery.</p><ul>{cluster.manifest.manifest.nodes.map(node=><li key={node.node_id}><a href={node.endpoints.https} rel="noreferrer">{node.endpoints.https}</a> · {node.installation_id}</li>)}</ul></details></section>:null;}
