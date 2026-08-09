import ActivityKit
import Foundation

/// The shape of the Lock Screen Live Activity NetClaw starts for a pending
/// approval (099/FR-017, data-model.md's `LiveActivityState`). Deliberately
/// carries only what's safe to show on a locked screen -- `targetName` and
/// a coarse status, never approval detail -- per FR-017's "without exposing
/// sensitive approval content" requirement.
///
/// This file is a member of BOTH the `Runner` app target (which starts/ends
/// the activity via `LiveActivityBridge.swift`) and the `LiveActivityWidget`
/// extension target (which renders it) -- ActivityKit requires the same
/// concrete `ActivityAttributes` type on both sides of that boundary.
@available(iOS 16.2, *)
struct PendingApprovalActivityAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var targetName: String
        var status: String // "pending" | "resolved" (data-model.md LiveActivityState.status)
    }

    var approvalId: Int
}
