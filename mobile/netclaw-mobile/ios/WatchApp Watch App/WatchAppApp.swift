//
//  WatchAppApp.swift
//  WatchApp Watch App
//
//  Created by John Capobianco on 7/27/26.
//

import SwiftUI

@main
struct WatchApp_Watch_AppApp: App {
    init() {
        // Activate the WatchConnectivity session at launch rather than
        // lazily on first use, so it's ready by the time any view's
        // `.task` fires its first relay call.
        _ = WatchConnectivitySession.shared
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
