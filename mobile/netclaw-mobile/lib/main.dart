import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import 'ncfed/approval_client.dart';
import 'ncfed/background_refresh.dart';
import 'ncfed/badge_lifecycle.dart';
import 'ncfed/capability_registration.dart';
import 'ncfed/capture_client.dart';
import 'ncfed/conversation_store.dart';
import 'ncfed/dashboard_data.dart';
import 'ncfed/device_deep_link.dart';
import 'ncfed/device_heartbeat.dart';
import 'ncfed/edge_ask_client.dart';
import 'ncfed/edge_client.dart';
import 'ncfed/edge_identity.dart';
import 'ncfed/enrollment_store.dart';
import 'ncfed/heartbeat.dart';
import 'ncfed/live_activity.dart';
import 'ncfed/local_notifications.dart';
import 'ncfed/message_feed.dart';
import 'ncfed/notification_deep_link.dart';
import 'ncfed/pending_approval_store.dart';
import 'ncfed/push_message_ingest.dart';
import 'ncfed/push_registration.dart';
import 'ncfed/reconnect_supervisor.dart';
import 'ncfed/turn_reconciler.dart';
import 'ncfed/watch_relay.dart';
import 'screens/approvals_screen.dart';
import 'screens/capture_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/device_scan_screen.dart';
import 'screens/enrollment_screen.dart';
import 'screens/feed_screen.dart';
import 'screens/settings_screen.dart';

