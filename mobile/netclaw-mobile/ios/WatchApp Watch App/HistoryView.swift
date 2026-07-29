import SwiftUI

/// Mirrors the phone's `ConversationTurn` (lib/ncfed/conversation_store.dart)
/// -- relayed through `watch/history/list`. Added after real-hardware
/// testing showed the operator wanted past chat Q&A visible on the wrist,
/// not just the live "Ask" flow -- read-only, no interaction, same as Feed.
struct WatchHistoryTurn: Identifiable {
    let id: String // taskId
    let requestText: String
    let answerText: String?
    let state: String // "answered" | "failed" | "waiting"
}

struct HistoryView: View {
    @ObservedObject var store: WatchDataStore

    var body: some View {
        Group {
            if !store.historyLoaded {
                ProgressView()
            } else if store.historyConnection != .connected {
                ContentUnavailableView {
                    Label(store.historyConnection.message, systemImage: "wifi.slash")
                } actions: {
                    Button("Retry") { Task { await store.refreshHistory() } }
                }
            } else if store.historyTurns.isEmpty {
                ContentUnavailableView("No chat history yet", systemImage: "clock")
            } else {
                List(store.historyTurns) { turn in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(turn.requestText).font(.headline)
                        if let answer = turn.answerText {
                            Text(answer).font(.caption)
                        } else if turn.state == "waiting" {
                            Text("Still working…").font(.caption).foregroundStyle(.secondary)
                        } else {
                            Text("No answer").font(.caption).foregroundStyle(.red)
                        }
                    }
                }
            }
        }
        .refreshable { await store.refreshHistory() }
    }
}
