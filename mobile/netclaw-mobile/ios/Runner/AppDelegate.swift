import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
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
  }
}
