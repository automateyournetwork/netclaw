import ActivityKit
import Flutter
import Foundation

private let liveActivityChannel = "ca.automateyournetwork.netclaw/live_activity"

/// Starts/ends the Lock Screen Live Activity from Dart (099/FR-017/FR-018).
/// No approval logic of its own -- Dart decides when a pending-approval
/// notification posts (start) and when `confirmAndResolve` succeeds from
/// ANY surface, phone/notification/watch (end), exactly mirroring how
/// `WatchRelayPlugin` has no Border logic of its own (072/research D1).
/// 113/FR-011/research.md R7: mirrors the Border's own ask-timeout ceiling
/// (`service.py`'s `_edge_ask_timeout()` -- the default 600s member-turn
/// budget plus the default 180s stall extension) rather than an arbitrary
/// client-side guess, so a genuinely abandoned in-flight activity goes stale
/// at the same point the Border itself would have given up. This is a
/// static mirror of that default, not a live-synced value -- Swift has no
/// way to read the Border's own runtime configuration.
private let askActivityStaleDateSeconds: TimeInterval = 780

@available(iOS 16.2, *)
public class LiveActivityBridge: NSObject, FlutterPlugin {
    private var currentActivity: Activity<PendingApprovalActivityAttributes>?
    /// Keyed by `taskId` (113/FR-004) -- one activity per in-flight ask,
    /// unlike the single aggregate `currentActivity` above.
    private var askActivities: [String: Activity<AskActivityAttributes>] = [:]

    public static func register(with registrar: FlutterPluginRegistrar) {
        let channel = FlutterMethodChannel(name: liveActivityChannel, binaryMessenger: registrar.messenger())
        let instance = LiveActivityBridge()
        registrar.addMethodCallDelegate(instance, channel: channel)
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "start":
            start(call, result: result)
        case "update":
            update(call, result: result)
        case "end":
            end(result: result)
        case "startAsk":
            startAsk(call, result: result)
        case "updateAsk":
            updateAsk(call, result: result)
        case "endAsk":
            endAsk(call, result: result)
        default:
            result(FlutterMethodNotImplemented)
        }
    }

    private func start(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            result(FlutterError(code: "DISABLED", message: "Live Activities are disabled", details: nil))
            return
        }
        guard let args = call.arguments as? [String: Any],
              let approvalId = args["approvalId"] as? Int,
              let targetName = args["targetName"] as? String
        else {
            result(FlutterError(code: "BAD_ARGS", message: "approvalId/targetName required", details: nil))
            return
        }
        do {
            let attributes = PendingApprovalActivityAttributes(approvalId: approvalId)
            let state = PendingApprovalActivityAttributes.ContentState(targetName: targetName, status: "pending")
            let activity = try Activity.request(attributes: attributes, content: .init(state: state, staleDate: nil))
            currentActivity = activity
            result(nil)
        } catch {
            result(FlutterError(code: "START_FAILED", message: error.localizedDescription, details: nil))
        }
    }

    /// 113/US2/FR-003: reflects a resolution from ANY surface, not just a
    /// tap on the activity itself -- Dart calls this whenever an approval id
    /// drops out of `ApprovalClient.currentPending`, regardless of which
    /// surface resolved it. A call for an approval id that isn't the
    /// currently-showing one, or after it has already ended, is a no-op --
    /// this activity is a single aggregate (099's own "shows the first
    /// pending one" design), not one activity per approval id.
    private func update(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let activity = currentActivity,
              let args = call.arguments as? [String: Any],
              let approvalId = args["approvalId"] as? Int,
              let status = args["status"] as? String,
              activity.attributes.approvalId == approvalId
        else {
            result(nil)
            return
        }
        Task {
            let updatedState = PendingApprovalActivityAttributes.ContentState(
                targetName: activity.content.state.targetName, status: status)
            await activity.update(.init(state: updatedState, staleDate: nil))
            // FR-003 asks for "reflects a resolved status AND dismisses" --
            // update() alone would leave a resolved-but-still-visible
            // activity lingering, so a resolved status ends it too, exactly
            // like end() already does, but scoped to the matching id above.
            if status == "resolved" {
                await activity.end(.init(state: updatedState, staleDate: nil), dismissalPolicy: .immediate)
                currentActivity = nil
            }
            result(nil)
        }
    }

    private func end(result: @escaping FlutterResult) {
        guard let activity = currentActivity else {
            result(nil)
            return
        }
        Task {
            let endedState = PendingApprovalActivityAttributes.ContentState(
                targetName: activity.content.state.targetName, status: "resolved")
            await activity.end(.init(state: endedState, staleDate: nil), dismissalPolicy: .immediate)
            currentActivity = nil
            result(nil)
        }
    }

    /// 113/US3/FR-004: starts one new activity per submitted question,
    /// keyed by `taskId` -- independent of every other in-flight ask and of
    /// the aggregate approval activity above.
    private func startAsk(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            result(FlutterError(code: "DISABLED", message: "Live Activities are disabled", details: nil))
            return
        }
        guard let args = call.arguments as? [String: Any],
              let taskId = args["taskId"] as? String,
              let questionPreview = args["questionPreview"] as? String
        else {
            result(FlutterError(code: "BAD_ARGS", message: "taskId/questionPreview required", details: nil))
            return
        }
        do {
            let attributes = AskActivityAttributes(taskId: taskId, questionPreview: questionPreview)
            let state = AskActivityAttributes.ContentState(
                startedAt: Date(), progressDetail: nil, state: "working")
            let staleDate = Date().addingTimeInterval(askActivityStaleDateSeconds)
            let activity = try Activity.request(
                attributes: attributes, content: .init(state: state, staleDate: staleDate))
            askActivities[taskId] = activity
            result(nil)
        } catch {
            result(FlutterError(code: "START_FAILED", message: error.localizedDescription, details: nil))
        }
    }

    /// 113/US3/FR-006: updates one specific in-flight activity's status text
    /// with the Border's own free-text progress detail, verbatim -- never a
    /// member count (research.md R1). A call for a `taskId` with no tracked
    /// activity (already ended, or never started) is a no-op.
    private func updateAsk(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let args = call.arguments as? [String: Any],
              let taskId = args["taskId"] as? String,
              let progressDetail = args["progressDetail"] as? String,
              let activity = askActivities[taskId]
        else {
            result(nil)
            return
        }
        Task {
            let updatedState = AskActivityAttributes.ContentState(
                startedAt: activity.content.state.startedAt,
                progressDetail: progressDetail,
                state: activity.content.state.state)
            let staleDate = Date().addingTimeInterval(askActivityStaleDateSeconds)
            await activity.update(.init(state: updatedState, staleDate: staleDate))
            result(nil)
        }
    }

    /// 113/US3/FR-007: ends one specific in-flight activity, reflecting its
    /// terminal state first. A call for a `taskId` with no tracked activity
    /// is a no-op.
    private func endAsk(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        guard let args = call.arguments as? [String: Any],
              let taskId = args["taskId"] as? String,
              let state = args["state"] as? String,
              let activity = askActivities[taskId]
        else {
            result(nil)
            return
        }
        Task {
            let finalState = AskActivityAttributes.ContentState(
                startedAt: activity.content.state.startedAt,
                progressDetail: activity.content.state.progressDetail,
                state: state)
            await activity.end(.init(state: finalState, staleDate: nil), dismissalPolicy: ["outcome_unknown", "cancellation_requested", "interrupted"].contains(state) ? .after(Date().addingTimeInterval(3600)) : .immediate)
            askActivities.removeValue(forKey: taskId)
            result(nil)
        }
    }
}
