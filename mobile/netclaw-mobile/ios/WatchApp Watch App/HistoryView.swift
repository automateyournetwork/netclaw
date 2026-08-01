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
    var acknowledged: Bool
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
                        HStack(spacing: 4) {
                            // Unread indicator (073/FR-011) -- an explicit
                            // acknowledge swipe clears it (FR-012); merely
                            // viewing this tab does not (spec Assumptions).
                            // A still-waiting turn has nothing to
                            // acknowledge yet, matching
                            // ConversationStore.unreadCount's own rule.
                            if turn.state != "waiting" && !turn.acknowledged {
                                Circle().fill(.blue).frame(width: 6, height: 6)
                            }
                            Text(turn.requestText).font(.headline)
                        }
                        if let answer = turn.answerText {
                            Text(answer).font(.caption)
                            readAloudButton(text: answer)
                        } else if turn.state == "waiting" {
                            Text("Still working…").font(.caption).foregroundStyle(.secondary)
                        } else {
                            Text("No answer").font(.caption).foregroundStyle(.red)
                        }
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) {
                            Task { await store.deleteHistory(taskId: turn.id) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        if turn.state != "waiting" && !turn.acknowledged {
                            Button {
                                Task { await store.acknowledgeHistory(taskId: turn.id) }
                            } label: {
                                Label("Acknowledge", systemImage: "checkmark.circle")
                            }
                            .tint(.blue)
                        }
                    }
                }
            }
        }
        .refreshable { await store.refreshHistory() }
    }

    /// On-demand "read aloud" (073/FR-017/FR-018) -- never triggered
    /// automatically, only by this explicit tap.
    @ViewBuilder
    private func readAloudButton(text: String) -> some View {
        Button {
            SpeechPlayback.shared.speak(text)
        } label: {
            Label("Read aloud", systemImage: "speaker.wave.2")
        }
        .font(.caption2)
    }
}
