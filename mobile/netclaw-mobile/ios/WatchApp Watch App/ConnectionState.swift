import Foundation

/// Whether the paired phone is currently reachable and able to service watch
/// requests (feature 072, data-model.md) -- surfaced consistently across
/// Approvals, Feed, and Ask so FR-012's "explicit not-connected state" holds
/// everywhere, not just in one view.
enum ConnectionState: Equatable {
    case connected
    case phoneUnreachable
    case notEnrolled

    var message: String {
        switch self {
        case .connected: return ""
        case .phoneUnreachable: return "Can't reach your iPhone. Make sure NetClaw Mobile is open and nearby."
        case .notEnrolled: return "Your iPhone hasn't enrolled with a Border yet."
        }
    }
}
