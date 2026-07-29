import LocalAuthentication
import SwiftUI

/// Mirrors the phone's `PendingApproval` (lib/ncfed/approval_client.dart) --
/// relayed through `watch/approvals/list` (contracts/watch-relay.md §1).
struct WatchApproval: Identifiable {
    let id: Int
    let targetType: String
    let targetName: String
    let requestingAgent: String
    let riskName: String?
}

/// User Story 1 (P1, the MVP): approve/deny pending Border-triggered
/// approvals from the wrist. Every resolve action requires a fresh, explicit
/// device-passcode confirmation (FR-003/research D3) -- never cached, never
/// skipped because the watch happens to already be unlocked.
struct ApprovalsView: View {
    @ObservedObject var store: WatchDataStore
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if !store.approvalsLoaded {
                ProgressView()
            } else if store.approvalsConnection != .connected {
                ContentUnavailableView {
                    Label(store.approvalsConnection.message, systemImage: "wifi.slash")
                } actions: {
                    Button("Retry") { Task { await store.refreshApprovals() } }
                }
            } else if store.approvals.isEmpty {
                ContentUnavailableView("No pending approvals", systemImage: "checkmark.circle")
            } else {
                List(store.approvals) { approval in
                    ApprovalRow(approval: approval, errorMessage: errorMessage) { action in
                        await resolve(approval, action: action)
                    }
                }
            }
        }
        .refreshable { await store.refreshApprovals() }
    }

    /// FR-003: a fresh `.deviceOwnerAuthentication` (passcode -- no biometric
    /// modality exists on watchOS) check immediately before every single
    /// approve/deny, per Clarifications. A failed/cancelled/unavailable
    /// confirmation leaves the approval untouched -- `resolve` is never
    /// called in that case.
    private func resolve(_ approval: WatchApproval, action: String) async {
        errorMessage = nil
        let context = LAContext()
        var authError: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &authError) else {
            errorMessage = "Passcode confirmation isn't available on this watch."
            return
        }
        let reason = action == "approve"
            ? "Confirm approval of \(approval.targetName)"
            : "Confirm denial of \(approval.targetName)"
        let confirmed: Bool
        do {
            confirmed = try await context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason)
        } catch {
            confirmed = false
        }
        guard confirmed else { return } // cancelled/failed -- send nothing (FR-003)

        let reply = await WatchConnectivitySession.shared.send(
            method: "watch/approvals/resolve",
            args: ["approval_id": approval.id, "action": action])
        if reply?["resolved"] as? Bool != true {
            errorMessage = "Could not resolve — check your iPhone connection."
        }
        await store.refreshApprovals() // FR-005: a resolved approval must drop off the list
    }
}

private struct ApprovalRow: View {
    let approval: WatchApproval
    let errorMessage: String?
    let onResolve: (String) async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("\(approval.targetType): \(approval.targetName)").font(.headline)
            Text("Requested by \(approval.requestingAgent)"
                + (approval.riskName.map { " (\($0))" } ?? ""))
                .font(.caption)
            if let errorMessage {
                Text(errorMessage).font(.caption2).foregroundStyle(.red)
            }
            HStack {
                Button("Approve") { Task { await onResolve("approve") } }
                Button("Deny", role: .destructive) { Task { await onResolve("deny") } }
            }
        }
    }
}
