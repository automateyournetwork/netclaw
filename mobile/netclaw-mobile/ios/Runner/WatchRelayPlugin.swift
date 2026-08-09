import Flutter
import Foundation
import WatchConnectivity

private let watchRelayChannel = "ca.automateyournetwork.netclaw/watch_relay"

/// The message-passing logic `WatchRelayPlugin` needs (099/FR-011) --
/// extracted into pure functions with no `WCSession`/`FlutterMethodChannel`
/// dependency so `WatchRelayPluginTests.swift` can exercise it directly,
/// without a paired watch/simulator (which CI doesn't provide).
enum WatchRelayMessage {
    /// The Flutter method name a watch request is relayed as
    /// (contracts/watch-relay.md) -- `nil` when the watch sent a message
    /// with no `method` field at all.
    static func extractMethod(from message: [String: Any]) -> String? {
        message["method"] as? String
    }

    /// Converts whatever Dart's `invokeMethod` completion handler produced
    /// into the `[String: Any]` shape `WCSession`'s `replyHandler` contract
    /// requires -- a successful Dart reply, a thrown `FlutterError`, or
    /// nothing at all (channel unavailable, Dart returned `nil`/an
    /// unexpected type) all need to reach the watch as *some* reply, never
    /// silently drop it.
    static func replyPayload(from dartReply: Any?) -> [String: Any] {
        if let reply = dartReply as? [String: Any] {
            return reply
        } else if let flutterError = dartReply as? FlutterError {
            return ["error": flutterError.message ?? "unknown error"]
        } else {
            return ["error": "no reply from phone app"]
        }
    }
}

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
        guard let method = WatchRelayMessage.extractMethod(from: message), let channel = channel else {
            replyHandler(["error": "no method or channel unavailable"])
            return
        }
        DispatchQueue.main.async {
            channel.invokeMethod(method, arguments: message) { reply in
                replyHandler(WatchRelayMessage.replyPayload(from: reply))
            }
        }
    }
}
