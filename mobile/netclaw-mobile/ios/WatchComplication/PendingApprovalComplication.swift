import SwiftUI
import WidgetKit

/// A single timeline entry: just the count at the time it was read.
struct PendingApprovalEntry: TimelineEntry {
    let date: Date
    let pendingCount: Int
}

/// Reads the shared count `WatchDataStore` writes on every approvals
/// refresh (099/FR-019) -- no network call of its own, no polling; the
/// watch app calls `WidgetCenter.shared.reloadAllTimelines()` immediately
/// after writing a new count, so this only needs to serve whatever is
/// already on disk.
struct PendingApprovalTimelineProvider: TimelineProvider {
    func placeholder(in context: Context) -> PendingApprovalEntry {
        PendingApprovalEntry(date: Date(), pendingCount: 0)
    }

    func getSnapshot(in context: Context, completion: @escaping (PendingApprovalEntry) -> Void) {
        completion(PendingApprovalEntry(date: Date(), pendingCount: PendingApprovalCountStore.read()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<PendingApprovalEntry>) -> Void) {
        let entry = PendingApprovalEntry(date: Date(), pendingCount: PendingApprovalCountStore.read())
        // `.never` -- reloadAllTimelines() (triggered by the app on every
        // count change) is the only thing that should refresh this, not a
        // periodic policy guessing when the count might have changed.
        completion(Timeline(entries: [entry], policy: .never))
    }
}

struct PendingApprovalComplicationView: View {
    let entry: PendingApprovalEntry

    var body: some View {
        if entry.pendingCount > 0 {
            Text("\(entry.pendingCount)")
                .font(.headline)
                .widgetLabel { Text("Pending") }
        } else {
            Image(systemName: "checkmark.shield")
        }
    }
}

struct PendingApprovalComplication: Widget {
    let kind = "PendingApprovalComplication"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: PendingApprovalTimelineProvider()) { entry in
            PendingApprovalComplicationView(entry: entry)
        }
        .configurationDisplayName("Pending Approvals")
        .description("Shows the count of approvals waiting for you.")
        .supportedFamilies([.accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}

@main
struct WatchComplicationBundle: WidgetBundle {
    var body: some Widget {
        PendingApprovalComplication()
    }
}
