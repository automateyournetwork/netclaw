import BackgroundTasks
import Flutter
import UIKit

/// 103/FR-013 (US3): must match Info.plist's `BGTaskSchedulerPermittedIdentifiers`
/// and the identifier registered below exactly, or the OS silently refuses to
/// run the task.
private let backgroundRefreshTaskIdentifier = "ca.automateyournetwork.netclaw.mobile.refresh"

/// 103/US3: minimum spacing iOS is asked to leave between opportunistic
/// refreshes. This is a REQUEST, not a guarantee -- iOS grants windows at its
/// own discretion based on usage patterns, battery, and Low Power Mode, and
/// may be far less frequent than this in practice (spec explicitly forbids
/// claiming otherwise).
private let backgroundRefreshMinimumInterval: TimeInterval = 15 * 60

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  // Retained for the lifetime of one background-refresh attempt so ARC
  // doesn't tear the engine down mid-flight; cleared once that attempt
  // finishes (success, failure, or OS expiration).
  private var backgroundRefreshEngine: FlutterEngine?

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Must be registered unconditionally, before this method returns, on
    // EVERY launch (including a plain foreground tap) -- BGTaskScheduler
    // throws at submit-time otherwise. Registering here, not lazily, is the
    // only correct place per Apple's docs.
    BGTaskScheduler.shared.register(
      forTaskWithIdentifier: backgroundRefreshTaskIdentifier, using: nil
    ) { [weak self] task in
      guard let self, let refreshTask = task as? BGAppRefreshTask else {
        task.setTaskCompleted(success: false)
        return
      }
      self.handleBackgroundRefresh(task: refreshTask)
    }
    let launched = super.application(application, didFinishLaunchingWithOptions: launchOptions)
    scheduleBackgroundRefresh()
    return launched
  }

  override func applicationDidEnterBackground(_ application: UIApplication) {
    super.applicationDidEnterBackground(application)
    scheduleBackgroundRefresh()
  }

  /// Requests the next opportunistic window. Called after every launch and
  /// on every backgrounding so a request is (almost) always outstanding --
  /// `submit` throws if one is already pending for this identifier, which is
  /// expected and harmless to ignore.
  private func scheduleBackgroundRefresh() {
    let request = BGAppRefreshTaskRequest(identifier: backgroundRefreshTaskIdentifier)
    request.earliestBeginDate = Date(timeIntervalSinceNow: backgroundRefreshMinimumInterval)
    try? BGTaskScheduler.shared.submit(request)
  }

  /// Runs 103/US3's headless reconnect-and-drain in a fresh `FlutterEngine`
  /// with no window/widget tree -- `backgroundRefreshMain` (Dart) does the
  /// actual work (reconnect via the persisted enrollment, let the Border's
  /// queue replay land, post one summarizing local notification if anything
  /// arrived) and reports back over `backgroundRefreshChannel`.
  private func handleBackgroundRefresh(task: BGAppRefreshTask) {
    // Reschedule immediately, regardless of this attempt's outcome -- a
    // failed or expired window must not silently end the opportunistic
    // refresh cycle.
    scheduleBackgroundRefresh()

    let engine = FlutterEngine(name: "background-refresh")
    engine.run(withEntrypoint: "backgroundRefreshMain")
    GeneratedPluginRegistrant.register(with: engine)
    // Only EdgeIdentityPlugin is needed: backgroundRefreshMain reconnects and
    // drains via EdgeClient/wireMessageFeed, which need the Secure Enclave
    // identity to prove possession of the pinned key (in2n/hello) -- it does
    // not touch the watch relay or Live Activity, so those plugins are
    // deliberately not registered against this headless engine.
    if let registrar = engine.registrar(forPlugin: "EdgeIdentityPlugin") {
      EdgeIdentityPlugin.register(with: registrar)
    }
    backgroundRefreshEngine = engine

    var finished = false
    let finish: (Bool) -> Void = { [weak self] success in
      guard !finished else { return }
      finished = true
      task.setTaskCompleted(success: success)
      self?.backgroundRefreshEngine = nil
    }

    let channel = FlutterMethodChannel(
      name: "ca.automateyournetwork.netclaw/background_refresh",
      binaryMessenger: engine.binaryMessenger)
    channel.setMethodCallHandler { call, result in
      guard call.method == "done" else {
        result(FlutterMethodNotImplemented)
        return
      }
      let args = call.arguments as? [String: Any]
      let success = args?["success"] as? Bool ?? false
      finish(success)
      result(nil)
    }

    // The OS's own safety net: if backgroundRefreshMain never reports back
    // (a hang, a crash, an unexpected exception outside its own try/catch)
    // before iOS reclaims the window, force-complete rather than let the
    // task -- and the engine holding it alive -- leak past expiration.
    task.expirationHandler = { [weak self] in
      finish(false)
      self?.backgroundRefreshEngine = nil
    }
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    // feature 066: NCFED edge-node identity (Secure Enclave keygen/sign).
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "EdgeIdentityPlugin") {
      EdgeIdentityPlugin.register(with: registrar)
    }
    // feature 072: relays Apple Watch companion-app requests into Dart.
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "WatchRelayPlugin") {
      WatchRelayPlugin.register(with: registrar)
    }
    // 099/FR-017/FR-018: starts/ends the Lock Screen Live Activity.
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "LiveActivityBridge") {
      LiveActivityBridge.register(with: registrar)
    }
  }
}
