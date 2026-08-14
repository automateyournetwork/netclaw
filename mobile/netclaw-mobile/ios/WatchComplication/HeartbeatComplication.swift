import SwiftUI
import WidgetKit

/// 103/US4 (FR-015 "raise your wrist"): a single timeline entry, read
/// straight from `HeartbeatStatusStore` -- no network call of its own, no
/// polling. `WatchDataStore.refreshHeartbeat()` writes a fresh value and
/// calls `reloadAllTimelines()` immediately after every successful phone
/// fetch, same pattern as `PendingApprovalComplication`.
struct HeartbeatEntry: TimelineEntry {
    let date: Date
    let status: HeartbeatStatusStore.Status?
}

struct HeartbeatTimelineProvider: TimelineProvider {
    func placeholder(in context: Context) -> HeartbeatEntry {
        HeartbeatEntry(date: Date(), status: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (HeartbeatEntry) -> Void) {
        completion(HeartbeatEntry(date: Date(), status: HeartbeatStatusStore.read()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<HeartbeatEntry>) -> Void) {
        let entry = HeartbeatEntry(date: Date(), status: HeartbeatStatusStore.read())
        // `.never` -- reloadAllTimelines() (triggered by the watch app on
        // every successful heartbeat fetch) is the only thing that should
        // refresh this, not a periodic policy guessing when a new heartbeat
        // might have landed.
        completion(Timeline(entries: [entry], policy: .never))
    }
}

struct HeartbeatComplicationView: View {
    let entry: HeartbeatEntry

    var body: some View {
        if let status = entry.status {
            if status.isAlarm {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .widgetLabel { Text("Alarm") }
            } else {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .widgetLabel { Text("Normal") }
            }
        } else {
            // No heartbeat has ever been received -- deliberately distinct
            // from "routine/all clear" (US4 acceptance scenario 3), so a
            // fresh enrollment never misreads as a healthy status.
            Image(systemName: "questionmark.circle")
                .widgetLabel { Text("No data") }
        }
    }
}

struct HeartbeatComplication: Widget {
    let kind = "HeartbeatComplication"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: HeartbeatTimelineProvider()) { entry in
            HeartbeatComplicationView(entry: entry)
        }
        .configurationDisplayName("NetClaw Status")
        .description("Shows the latest device heartbeat at a glance.")
        .supportedFamilies([.accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}
