import Foundation

/// Bridges the phone-relayed device heartbeat (103/US4/FR-015) to the
/// `WatchComplication` extension via the shared App Group container,
/// mirroring `PendingApprovalCountStore`'s pattern -- a widget extension has
/// no way to read another process's in-memory `@Published` state directly. A
/// member of BOTH the `WatchApp` and `WatchComplication` targets, same as
/// that file.
///
/// Also doubles as the main watch app's own "last known" fallback (US4
/// acceptance scenario 3: "the phone is unreachable... shows the last-known
/// status and its age rather than an empty or misleading view") — unlike
/// Approvals/Feed/History, which show nothing when disconnected, the
/// heartbeat view falls back to whatever was last written here.
enum HeartbeatStatusStore {
    private static let appGroupID = "group.ca.automateyournetwork.netclaw.mobile"
    private static let summaryKey = "heartbeatSummary"
    private static let pushedAtKey = "heartbeatPushedAt"
    private static let isAlarmKey = "heartbeatIsAlarm"

    struct Status {
        let summary: String
        let pushedAt: Date
        let isAlarm: Bool
    }

    static func write(summary: String, pushedAt: Date, isAlarm: Bool) {
        let defaults = UserDefaults(suiteName: appGroupID)
        defaults?.set(summary, forKey: summaryKey)
        defaults?.set(pushedAt.timeIntervalSince1970, forKey: pushedAtKey)
        defaults?.set(isAlarm, forKey: isAlarmKey)
    }

    static func read() -> Status? {
        guard let defaults = UserDefaults(suiteName: appGroupID),
              let summary = defaults.string(forKey: summaryKey),
              defaults.object(forKey: pushedAtKey) != nil
        else { return nil }
        return Status(
            summary: summary,
            pushedAt: Date(timeIntervalSince1970: defaults.double(forKey: pushedAtKey)),
            isAlarm: defaults.bool(forKey: isAlarmKey))
    }
}
