import SwiftUI

/// 103/US4 (FR-015): the latest Border-composed device heartbeat, relayed
/// through `watch/heartbeat/latest` (contracts/watch-heartbeat.md). Unlike
/// Approvals/Feed/History, an unreachable phone does NOT show a blocking
/// "can't reach your iPhone" placeholder here -- `WatchDataStore` falls back
/// to `HeartbeatStatusStore`'s last-known value (acceptance scenario 3), so
/// this view only needs to render whatever it's given plus a small
/// unreachable hint when that's the reason the value might be stale.
struct HeartbeatView: View {
    @ObservedObject var store: WatchDataStore

    var body: some View {
        Group {
            if !store.heartbeatLoaded {
                ProgressView()
            } else if let summary = store.heartbeatSummary, let pushedAt = store.heartbeatPushedAt {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 6) {
                            Image(systemName: store.heartbeatIsAlarm
                                ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                                .foregroundStyle(store.heartbeatIsAlarm ? .red : .green)
                            Text(store.heartbeatIsAlarm ? "Alarm" : "Normal")
                                .font(.caption)
                                .foregroundStyle(store.heartbeatIsAlarm ? .red : .green)
                        }
                        Text(summary)
                            .font(.body)
                            .foregroundStyle(store.heartbeatIsAlarm ? .red : .primary)
                        Text(relativeAge(of: pushedAt))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        if store.heartbeatConnection != .connected {
                            Text("Can't reach your iPhone right now — showing the last known status.")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.horizontal, 4)
                }
            } else if store.heartbeatConnection != .connected {
                ContentUnavailableView {
                    Label(store.heartbeatConnection.message, systemImage: "wifi.slash")
                } actions: {
                    Button("Retry") { Task { await store.refreshHeartbeat() } }
                }
            } else {
                ContentUnavailableView("No heartbeat yet", systemImage: "waveform.path.ecg")
            }
        }
        .refreshable { await store.refreshHeartbeat() }
    }

    /// A watch-sized relative age string ("just now" / "5m ago" / "3h ago" /
    /// "2d ago") -- FR-015 requires showing the heartbeat's age, not just its
    /// content, since a stale "all clear" read minutes after the phone went
    /// dark is a very different thing from a fresh one.
    private func relativeAge(of date: Date) -> String {
        let seconds = max(0, Int(Date().timeIntervalSince(date)))
        switch seconds {
        case ..<60: return "just now"
        case ..<3600: return "\(seconds / 60)m ago"
        case ..<86400: return "\(seconds / 3600)h ago"
        default: return "\(seconds / 86400)d ago"
        }
    }
}
