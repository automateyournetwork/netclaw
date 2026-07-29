import SwiftUI

/// Mirrors the phone's `EdgeMessage` (lib/ncfed/message_feed.dart) -- relayed
/// through `watch/feed/list` (contracts/watch-relay.md §3). Non-text
/// `content` is already dropped by the phone-side relay before it ever
/// reaches here (data-model.md).
struct WatchFeedMessage: Identifiable {
    let id = UUID()
    let contentType: String
    let content: String
    let designatedBy: String
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
                        Text(message.designatedBy).font(.caption2).foregroundStyle(.secondary)
                        content(for: message)
                    }
                }
            }
        }
        .refreshable { await store.refreshFeed() }
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
