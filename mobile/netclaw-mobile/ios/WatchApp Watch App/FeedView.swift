import SwiftUI

/// Mirrors the phone's `EdgeMessage` (lib/ncfed/message_feed.dart) -- relayed
/// through `watch/feed/list` (contracts/watch-relay.md §3). Non-text
/// `content` is already dropped by the phone-side relay before it ever
/// reaches here (data-model.md).
struct WatchFeedMessage: Identifiable {
    let id = UUID()
    /// The message's `pushed_at` ISO string -- the identity acknowledge/
    /// delete relay calls key on (073, contracts/watch-relay-extensions.md).
    let pushedAt: String
    let contentType: String
    let content: String
    let designatedBy: String
    var acknowledged: Bool
}

/// User Story 2 (P2): read-only, scrollable view of Border-pushed messages.
/// No interaction beyond viewing/scrolling (FR-006) -- image/voice messages
/// show a type indicator rather than their (unavailable) content (FR-007).
struct FeedView: View {
    @ObservedObject var store: WatchDataStore

    var body: some View {
        Group {
            if !store.feedLoaded {
                ProgressView()
            } else if store.feedConnection != .connected {
                ContentUnavailableView {
                    Label(store.feedConnection.message, systemImage: "wifi.slash")
                } actions: {
                    Button("Retry") { Task { await store.refreshFeed() } }
                }
            } else if store.feedMessages.isEmpty {
                ContentUnavailableView("No messages yet", systemImage: "tray")
            } else {
                List(store.feedMessages) { message in
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 4) {
                            // Unread indicator (073/FR-011) -- an explicit
                            // acknowledge swipe clears it (FR-012); merely
                            // viewing this tab does not (spec Assumptions).
                            if !message.acknowledged {
                                Circle().fill(.blue).frame(width: 6, height: 6)
                            }
                            Text(message.designatedBy).font(.caption2).foregroundStyle(.secondary)
                        }
                        content(for: message)
                        readAloudButton(for: message)
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) {
                            Task { await store.deleteFeed(pushedAt: message.pushedAt) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        if !message.acknowledged {
                            Button {
                                Task { await store.acknowledgeFeed(pushedAt: message.pushedAt) }
                            } label: {
                                Label("Acknowledge", systemImage: "checkmark.circle")
                            }
                            .tint(.blue)
                        }
                    }
                }
            }
        }
        .refreshable { await store.refreshFeed() }
    }

    /// On-demand "read aloud" (073/FR-017/FR-018) -- never triggered
    /// automatically, only by this explicit tap. A photo/voice message has
    /// no text to speak, so it speaks a description of the content type
    /// instead of failing silently (FR-019).
    @ViewBuilder
    private func readAloudButton(for message: WatchFeedMessage) -> some View {
        Button {
            let text = switch message.contentType {
            case "image": "Photo message"
            case "voice": "Voice message"
            default: message.content
            }
            SpeechPlayback.shared.speak(text)
        } label: {
            Label("Read aloud", systemImage: "speaker.wave.2")
        }
        .font(.caption2)
    }

    @ViewBuilder
    private func content(for message: WatchFeedMessage) -> some View {
        switch message.contentType {
        case "image":
            Label("Photo", systemImage: "photo")
        case "voice":
            Label("Voice message", systemImage: "mic")
        default:
            Text(message.content)
        }
    }

}
