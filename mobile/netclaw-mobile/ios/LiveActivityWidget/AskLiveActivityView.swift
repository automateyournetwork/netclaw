import ActivityKit
import SwiftUI
import WidgetKit

/// Lock Screen / Dynamic Island presentation for an in-flight submitted
/// question (spec 113, User Story 3). Shows the question preview, a
/// continuously-ticking elapsed timer (`Text(timerInterval:)`, FR-005), and
/// the Border's own free-text progress detail when one has arrived
/// (FR-006) -- never a member count of any kind. Tapping opens
/// `netclaw://chat/<taskId>` (FR-008, research.md R3), the same
/// `netclaw://` scheme/`app_links` mechanism the pending-approval activity's
/// buttons use.
@available(iOS 16.2, *)
struct AskLiveActivityView: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: AskActivityAttributes.self) { context in
            VStack(alignment: .leading, spacing: 4) {
                Text(context.attributes.questionPreview)
                    .font(.headline)
                    .lineLimit(2)
                status(context.state)
                    .font(.subheadline)
                    .monospacedDigit()
                if let detail = context.state.progressDetail {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
            .activityBackgroundTint(Color.black.opacity(0.8))
            .activitySystemActionForegroundColor(Color.white)
            .widgetURL(chatDeepLink(for: context.attributes.taskId))
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    VStack {
                        Text(context.attributes.questionPreview)
                            .font(.headline)
                            .lineLimit(2)
                        status(context.state)
                            .font(.subheadline)
                            .monospacedDigit()
                        if let detail = context.state.progressDetail {
                            Text(detail)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            } compactLeading: {
                Image(systemName: "hourglass")
            } compactTrailing: {
                status(context.state)
                    .monospacedDigit()
                    .font(.caption2)
            } minimal: {
                Image(systemName: "hourglass")
            }
            .widgetURL(chatDeepLink(for: context.attributes.taskId))
        }
    }

    @ViewBuilder
    private func status(_ state: AskActivityAttributes.ContentState) -> some View {
        switch state.state {
        case "working", "pending":
            Text(timerInterval: state.startedAt...Date.distantFuture, countsDown: false)
        case "outcome_unknown": Text("Outcome unknown — do not resend")
        case "cancellation_requested": Text("Cancellation requested — stop unconfirmed")
        case "interrupted": Text("Interrupted before execution")
        case "completed": Text("Completed")
        case "cancelled": Text("Cancellation confirmed")
        case "failed": Text("Failed")
        default: Text("Status unknown — check NetClaw")
        }
    }

    private func chatDeepLink(for taskId: String) -> URL? {
        URL(string: "netclaw://chat/\(taskId)")
    }
}
