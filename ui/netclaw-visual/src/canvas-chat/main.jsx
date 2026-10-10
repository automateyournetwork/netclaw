import React from 'react';
import { createRoot } from 'react-dom/client';
import { bootstrapRuntime } from '../shared/runtime-client.js';
const root = createRoot(document.getElementById('root'));
bootstrapRuntime().then(() => import('./App.jsx')).then(({default:App}) => root.render(<React.StrictMode><App /></React.StrictMode>)).catch(error => root.render(<p role="alert">{error.message}</p>));
