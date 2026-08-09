import Flutter
import XCTest

@testable import Runner

/// 099/FR-011: the watch-relay message-passing logic (`WatchRelayMessage`,
/// extracted from `WatchRelayPlugin` for exactly this reason) needs at
/// least a basic automated test that fails if it breaks -- this is the
/// first real content this app's native test target has ever had.
final class WatchRelayPluginTests: XCTestCase {
    func testExtractMethodReturnsTheMethodField() {
        let method = WatchRelayMessage.extractMethod(from: ["method": "askQuestion", "text": "status?"])
        XCTAssertEqual(method, "askQuestion")
    }

    func testExtractMethodReturnsNilWhenMissing() {
        let method = WatchRelayMessage.extractMethod(from: ["text": "status?"])
        XCTAssertNil(method)
    }

    func testExtractMethodReturnsNilWhenWrongType() {
        let method = WatchRelayMessage.extractMethod(from: ["method": 42])
        XCTAssertNil(method)
    }

    func testReplyPayloadPassesThroughASuccessfulDictReply() {
        let payload = WatchRelayMessage.replyPayload(from: ["answer": "3 pending approvals"])
        XCTAssertEqual(payload["answer"] as? String, "3 pending approvals")
    }

    func testReplyPayloadWrapsAFlutterError() {
        let error = FlutterError(code: "NO_HANDLER", message: "no handler registered", details: nil)
        let payload = WatchRelayMessage.replyPayload(from: error)
        XCTAssertEqual(payload["error"] as? String, "no handler registered")
    }

    func testReplyPayloadWrapsAFlutterErrorWithNoMessage() {
        let error = FlutterError(code: "NO_HANDLER", message: nil, details: nil)
        let payload = WatchRelayMessage.replyPayload(from: error)
        XCTAssertEqual(payload["error"] as? String, "unknown error")
    }

    func testReplyPayloadHandlesNilReply() {
        let payload = WatchRelayMessage.replyPayload(from: nil)
        XCTAssertEqual(payload["error"] as? String, "no reply from phone app")
    }

    func testReplyPayloadHandlesAnUnexpectedType() {
        let payload = WatchRelayMessage.replyPayload(from: 42)
        XCTAssertEqual(payload["error"] as? String, "no reply from phone app")
    }
}
