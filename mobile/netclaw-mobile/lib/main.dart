import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import 'ncfed/approval_client.dart';
import 'ncfed/capability_registration.dart';
import 'ncfed/capture_client.dart';
import 'ncfed/conversation_store.dart';
import 'ncfed/device_deep_link.dart';
import 'ncfed/edge_ask_client.dart';
import 'ncfed/edge_client.dart';
import 'ncfed/edge_identity.dart';
import 'ncfed/enrollment_store.dart';
import 'ncfed/heartbeat.dart';
import 'ncfed/message_feed.dart';
import 'ncfed/notification_deep_link.dart';
import 'ncfed/push_registration.dart';
import 'ncfed/reconnect_supervisor.dart';
import 'screens/approvals_screen.dart';
import 'screens/capture_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/device_scan_screen.dart';
import 'screens/enrollment_screen.dart';
import 'screens/feed_screen.dart';
import 'screens/settings_screen.dart';

void main() {
  runApp(const NetClawMobileApp());
}

class NetClawMobileApp extends StatelessWidget {
  const NetClawMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NetClaw Mobile',
      // The claw mark's own orange (assets/icon/icon.png) — matches the
      // brand, not an arbitrary Material default.
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFE65733))),
      home: const EnrollmentGate(),
    );
  }
}

/// Shows the enrollment flow first time through; on every later launch,
/// reconnects using the persisted enrollment instead (068 polish) — without
/// this, every cold start generated a fresh `memberId` and re-showed the QR
/// scanner, federating a brand-new edge member on every single launch
/// rather than reconnecting as the same one.
class EnrollmentGate extends StatefulWidget {
  /// Injectable so tests never touch the real `path_provider` platform
  /// channel (mirrors `VoiceTranscription`/`ReconnectSupervisor`'s existing
  /// injectable-function-with-production-default pattern).
  final Future<Directory> Function() documentsDirectory;

  const EnrollmentGate({super.key, this.documentsDirectory = getApplicationDocumentsDirectory});

  @override
  State<EnrollmentGate> createState() => _EnrollmentGateState();
}

enum _GateState { loading, reconnecting, reconnectFailed, needsEnrollment }

class _EnrollmentGateState extends State<EnrollmentGate> {
  static const _identity = EdgeIdentity();
  final String _newMemberId = 'risk/${DateTime.now().millisecondsSinceEpoch}';
  EnrollmentStore? _store;
  _GateState _state = _GateState.loading;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final dir = await widget.documentsDirectory();
    final store = EnrollmentStore(dir);
    final stored = await store.load();
    if (!mounted) return;
    _store = store;
    if (stored == null) {
      setState(() => _state = _GateState.needsEnrollment);
      return;
    }
    setState(() => _state = _GateState.reconnecting);
    try {
      final client = await EdgeClient.reconnect(
        stored.toPayload(),
        memberId: stored.memberId,
        keyFingerprint: stored.keyFingerprint,
        identity: _identity,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => HomeShell(client: client, stored: stored)),
      );
    } catch (e) {
      if (isRevokedByBorder(e)) {
        await store.clear();
        if (mounted) setState(() => _state = _GateState.needsEnrollment);
      } else if (mounted) {
        // Plausibly transient (timeout, connection_error, a dropped TLS
        // handshake, DNS failure) -- keep the persisted enrollment intact
        // so a later launch can still reconnect as the same device.
        setState(() => _state = _GateState.reconnectFailed);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_state == _GateState.needsEnrollment) {
      return EnrollmentScreen(
        memberId: _newMemberId,
        identity: _identity,
        onEnrolled: (client, payload) async {
          final navigator = Navigator.of(context); // captured before the async gap below
          final fingerprint = client.enrollFingerprint;
          StoredEnrollment? stored;
          if (fingerprint != null) {
            stored = StoredEnrollment(
              memberId: _newMemberId,
              keyFingerprint: fingerprint,
              borderHost: payload.borderHost,
              borderPort: payload.borderPort,
              clawDomain: payload.clawDomain,
            );
            await _store!.save(stored);
          }
          if (!mounted) return;
          navigator.pushReplacement(
            MaterialPageRoute(builder: (_) => HomeShell(client: client, stored: stored)),
          );
        },
      );
    }
    if (_state == _GateState.reconnectFailed) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  "Couldn't reconnect — this may just be a momentary "
                  'network blip. Your enrollment is still saved.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: () {
                    setState(() => _state = _GateState.reconnecting);
                    _init();
                  },
                  child: const Text('Retry'),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => setState(() => _state = _GateState.needsEnrollment),
                  child: const Text('Enter enrollment details instead'),
                ),
              ],
            ),
          ),
        ),
      );
    }
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}

/// Chat + Feed + Approvals + Settings tabs, once enrolled and connected
/// (feature 066/067/068). `stored` is null only when the fingerprint wasn't
/// returned on enroll (defensive; shouldn't happen in practice) — in that
/// case reconnect/push simply aren't available for this session, same as
/// today's behavior, rather than crashing.
class HomeShell extends StatefulWidget {
  final EdgeClient client;
  final StoredEnrollment? stored;

  const HomeShell({super.key, required this.client, this.stored});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  bool _connected = true;
  MessageFeedStore? _feedStore;
  EdgeAskClient? _askClient;
  ConversationStore? _conversationStore;
  ApprovalClient? _approvalClient;
  CapabilityRegistration? _capabilities;
  DeviceDeepLinkListener? _deepLinkListener;
  ReconnectSupervisor<void>? _reconnectSupervisor;
  DateTime? _highlightPushedAt;

