import ActivityKit
import SwiftUI
import WidgetKit

/// Lock Screen / Dynamic Island presentation (099/FR-017). Shows only that a
/// pending approval exists and its non-sensitive target name -- no approval
/// payload, no requesting-agent detail, nothing an unlocked-phone screen
/// alone would reveal.
@available(iOS 16.2, *)
struct PendingApprovalLiveActivityView: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: PendingApprovalActivityAttributes.self) { context in
            HStack {
                Image(systemName: "checkmark.shield")
                VStack(alignment: .leading) {
                    Text("Pending approval")
                        .font(.headline)
                    Text(context.state.targetName)
                        .font(.subheadline)
                }
                Spacer()
            }
            .padding()
            .activityBackgroundTint(Color.black.opacity(0.8))
            .activitySystemActionForegroundColor(Color.white)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    VStack {
                        Text("Pending approval")
                            .font(.headline)
                        Text(context.state.targetName)
                            .font(.subheadline)
                    }
                }
            } compactLeading: {
                Image(systemName: "checkmark.shield")
            } compactTrailing: {
                Text("•")
            } minimal: {
                Image(systemName: "checkmark.shield")
            }
        }
    }
}

@available(iOS 16.2, *)
@main
struct LiveActivityWidgetBundle: WidgetBundle {
    var body: some Widget {
        PendingApprovalLiveActivityView()
    }
}
