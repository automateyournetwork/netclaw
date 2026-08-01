import AVFoundation

/// On-demand text-to-speech for the watch's Feed/History/Ask views
/// (073/FR-017/FR-018/FR-019). `AVSpeechSynthesizer` is the same framework
/// iOS uses -- no new capability or entitlement is required on watchOS.
/// Deliberately has no automatic-trigger path anywhere in this file or its
/// callers: every call to [speak] traces back to an explicit operator tap.
final class SpeechPlayback {
    static let shared = SpeechPlayback()

    private let synthesizer = AVSpeechSynthesizer()

    private init() {}

    func speak(_ text: String) {
        guard !text.isEmpty else { return }
        let utterance = AVSpeechUtterance(string: text)
        synthesizer.speak(utterance)
    }
}
