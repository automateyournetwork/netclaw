export function unbindImportedSession(value) {
  if (!value || !Array.isArray(value.nodes)) return value;
  return { ...value, nodes: value.nodes.map(({hudThread,...node}) => ({ ...node, messages: (node.messages || []).map(message => {
    const { assessmentRefs, ...rest } = message;
    return assessmentRefs ? { ...rest, assessmentBinding: 'unbound' } : rest;
  }) })) };
}
export function openAssessment(reference) {
  if (window.parent !== window) window.parent.postMessage({ type: 'netclaw:assessment', reference }, location.origin);
  else window.open(`/assessment.html?task=${encodeURIComponent(reference.taskRef)}&assessment=${encodeURIComponent(reference.assessmentId)}`, '_blank', 'noopener');
}
