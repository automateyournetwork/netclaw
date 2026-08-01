import SwiftUI

private enum AskState {
    case idle, waiting, answered, failed
}

/// User Story 3 (P3): dictate a question, submit it through the phone
/// exactly like a typed iPhone chat message, see the answer. A `TextField`
/// is dictation-first on watchOS by default (research D5) -- no custom
/// speech-recognition code is written here.
struct AskView: View {
    @State private var questionText: String = ""
    @State private var state: AskState = .idle
    @State private var answerText: String = ""
    @State private var connection: ConnectionState = .connected
    @State private var taskId: String?

    var body: some View {
        VStack(spacing: 8) {
            if connection != .connected {
                ContentUnavailableView(connection.message, systemImage: "wifi.slash")
            } else {
                switch state {
                case .waiting:
                    ProgressView("Waiting for an answer…")
                case .answered:
                    ScrollView { Text(answerText) }
                    // On-demand "read aloud" (073/FR-017/FR-018) -- never
                    // triggered automatically, only by this explicit tap.
                    Button {
                        SpeechPlayback.shared.speak(answerText)
                    } label: {
                        Label("Read aloud", systemImage: "speaker.wave.2")
                    }
                    Button("Ask another") { reset() }
                case .failed:
                    Text("Couldn't get an answer.").foregroundStyle(.red)
                    Button("Try again") { reset() }
                case .idle:
                    TextField("Ask something…", text: $questionText)
                    Button("Submit") { Task { await submit() } }
                        .disabled(questionText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
        .padding()
    }

    private func reset() {
        state = .idle
        questionText = ""
        answerText = ""
        taskId = nil
    }

    private func submit() async {
        let text = questionText.trimmingCharacters(in: .whitespacesAndNewlines)
        // FR-010: a dictation/typed result with no usable text must never
        // reach the Border as an empty request.
        guard !text.isEmpty else { return }
        state = .waiting
        let reply = await WatchConnectivitySession.shared.send(method: "watch/ask/submit", args: ["text": text])
        connection = WatchConnectivitySession.connectionState(from: reply)
        guard connection == .connected, let id = reply?["task_id"] as? String else {
            state = .failed
            return
        }
        taskId = id
        await poll()
    }

    /// Polls every 2s, bounded at 150 attempts (~5 minutes) -- long enough to
    /// cover a genuinely slow Border-side agent turn (spec 071 observed
    /// multi-minute pyATS calls) without polling forever if something on the
    /// Border side never resolves at all (FR-009: must reach a terminal
    /// state, not spin indefinitely).
    private func poll() async {
        guard let taskId else { return }
        for _ in 0..<150 {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            let reply = await WatchConnectivitySession.shared.send(
                method: "watch/ask/status", args: ["task_id": taskId])
            // A single missed round-trip (WatchConnectivity flakiness, or our
            // own 10s send() timeout) is NOT a terminal failure -- only the
            // Border explicitly reporting "failed", or exhausting the whole
            // polling budget below, ends the wait (FR-009).
            guard let reply, let watchState = reply["state"] as? String else {
                continue
            }
            if watchState == "answered" {
                answerText = reply["answer_text"] as? String ?? ""
                state = .answered
                return
            } else if watchState == "failed" {
                state = .failed
                return
            }
            // still "waiting" -- poll again
        }
        state = .failed
    }
}
