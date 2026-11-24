export function verifyClusterRuntime(runtime: any, options: any): Promise<{descriptor: any; pin: any}>;
export function verifyClusterDescriptor(runtime: any, options: any): Promise<{descriptor: any; pin: any}>;
export function clusterReviewMatches(cluster: any, review: any, principal?: any): boolean;
export function clusterCanDecide(cluster: any, operation: any): boolean;
export function verifyFederatedOperation(cluster: any, operation: any, principal: any, options?: any): Promise<any>;
