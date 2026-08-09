import ActivityKit
import Flutter
import Foundation

private let liveActivityChannel = "ca.automateyournetwork.netclaw/live_activity"

/// Starts/ends the Lock Screen Live Activity from Dart (099/FR-017/FR-018).
/// No approval logic of its own -- Dart decides when a pending-approval
/// notification posts (start) and when `confirmAndResolve` succeeds from
/// ANY surface, phone/notification/watch (end), exactly mirroring how
/// `WatchRelayPlugin` has no Border logic of its own (072/research D1).
@available(iOS 16.2, *)
public class LiveActivityBridge: NSObject, FlutterPlugin {
    private var currentActivity: Activity<PendingApprovalActivityAttributes>?

    public static func register(with registrar: FlutterPluginRegistrar) {
        let channel = FlutterMethodChannel(name: liveActivityChannel, binaryMessenger: registrar.messenger())
        let instance = LiveActivityBridge()
        registrar.addMethodCallDelegate(instance, channel: channel)
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "start":
            start(call, result: result)
        case "end":
            end(result: result)
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
}
