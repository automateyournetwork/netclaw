import SwiftUI

/// Approvals (US1, the MVP) / Feed (US2) / Ask (US3) / History (added after
/// real-hardware testing) -- everything here relays through the phone
/// (FR-011), never connecting to a Border directly. Enrollment, capture, and
/// Settings remain deliberately absent (FR-013).
struct ContentView: View {
    @StateObject private var store = WatchDataStore()

    var body: some View {
        TabView {
            HeartbeatView(store: store)
                .tabItem { Label("Status", systemImage: "waveform.path.ecg") }
            ApprovalsView(store: store)
                .tabItem { Label("Approvals", systemImage: "checkmark.shield") }
            FeedView(store: store)
                .tabItem { Label("Feed", systemImage: "tray") }
            AskView()
                .tabItem { Label("Ask", systemImage: "mic") }
            HistoryView(store: store)
                .tabItem { Label("History", systemImage: "clock") }
        }
        .onAppear { store.preload() }
    }
}

#Preview {
    ContentView()
}
