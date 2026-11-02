// Each RAG tool starts a private stdio server. Its startup recovery sweep must
// never race another HUD ingestion, and polling must not multiply processes.
export function createRagQueue(execute, { maxPending = 32 } = {}) {
  let tail = Promise.resolve(), pending = 0;
  const reads = new Map();
  return (tool, args = {}, timeoutSec = 300) => {
    const read = tool === 'rag_list' || tool === 'rag_stats';
    const key = read ? JSON.stringify([tool, args, timeoutSec]) : null;
    if (key && reads.has(key)) return reads.get(key);
    if (pending >= maxPending) return Promise.reject(new Error('RAG request capacity busy; try later.'));
    // A later read must observe intervening writes, even if an earlier read is
    // still running. Mutations are always distinct and are never retried here.
    if (!read) reads.clear();
    pending++;
    const result = tail.then(() => execute(tool, args, timeoutSec)).finally(() => {
      pending--;
      if (key && reads.get(key) === result) reads.delete(key);
    });
    tail = result.catch(() => {});
    if (key) reads.set(key, result);
    return result;
  };
}
