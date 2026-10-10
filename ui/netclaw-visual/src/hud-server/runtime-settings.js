import { gatewayAgentId } from './gateway-agent.js';
const text = value => typeof value === 'string' && value.length <= 1024 ? value : 'Not configured';
const modelName = value => text(value).split('@')[0];

export function hermesRuntimeSettings(config, source) {
  const model = config?.model;
  return { config: {runtime:'hermes'}, settings: [
    {label:'Selected runtime', value:'Hermes'},
    {label:'Configuration source', value:source},
    {label:'Primary Model', value:modelName(typeof model==='string'?model:model?.default || model?.model)},
    {label:'Provider', value:text(model?.provider)},
    {label:'Execution policy', value:'Qualified read-only tools; writes unavailable'},
    ...(!config?[{label:'Hermes settings',value:'Unavailable: configuration could not be read'}]:[]),
  ] };
}

export function runtimeSettings(config, deviceCount, source) {
  if (!config) return { config: {}, settings: [
    { label: 'Configuration source', value: source },
    { label: 'OpenClaw settings', value: 'Unavailable: configuration could not be read' },
    { label: 'Devices in Testbed', value: String(deviceCount) },
  ] };
  const agentId = gatewayAgentId(config);
  const defaults = config.agents?.defaults || {};
  const agent = config.agents?.entries?.[agentId] || config.agents?.list?.find(a => a.id === agentId) || {};
  const model = agent.model ?? defaults.model;
  const primary = modelName(typeof model === 'string' ? model : model?.primary);
  const fallbacks = (Array.isArray(model?.fallbacks) ? model.fallbacks : []).map(modelName);
  const workspace = text(agent.workspace ?? defaults.workspace);
  const mode = text(config.gateway?.mode), command = typeof config.commands?.native === 'boolean' ? String(config.commands.native) : text(config.commands?.native);
  return {
    // Compatibility projection for the classic footer, never the raw live config.
    config: { gateway: { mode }, agents: { defaults: { model: { primary, fallbacks }, workspace } }, commands: { native: command } },
    settings: [
      { label: 'Configuration source', value: source },
      { label: 'Selected Agent', value: agentId },
      { label: 'Gateway Mode', value: mode },
      { label: 'Gateway Bind', value: text(config.gateway?.bind) },
      { label: 'Gateway Port', value: Number.isInteger(config.gateway?.port) ? String(config.gateway.port) : 'Default (18789)' },
      { label: 'Primary Model', value: primary },
      { label: 'Fallback Models', value: fallbacks.join(', ') || 'None configured' },
      { label: 'Workspace', value: workspace },
      { label: 'Command Mode', value: command },
      { label: 'Devices in Testbed', value: String(deviceCount) },
    ],
  };
}
