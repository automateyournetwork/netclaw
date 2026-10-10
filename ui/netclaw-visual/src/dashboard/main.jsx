import React from 'react';
import { createRoot } from 'react-dom/client';
import { bootstrapRuntime } from '../shared/runtime-client.js';
import './dashboard.css';
const root = createRoot(document.getElementById('root'));
(window.NETCLAW_PREVIEW ? Promise.resolve() : bootstrapRuntime()).then(() => import('./Dashboard.jsx')).then(({default:Dashboard}) => root.render(<Dashboard />)).catch(error => root.render(<p role="alert">{error.message}</p>));