  @override
  void initState() {
    super.initState();
    getApplicationDocumentsDirectory().then((dir) async {
      final feedStore = MessageFeedStore(dir);
      final askClient = EdgeAskClient(widget.client);
      final conversationStore = ConversationStore(dir);
      final approvalClient = ApprovalClient(widget.client);
      final capabilities = CapabilityRegistration(widget.client);
      wireMessageFeed(widget.client, feedStore, onApproval: approvalClient.receiveApproval);
      wireHeartbeat(widget.client);
      CaptureClient(
        askClient: askClient,
        capture: (type) => CaptureScreen.capture(context, type),
      ).wire(widget.client);
      await capabilities.register();
      setState(() {
        _feedStore = feedStore;
        _askClient = askClient;
        _conversationStore = conversationStore;
        _approvalClient = approvalClient;
        _capabilities = capabilities;
      });
      // T022: a cold-start-from-link and a foreground-tap both land on
      // ChatScreen with the auto-submitted request visible.
      _deepLinkListener = DeviceDeepLinkListener(
        handler: DeviceDeepLinkHandler(askClient),
        onSubmitted: (taskId, text) async {
          await conversationStore.addPending(taskId, text);
          if (mounted) setState(() => _tab = 0);
        },
      );
      _deepLinkListener!.start();
      _wireReconnect();
      _tryRegisterPush();
    });
  }

  /// Auto-redials on a dropped connection (068 polish, ports 066's
  /// `ReconnectSupervisor` from a tested-in-isolation class into the actual
  /// running app) — reuses the SAME `EdgeClient` object via
  /// `reconnectInPlace`, so nothing built above (askClient, feedStore's
  /// wiring, capture/approval handlers) needs to be rebuilt after a drop.
  void _wireReconnect() {
    final stored = widget.stored;
    if (stored == null) return; // no persisted identity to redial with
    final supervisor = ReconnectSupervisor<void>(
      dial: () => widget.client.reconnectInPlace(
        stored.toPayload(),
        memberId: stored.memberId,
        keyFingerprint: stored.keyFingerprint,
      ),
      onConnected: (_) {
        if (mounted) setState(() => _connected = true);
      },
      initiallyConnected: true,
    );
    widget.client.onDisconnected = () {
      supervisor.notifyDisconnected();
      if (mounted) setState(() => _connected = false);
    };
    supervisor.run(); // permanent retry loop; stopped in dispose()
    _reconnectSupervisor = supervisor;
  }

  /// Best-effort FCM/APNs token registration (066 US3) — safe to attempt
  /// with no real Firebase project configured (nothing in this repo ships
  /// `google-services.json`/`GoogleService-Info.plist`): any failure here
  /// just means the push-notification fallback isn't available yet, never
  /// something that blocks or crashes the rest of the app.
  ///
  /// Notification-tap deep-linking (T032) is wired here too, and only on the
  /// success path — `NotificationDeepLink` calls into `FirebaseMessaging`,
  /// which throws if `initializeApp` didn't succeed.
  Future<void> _tryRegisterPush() async {
    try {
      await Firebase.initializeApp();
      await PushRegistration(widget.client).registerCurrentToken();
      await _wireNotificationDeepLink();
    } catch (e) {
      debugPrint('push registration unavailable (no Firebase project configured?): $e');
    }
  }

  /// Tapping a delivered push (or cold-starting from one) jumps to the Feed
  /// tab with the referenced message scrolled into view and highlighted.
  Future<void> _wireNotificationDeepLink() async {
    final feedStore = _feedStore;
    if (feedStore == null) return;
    await NotificationDeepLink(
      store: feedStore,
      openMessage: (message) {
        if (!mounted) return;
        setState(() {
          _tab = 1; // Feed
          _highlightPushedAt = message.pushedAt;
        });
      },
    ).wire();
  }

  @override
  void dispose() {
    _reconnectSupervisor?.stop();
    _askClient?.dispose();
    _approvalClient?.dispose();
    super.dispose();
  }

  Future<void> _scanDevice() async {
    if (_askClient == null || _conversationStore == null) return;
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => DeviceScanScreen(
        handler: DeviceDeepLinkHandler(_askClient!),
        onSubmitted: (taskId) {
          Navigator.of(context).pop();
        },
      ),
    ));
  }

  static const _titles = ['Chat', 'Feed', 'Approvals', 'Settings'];

  @override
  Widget build(BuildContext context) {
    if (_feedStore == null ||
        _askClient == null ||
        _conversationStore == null ||
        _approvalClient == null ||
        _capabilities == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final pages = [
      ChatScreen(askClient: _askClient!, store: _conversationStore!),
      FeedScreen(store: _feedStore!, highlightPushedAt: _highlightPushedAt),
      ApprovalsScreen(approvalClient: _approvalClient!),
      SettingsScreen(capabilities: _capabilities!),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_tab]),
        actions: [
          if (!_connected)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 12),
              child: Center(
                child: SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            ),
          IconButton(icon: const Icon(Icons.qr_code_scanner), onPressed: _scanDevice),
        ],
      ),
      body: pages[_tab],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.chat), label: 'Chat'),
          NavigationDestination(icon: Icon(Icons.notifications), label: 'Feed'),
          NavigationDestination(icon: Icon(Icons.verified_user), label: 'Approvals'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}
