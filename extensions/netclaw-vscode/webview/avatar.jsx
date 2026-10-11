import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import PalAvatar from '../../../ui/netclaw-visual/src/dashboard/PalAvatar.jsx';

const host=document.getElementById('avatar');
function Avatar(){
  const [avatar,setAvatar]=useState('john');
  return <section aria-label="Local Avatar"><label htmlFor="avatar-character">Avatar character</label><select id="avatar-character" value={avatar} onChange={event=>setAvatar(event.target.value)}><option value="john">John</option><option value="lobster">NetClaw</option></select><PalAvatar avatar={avatar} assetBase={host.dataset.assets} fallbackDetail="Your text conversation remains available."/><p className="hint">Local bundled avatar. Character and camera controls do not send a prompt. Voice and hosted video are not enabled in this candidate.</p></section>;
}
createRoot(host).render(<Avatar/>);
