import Flutter
import Foundation
import WatchConnectivity

private let watchRelayChannel = "ca.automateyournetwork.netclaw/watch_relay"

/// Feature 072: relays watch requests into Dart, and Dart's replies back to the
/// watch — this plugin has no Border logic of its own (research D1). The
/// watch has no identity, enrollment, or network connection of its own; every
/// capability is answered by the SAME `ApprovalClient`/`EdgeAskClient`/
/// `MessageFeedStore` instances the phone's own UI already uses, reached via
/// `watch_relay.dart`'s method-channel handler.
public class WatchRelayPlugin: NSObject, FlutterPlugin, WCSessionDelegate {
    private var channel: FlutterMethodChannel?

    public static func register(with registrar: FlutterPluginRegistrar) {
        let channel = FlutterMethodChannel(name: watchRelayChannel, binaryMessenger: registrar.messenger())
        let instance = WatchRelayPlugin()
        instance.channel = channel
        registrar.addMethodCallDelegate(instance, channel: channel)
        instance.activateSession()
    }

    private func activateSession() {
        guard WCSession.isSupported() else { return }
        let session = WCSession.default
        session.delegate = self
        session.activate()
    }

    // MARK: - FlutterPlugin (Dart -> native, unused here -- this plugin is a
    // pure native-to-Dart relay; it registers no Dart-invokable methods of
    // its own).
    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        result(FlutterMethodNotImplemented)
    }

    // MARK: - WCSessionDelegate (watch -> phone)

    public func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {}

    public func sessionDidBecomeInactive(_ session: WCSession) {}
    public func sessionDidDeactivate(_ session: WCSession) {
        session.activate()
    }

    /// Forwards a watch request into Dart via the method channel, using the
    /// `method` field (contracts/watch-relay.md) as the Flutter method name
    /// and the rest of the message as its arguments. The reply handler is
    /// called with whatever Dart's handler returned, once — exactly matching
    /// WCSession's own single-reply contract.
    public func session(_ session: WCSession, didReceiveMessage message: [String: Any], replyHandler: @escaping ([String: Any]) -> Void) {
        guard let method = message["method"] as? String, let channel = channel else {
            replyHandler(["error": "no method or channel unavailable"])
            return
        }
        DispatchQueue.main.async {
            channel.invokeMethod(method, arguments: message) { reply in
                if let reply = reply as? [String: Any] {
                    replyHandler(reply)
                } else if let flutterError = reply as? FlutterError {
                    replyHandler(["error": flutterError.message ?? "unknown error"])
                } else {
                    replyHandler(["error": "no reply from phone app"])
                }
            }
        }
    }
}
