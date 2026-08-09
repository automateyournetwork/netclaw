import Foundation
import WidgetKit

/// Preloads Approvals + Feed concurrently as soon as the watch app launches,
/// instead of each tab triggering its own blocking WatchConnectivity
/// round-trip only when first swiped to -- that per-tab lazy load is what
/// made tab switching feel "laggy"/"buggy" on real hardware (every reveal
/// re-sent a request and waited on it). Ask has no passive list to preload;
/// it stays independent, driven entirely by the operator submitting a
/// question.
@MainActor
final class WatchDataStore: ObservableObject {
    @Published var approvals: [WatchApproval] = []
    @Published var approvalsConnection: ConnectionState = .connected
    @Published var approvalsLoaded = false

    @Published var feedMessages: [WatchFeedMessage] = []
    @Published var feedConnection: ConnectionState = .connected
    @Published var feedLoaded = false

    @Published var historyTurns: [WatchHistoryTurn] = []
    @Published var historyConnection: ConnectionState = .connected
    @Published var historyLoaded = false

    func preload() {
        Task {
            await refreshApprovals()
            // The very first request can race the phone's WatchConnectivity
            // session finishing activation right after a cold launch of both
            // apps together -- a single unreachable result there is a launch
            // timing artifact, not a real "phone is gone" state, so retry
            // once automatically rather than leaving the operator staring at
            // an unlabeled swipe-to-refresh as their only way out.
            if approvalsConnection == .phoneUnreachable {
                try? await Task.sleep(nanoseconds: 2_500_000_000)
                await refreshApprovals()
            }
        }
        Task {
            await refreshFeed()
            if feedConnection == .phoneUnreachable {
                try? await Task.sleep(nanoseconds: 2_500_000_000)
                await refreshFeed()
            }
        }
        Task {
            await refreshHistory()
            if historyConnection == .phoneUnreachable {
                try? await Task.sleep(nanoseconds: 2_500_000_000)
                await refreshHistory()
            }
        }
    }

    func refreshApprovals() async {
        let reply = await WatchConnectivitySession.shared.send(method: "watch/approvals/list")
        approvalsConnection = WatchConnectivitySession.connectionState(from: reply)
        if approvalsConnection == .connected, let list = reply?["approvals"] as? [[String: Any]] {
            approvals = list.compactMap { dict in
                guard let id = dict["approval_id"] as? Int,
                      let targetType = dict["target_type"] as? String,
                      let targetName = dict["target_name"] as? String,
                      let requestingAgent = dict["requesting_agent"] as? String
                else { return nil }
                return WatchApproval(id: id, targetType: targetType, targetName: targetName,
                                      requestingAgent: requestingAgent, riskName: dict["risk_name"] as? String)
            }
        } else {
            approvals = []
        }
        approvalsLoaded = true
        // 099/FR-019: the complication has no data of its own -- every
        // approvals refresh is the one place the shared count changes, so
        // this is the one place to write it and prompt WidgetKit to redraw.
        PendingApprovalCountStore.write(approvals.count)
        WidgetCenter.shared.reloadAllTimelines()
    }

    func refreshFeed() async {
        let reply = await WatchConnectivitySession.shared.send(method: "watch/feed/list")
        feedConnection = WatchConnectivitySession.connectionState(from: reply)
        if feedConnection == .connected, let list = reply?["messages"] as? [[String: Any]] {
            feedMessages = list.compactMap { dict in
                guard let contentType = dict["content_type"] as? String,
                      let designatedBy = dict["designated_by"] as? String,
                      let pushedAt = dict["pushed_at"] as? String
                else { return nil }
                return WatchFeedMessage(
                    pushedAt: pushedAt,
                    contentType: contentType,
                    content: dict["content"] as? String ?? "",
                    designatedBy: designatedBy,
                    acknowledged: dict["acknowledged"] as? Bool ?? true)
            }
        } else {
            feedMessages = []
        }
        feedLoaded = true
    }

    /// Acknowledge/delete (073/FR-012/FR-013) always re-fetch afterward --
    /// the same on-demand refresh pattern every other relay call already
    /// uses (spec 072's design), so the watch's own list reflects the
    /// change immediately rather than only on the next unrelated refresh.
    func acknowledgeFeed(pushedAt: String) async {
        _ = await WatchConnectivitySession.shared.send(
            method: "watch/feed/acknowledge", args: ["pushed_at": pushedAt])
        await refreshFeed()
    }

    func deleteFeed(pushedAt: String) async {
        _ = await WatchConnectivitySession.shared.send(
            method: "watch/feed/delete", args: ["pushed_at": pushedAt])
        await refreshFeed()
    }

    func refreshHistory() async {
        let reply = await WatchConnectivitySession.shared.send(method: "watch/history/list")
        historyConnection = WatchConnectivitySession.connectionState(from: reply)
        if historyConnection == .connected, let list = reply?["turns"] as? [[String: Any]] {
            historyTurns = list.compactMap { dict in
                guard let taskId = dict["task_id"] as? String,
                      let requestText = dict["request_text"] as? String,
                      let state = dict["state"] as? String
                else { return nil }
                return WatchHistoryTurn(id: taskId, requestText: requestText,
                                         answerText: dict["answer_text"] as? String, state: state,
                                         acknowledged: dict["acknowledged"] as? Bool ?? true)
            }
        } else {
            historyTurns = []
        }
        historyLoaded = true
    }

    func acknowledgeHistory(taskId: String) async {
        _ = await WatchConnectivitySession.shared.send(
            method: "watch/history/acknowledge", args: ["task_id": taskId])
        await refreshHistory()
    }

    func deleteHistory(taskId: String) async {
        _ = await WatchConnectivitySession.shared.send(
            method: "watch/history/delete", args: ["task_id": taskId])
        await refreshHistory()
    }
}
