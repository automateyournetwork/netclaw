import Foundation
import WatchConnectivity

/// Watch-side counterpart to the phone's `WatchRelayPlugin` (research D1/D2).
/// Only ever uses `sendMessage`'s live request/reply -- never background or
/// queued delivery -- so an unreachable phone is a direct, immediate `nil`,
/// not something a separate reachability check has to infer.
final class WatchConnectivitySession: NSObject, WCSessionDelegate {
    static let shared = WatchConnectivitySession()

    private let session = WCSession.default

    private override init() {
        super.init()
        if WCSession.isSupported() {
            session.delegate = self
            session.activate()
        }
    }

    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {}

    /// Sends one request to the phone and returns its reply, or `nil` if the
    /// phone could not be reached at all -- that `nil` IS the
    /// `phoneUnreachable` signal (research D2, FR-012); callers never do a
    /// separate reachability check before calling this.
    ///
    /// Real-hardware `sendMessage` calls have been observed to neither reply
    /// nor error back promptly even while `isReachable` reports true -- a
    /// 10s fallback timeout guarantees callers always resolve to a state
    /// (never an indefinite spinner, which FR-012 treats as a silent failure).
    func send(method: String, args: [String: Any] = [:]) async -> [String: Any]? {
        guard session.activationState == .activated, session.isReachable else { return nil }
        var message = args
        message["method"] = method
        return await withCheckedContinuation { (continuation: CheckedContinuation<[String: Any]?, Never>) in
            let lock = NSLock()
            var didResume = false
            func resumeOnce(_ value: [String: Any]?) {
                lock.lock()
                defer { lock.unlock() }
                guard !didResume else { return }
                didResume = true
                continuation.resume(returning: value)
            }

            session.sendMessage(message, replyHandler: { reply in
                resumeOnce(reply)
            }, errorHandler: { _ in
                resumeOnce(nil)
            })

            DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                resumeOnce(nil)
            }
        }
    }

    /// Derives the shared three-way `ConnectionState` from a relay reply (or
    /// its absence) -- one definition all three views agree on (FR-012).
    static func connectionState(from reply: [String: Any]?) -> ConnectionState {
        guard let reply else { return .phoneUnreachable }
        if let enrolled = reply["enrolled"] as? Bool, !enrolled { return .notEnrolled }
        return .connected
    }
}
