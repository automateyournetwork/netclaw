import Foundation

/// Bridges `WatchDataStore.approvals.count` (running in the watch app's
/// process) to the `WatchComplication` extension (its own separate
/// process) via the shared App Group container -- a widget extension has
/// no way to read another process's in-memory `@Published` state directly
/// (099/FR-019). A member of BOTH the `WatchApp` and `WatchComplication`
/// targets, same reason `PendingApprovalActivityAttributes.swift` (Story 7)
/// is shared between `Runner` and `LiveActivityWidget`.
enum PendingApprovalCountStore {
    private static let appGroupID = "group.ca.automateyournetwork.netclaw.mobile"
    private static let key = "pendingApprovalCount"

    static func write(_ count: Int) {
        UserDefaults(suiteName: appGroupID)?.set(count, forKey: key)
    }

    static func read() -> Int {
        UserDefaults(suiteName: appGroupID)?.integer(forKey: key) ?? 0
    }
}