/// Referenced only so [backgroundRefreshMain] (103/US3) stays part of the
/// compiled program's import graph -- native code invokes it by name via a
/// headless `FlutterEngine.run(withEntrypoint:)` when iOS grants a
/// `BGAppRefreshTask` window, never through a Dart call site. See
/// ncfed/background_refresh.dart.
final backgroundRefreshEntryPointKeepAlive = backgroundRefreshMain;

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
  late final BadgeLifecycleObserver _badgeLifecycleObserver =
      BadgeLifecycleObserver(_recomputeBadge);
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
  String? _highlightTaskId;
  int _unreadFeed = 0;
  PushStatus _pushStatus = PushStatus.unknown;
  LocalNotifications? _localNotifications;
  bool _localNotificationsPermissionDenied = false;
  NotificationDeepLink? _notificationDeepLink;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(_badgeLifecycleObserver);
    getApplicationDocumentsDirectory().then((dir) async {
      final feedStore = MessageFeedStore(dir);
      final askClient = EdgeAskClient(widget.client);
      final conversationStore = ConversationStore(dir);
      final approvalClient = ApprovalClient(widget.client);
      // 103/US3: an approval may have arrived and been ACKed to the Border
      // during a headless BGAppRefreshTask window, where no live
      // ApprovalClient existed to hold it in memory -- PendingApprovalStore
      // is the durable holding pen for exactly that case. Drained once, here,
      // before anything else might reasonably act on approvals.
      PendingApprovalStore(dir).loadAndClear().then((pending) {
        for (final params in pending) {
          approvalClient.receiveApproval(params);
        }
      });
      final capabilities = CapabilityRegistration(widget.client);
      // 099/FR-017/FR-018: reacts to the SAME `currentPending` stream
      // regardless of which surface changed it -- in-app buttons,
      // notification actions (confirmAndResolve), and the watch (which
      // resolves through this exact ApprovalClient too, via WatchRelay) --
      // so the Live Activity starts/ends correctly no matter which one
      // acted. Aggregate, not per-approval: shows the first pending one.
      final liveActivity = LiveActivity();
      approvalClient.pending.listen((pending) {
        if (pending.isNotEmpty) {
          liveActivity.start(approvalId: pending.first.approvalId, targetName: pending.first.targetName);
        } else {
          liveActivity.end();
        }
      });

      // 073: real local notifications while the app process is alive,
      // distinct from feature 066's credential-blocked remote FCM/APNs path
      // below (_tryRegisterPush). Constructed (not yet initialize()'d) before
      // wireMessageFeed/wireHeartbeat/CaptureClient below, which only need the
      // object to exist -- see the race-window note on that block.
      final localNotifications = LocalNotifications();

      // 103/BORDER-FINDINGS: `_listen()` starts dispatching inbound
      // Border-initiated calls (n2n/edge/message, n2n/edge/heartbeat, capture
      // requests) the instant `widget.client` connects -- which already
      // happened, at latest, when `EnrollmentGate` handed us this client.
      // `EdgeClient._onMessage` silently drops any call with no registered
      // handler (no error reply), so the Border-side caller just times out
      // with no client-visible symptom. A live Border trace caught exactly
      // this: a queued-replay push arrived 86ms after a fresh handshake and
      // got no reply for the full 30s timeout, on a connection that had only
      // just been authenticated -- not a suspended/backgrounded app. The
      // previous code registered these handlers only after `await
      // localNotifications.initialize()` and `await
      // localNotifications.requestPermission()` below, the second of which
      // can block on a real user-facing permission dialog and so is
      // effectively unbounded. Moved up here, before either await, so the
      // race window shrinks to the sub-millisecond gap between this line and
      // the object constructions just above it.
      wireMessageFeed(
        widget.client,
        feedStore,
        onApproval: (params) {
          approvalClient.receiveApproval(params);
          final approval = approvalClient.currentPending
              .where((a) => a.approvalId == params['approval_id'])
              .toList();
          if (approval.isNotEmpty) {
            localNotifications.postApprovalNotification(
              identifier: approval.single.approvalId.toString(),
              targetName: approval.single.targetName,
              requestingAgent: approval.single.requestingAgent,
            );
          }
        },
        onMessage: (message) {
          // 103/US4: persisted regardless of `mounted` -- this durable-store
          // write is what the watch relay reads from, not a UI update, and
          // must not be skipped just because the app happens to be
          // backgrounded when a heartbeat lands.
          if (looksLikeDeviceHeartbeat(message)) {
            DeviceHeartbeatStore(dir).save(DeviceHeartbeatStatus.fromMessage(message));
          }
          // Spec 107/US1: the feed just gained a message, so a notification tap
          // still waiting for one may now be satisfiable. This is the signal that
          // makes the pending-intent approach work without polling — replay lands
          // seconds after a cold-start tap, and this is where that arrival is
          // already observed. Late-bound through the field on purpose:
          // `wireMessageFeed` is deliberately registered before the deep link is
          // constructed (see the race comment above), so this must not capture a
          // local that does not exist yet.
          _notificationDeepLink?.messageArrived();
          if (!mounted) return;
          // Don't badge the tab the operator is already looking at.
          if (_tab != 2) { // Feed (099/FR-012: shifted by Dashboard at index 0)
            setState(() => _unreadFeed++);
            localNotifications.postFeedNotification(
              identifier: message.pushedAt.toIso8601String(),
              preview: message.contentType == MessageContentType.text
                  ? message.content
                  : 'New ${message.contentType.name} message',
              badgeCount: combinedBadgeCount(
                unreadFeed: feedStore.unreadCount,
                unreadChat: conversationStore.unreadCount,
              ),
            );
          }
          _recomputeBadge();
        },
      );
      wireHeartbeat(widget.client);
      CaptureClient(
        askClient: askClient,
        capture: (type) => CaptureScreen.capture(context, type),
      ).wire(widget.client);
      // feature 072: answers Apple Watch companion-app requests using these
      // SAME instances -- the watch has no connection of its own (FR-011).
      // Registered before `await capabilities.register()` below: that's a
      // network round trip to the Border, and the watch relay must not wait
      // on it -- a slow/hung Border registration must not leave the watch's
      // native side waiting on a Dart handler that was never wired up.
      final watchRelay = WatchRelay(
          approvalClient: approvalClient,
          askClient: askClient,
          feedStore: feedStore,
          conversationStore: conversationStore,
          heartbeatStore: DeviceHeartbeatStore(dir));
      const MethodChannel('ca.automateyournetwork.netclaw/watch_relay')
          .setMethodCallHandler((call) => watchRelay.handle(
                call.method,
                (call.arguments as Map?)?.cast<String, dynamic>() ?? {},
              ));

      final notificationDeepLink = NotificationDeepLink(
        store: feedStore,
        conversationStore: conversationStore,
        openMessage: (message) {
          if (!mounted) return;
          setState(() {
            _tab = 2; // Feed (099/FR-012: shifted by Dashboard at index 0)
            _highlightPushedAt = message.pushedAt;
          });
        },
        openChatTurn: (turn) {
          if (!mounted) return;
          setState(() {
            _tab = 1; // Chat (099/FR-012: shifted by Dashboard at index 0)
            _highlightTaskId = turn.taskId;
          });
        },
        // Spec 107/FR-003: the tapped message never turned up within the bound.
        // Land the operator on the Feed rather than leaving them wherever the app
        // happened to open — they tapped a notification about a message, so the
        // feed is the least surprising place to be, and spec 106 means the
        // message will appear there whenever it does arrive.
        onOpenTimedOut: () {
          if (!mounted) return;
          setState(() => _tab = 2); // Feed
        },
      );
      await localNotifications.initialize(
        onResponse: (response) => handleNotificationResponse(
          response,
          approvalClient: approvalClient,
          deepLink: notificationDeepLink,
        ),
      );
      final permissionGranted = await localNotifications.requestPermission();
      if (mounted) {
        setState(() {
          _localNotifications = localNotifications;
          _notificationDeepLink = notificationDeepLink;
          _localNotificationsPermissionDenied = !permissionGranted;
        });
      }

      conversationStore.onCompleted = (turn) {
        if (!mounted) return;
        if (_tab != 1) { // Chat (099/FR-012: shifted by Dashboard at index 0)
          localNotifications.postChatNotification(
            identifier: turn.taskId,
            preview: turn.answerText ?? 'Answer ready.',
            badgeCount: combinedBadgeCount(
              unreadFeed: feedStore.unreadCount,
              unreadChat: conversationStore.unreadCount,
            ),
          );
        }
        _recomputeBadge();
      };

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
          if (mounted) setState(() => _tab = 1); // Chat (099/FR-012: shifted by Dashboard at index 0)
        },
      );
      _deepLinkListener!.start();
      _wireReconnect();
      _tryRegisterPush();
      // 099/FR-001: reconcile the OS badge to the true unread count on cold
      // launch too, not just on the reactive arrival/acknowledge triggers
      // above -- otherwise a badge left stale by a push delivered while the
      // app was fully closed never self-corrects until the next new arrival.
      _recomputeBadge();
    });
  }

  /// Combined badge (073/FR-008): unacknowledged Feed + unacknowledged Chat,
  /// recomputed on every new arrival (here) and every acknowledge/delete
  /// (wired alongside those actions once built) so it never drifts stale.
  Future<void> _recomputeBadge() async {
    final feedStore = _feedStore;
    final conversationStore = _conversationStore;
    final notifications = _localNotifications;
    if (feedStore == null || conversationStore == null || notifications == null) return;
    await notifications.setBadgeCount(
      combinedBadgeCount(
        unreadFeed: feedStore.unreadCount,
        unreadChat: conversationStore.unreadCount,
      ),
    );
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
        debugPrint('[edge-diag] reconnected ${DateTime.now().toIso8601String()}');
        if (mounted) setState(() => _connected = true);
        // A reconnect is the moment to collect anything that finished while we
        // were away: `ask_result` is best-effort and is simply not sent when no
        // channel is live, and the Border never re-pushes spontaneously.
        _reconcileAfterReconnect();
      },
      // Revoked mid-session: the pinned identity is gone and no amount of
      // retrying brings it back. Drop the persisted enrollment and return to
      // the enrollment gate, matching what a cold start already does — rather
      // than spinning on a dead identity forever.
      onUnrecoverable: _handleRevoked,
      initiallyConnected: true,
    );
    widget.client.onDisconnected = () {
      debugPrint('[edge-diag] disconnected ${DateTime.now().toIso8601String()}');
      supervisor.notifyDisconnected();
      if (mounted) setState(() => _connected = false);
    };
    supervisor.run(); // permanent retry loop; stopped in dispose()
    _reconnectSupervisor = supervisor;
  }

  /// Best-effort FCM/APNs token registration (066 US3) — safe to attempt
  /// with no real Firebase project configured: any failure here just means the
  /// push-notification fallback isn't available, never something that blocks
  /// or crashes the rest of the app.
  ///
  /// Notification-tap deep-linking (T032) is wired here too, and only on the
  /// success path — `NotificationDeepLink` calls into `FirebaseMessaging`,
  /// which throws if `initializeApp` didn't succeed.
  ///
  /// The outcome is recorded in [_pushStatus] rather than discarded. This used
  /// to be one bare `catch` that logged everything at the same level, so a
  /// genuinely broken push setup looked exactly like an unconfigured build —
  /// and since the app works fine without push, nobody would notice.
  Future<void> _tryRegisterPush() async {
    PushStatus status;
    try {
      await Firebase.initializeApp();
      status = await PushRegistration(widget.client).registerCurrentToken();
      if (status == PushStatus.registered) {
        await _wireNotificationDeepLink();
        _wireForegroundPushIngest();
      }
    } catch (e, stack) {
      status = classifyPushError(e);
      if (status == PushStatus.failed) {
        // Configured but broken: a real defect, not an expected absence.
        FlutterError.reportError(FlutterErrorDetails(
          exception: e,
          stack: stack,
          library: 'netclaw push',
          context: ErrorDescription('registering for push notifications'),
        ));
      } else {
        debugPrint('push disabled: no Firebase project in this build ($e)');
      }
    }
    if (mounted) setState(() => _pushStatus = status);
  }

  /// Tapping a delivered REMOTE push (or cold-starting from one) jumps to the
  /// Feed tab with the referenced message scrolled into view and
  /// highlighted. Reuses the SAME `NotificationDeepLink` instance the local
  /// notification handler already uses (073) — `.wire()` just adds the
  /// Firebase remote-tap listener on top of it, rather than constructing a
  /// second, parallel dispatcher.
  Future<void> _wireNotificationDeepLink() async {
    await _notificationDeepLink?.wire();
  }

  /// Spec 107/US2: record a pushed message straight from its payload, so it is
  /// readable without waiting for — or even having — a live channel.
  ///
  /// The sender has always included the full content beside the banner; nothing
  /// consumed it until now, which is why a push to a disconnected device drew a
  /// notification and left the feed empty.
  ///
  /// Safe only because [MessageFeedStore.append] deduplicates: this message will
  /// also arrive over the live channel when the Border replays it, and without
  /// dedup the operator would see two of everything.
  ///
  /// Foreground only, deliberately. Background execution for a data-carrying push
  /// is at the OS's discretion on both platforms, so treating it as a delivery
  /// guarantee would reintroduce the silent-loss class spec 106 removed. Spec 106's
  /// queue-and-replay stays the guarantee; this is an acceleration of it, and a
  /// push that arrives while backgrounded still lands in the feed via replay.
  void _wireForegroundPushIngest() {
    final store = _feedStore;
    if (store == null) return;
    FirebaseMessaging.onMessage.listen((remote) async {
      final outcome = await ingestPushPayload(
        remote.data,
        store: store,
        onApproval: (params) => _approvalClient?.receiveApproval(params),
        onMessage: (_) {
          _notificationDeepLink?.messageArrived();
          if (!mounted) return;
          if (_tab != 2) setState(() => _unreadFeed++);
          _recomputeBadge();
        },
      );
      if (outcome == PushIngestOutcome.rejected) {
        // Not fatal: the Border still replays it over the live channel.
        debugPrint('push payload not usable; awaiting replay instead');
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(_badgeLifecycleObserver);
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

  // 099/FR-012: Dashboard is index 0, the default landing tab -- everything
  // else shifted one slot right of what it was before this feature.
  static const _titles = ['Dashboard', 'Chat', 'Feed', 'Approvals', 'Settings'];

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
      DashboardScreen(
        snapshot: buildDashboardSnapshot(
          connected: _connected,
          stored: widget.stored,
          feedStore: _feedStore,
          conversationStore: _conversationStore,
          approvalClient: _approvalClient,
        ),
      ),
      ChatScreen(
        askClient: _askClient!,
        store: _conversationStore!,
        highlightTaskId: _highlightTaskId,
        onChanged: _recomputeBadge,
      ),
      FeedScreen(
        store: _feedStore!,
        highlightPushedAt: _highlightPushedAt,
        onChanged: _recomputeBadge,
      ),
      ApprovalsScreen(approvalClient: _approvalClient!),
      SettingsScreen(
        capabilities: _capabilities!,
        pushStatus: _pushStatus,
        localNotificationsPermissionDenied: _localNotificationsPermissionDenied,
      ),
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
          _buildOverflowMenu(),
        ],
      ),
      // IndexedStack, not `pages[_tab]`. Indexing keeps only the selected page
      // in the tree, so switching tabs DISPOSES the previous page's State —
      // which reset the chat's scroll position (and re-ran its load + stale-turn
      // reconciliation) every single time you came back to it. IndexedStack
      // keeps all four mounted and just changes which is painted.
      body: IndexedStack(index: _tab, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() {
          _tab = i;
          // Opening the Feed is what marks it read; clear the badge and the
          // one-shot notification highlight together. Indices shifted by one
          // (099/FR-012) now that Dashboard occupies index 0.
          if (i == 2) {
            _unreadFeed = 0;
            _highlightPushedAt = null;
          }
          if (i == 1) _highlightTaskId = null;
        }),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
          const NavigationDestination(icon: Icon(Icons.chat), label: 'Chat'),
          NavigationDestination(
            // Without this the operator has no way to know a Border push
            // arrived — messages land silently in the Feed while they sit on
            // Chat. Observed with a real tester: a push delivered successfully
            // and went unnoticed entirely.
            icon: Badge(
              isLabelVisible: _unreadFeed > 0,
              label: Text('$_unreadFeed'),
              child: const Icon(Icons.notifications),
            ),
            label: 'Feed',
          ),
          const NavigationDestination(icon: Icon(Icons.verified_user), label: 'Approvals'),
          const NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }

  /// Pull in the outcome of any turn that finished while this device was
  /// disconnected. Driven by the reconnect supervisor rather than by widget
  /// construction, so it keeps working now that IndexedStack keeps every tab
  /// mounted for the lifetime of the session.
  Future<void> _reconcileAfterReconnect() async {
    final askClient = _askClient;
    final store = _conversationStore;
    if (askClient == null || store == null) return; // not wired up yet
    await reconcileStaleTurns(askClient, store,
        onChanged: () { if (mounted) setState(() {}); });
  }

  /// The Border revoked this device while it was running. Clear the persisted
  /// enrollment and send the operator back to the enrollment gate with an
  /// explanation, so the state on screen matches reality.
  Future<void> _handleRevoked() async {
    final dir = await getApplicationDocumentsDirectory();
    await EnrollmentStore(dir).clear();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const EnrollmentGate()),
    );
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text('This device was removed by your Border. Enroll again to reconnect.'),
      duration: Duration(seconds: 6),
    ));
  }

  /// Per-tab destructive actions, behind a confirmation. Both clears are
  /// on-device only — the Border keeps its own GAIT audit trail either way.
  Widget _buildOverflowMenu() {
    return PopupMenuButton<String>(
      onSelected: (v) {
        if (v == 'clear_chat') _confirmClearChat();
        if (v == 'clear_feed') _confirmClearFeed();
      },
      itemBuilder: (context) => [
        if (_tab == 1) // Chat (099/FR-012: shifted by Dashboard at index 0)
          const PopupMenuItem(value: 'clear_chat', child: Text('Clear chat history')),
        if (_tab == 2) // Feed (099/FR-012: shifted by Dashboard at index 0)
          const PopupMenuItem(value: 'clear_feed', child: Text('Clear all messages')),
      ],
    );
  }

  Future<bool> _confirm(String title, String body, String action) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(action)),
        ],
      ),
    );
    return ok ?? false;
  }

  Future<void> _confirmClearChat() async {
    final store = _conversationStore;
    if (store == null) return;
    // In-progress requests are now KEPT rather than destroyed. This dialog used
    // to warn that a running request's answer "will no longer appear here" —
    // i.e. it described the data loss instead of preventing it. Reported by a
    // tester as a bug, and rightly so: clearing history should not silently
    // discard work the Border is still doing.
    final extra = store.hasInProgressTurns
        ? '\n\nRequests still in progress will be kept so their answers can '
            'still arrive.'
        : '';
    if (!await _confirm('Clear chat history?',
        'Deletes finished requests from this phone. Your Border keeps its own '
        'audit record.$extra',
        'Clear')) {
      return;
    }
    await store.clear();
    if (mounted) setState(() {});
  }

  Future<void> _confirmClearFeed() async {
    final store = _feedStore;
    if (store == null) return;
    if (!await _confirm('Clear all messages?',
        'Deletes every message your Border has pushed to this phone. They '
        'cannot be retrieved again from here.',
        'Clear')) {
      return;
    }
    await store.clear();
    if (mounted) {
      setState(() {
        _unreadFeed = 0;
        _highlightPushedAt = null;
      });
    }
  }
}
