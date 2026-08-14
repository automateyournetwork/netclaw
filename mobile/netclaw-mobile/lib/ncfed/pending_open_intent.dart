import 'dart:async';

import 'message_feed.dart';

/// "The operator tapped a notification naming a message we may not have yet."
///
/// Why this exists (spec 107, research R1): the tap and the message's arrival
/// are genuinely concurrent, so the old single read of the feed store at tap
/// time could not win the race. Measured against a real Border — the channel
/// authenticated at 16:49:12.513 and the replayed message landed at
/// 16:49:15.514, a 3.0s gap set by the Border's own replay settle delay. Cold
/// app launch from a notification tap completes well inside that window, so the
/// single read was *guaranteed* to miss on a cold start, not merely likely to.
///
/// So the tap records an intent instead, and the intent resolves whenever the
/// named message shows up — immediately if it is already stored. It is
/// deliberately ignorant of *how* the message arrives: replay over the live
/// channel and ingest from a push payload both just add to the feed, and both
/// resolve this the same way.
///
/// In-memory only, by design (data-model.md): this describes a navigation
/// intent within one app session, not durable state. Persisting it would let a
/// stale intent hijack navigation on a later launch for a reason the operator
/// no longer remembers.
class PendingOpenIntent {
  /// Well inside SC-007's 10s outer bound, with room for channel auth plus the
  /// Border's replay settle plus retry margin on a slow network.
  static const Duration defaultTimeout = Duration(seconds: 8);

  final Duration timeout;

  /// Fires at most once per recorded intent, and never on expiry (contract §1.6).
  final void Function(EdgeMessage message) onOpen;

  /// Optional. Lets the caller land the operator somewhere usable when the
  /// named message never arrives (FR-003) rather than leaving them wherever the
  /// app happened to open.
  final void Function()? onExpire;

  String? _identifier;
  Timer? _timer;

  PendingOpenIntent({
    required this.onOpen,
    this.onExpire,
    this.timeout = defaultTimeout,
  });

  bool get isPending => _identifier != null;

  /// The `pushed_at` the pending notification named, or null if nothing is
  /// pending. Exposed for diagnostics and tests, not for callers to match on —
  /// matching belongs in [tryResolve] so the fire-once guarantee stays here.
  String? get identifier => _identifier;

  /// Records a tap. A second record discards the first (contract §1.2), so the
  /// operator lands on what they most recently tapped rather than the app
  /// racing between two.
  ///
  /// Does not itself navigate (contract §1.1) — call [tryResolve] for that.
  void record(String identifier) {
    _timer?.cancel();
    _identifier = identifier;
    _timer = Timer(timeout, _expire);
  }

  /// Resolves against the messages currently in the feed. Returns true if the
  /// named message was found and [onOpen] fired.
  ///
  /// Safe to call as often as you like — once resolved, the intent is cleared,
  /// so [onOpen] cannot fire twice for one tap.
  bool tryResolve(Iterable<EdgeMessage> messages) {
    final wanted = _identifier;
    if (wanted == null) return false;
    for (final message in messages) {
      if (messageIdentity(message.pushedAt) == identityOf(wanted)) {
        _clearTimer();
        _identifier = null;
        onOpen(message);
        return true;
      }
    }
    return false;
  }

  /// Abandons any pending intent without firing either callback.
  void cancel() {
    _clearTimer();
    _identifier = null;
  }

  void dispose() => cancel();

  void _expire() {
    if (_identifier == null) return;
    _clearTimer();
    _identifier = null;
    onExpire?.call();
  }

  void _clearTimer() {
    _timer?.cancel();
    _timer = null;
  }

  /// Parses a notification's `pushed_at` string to the same instant-based
  /// identity [messageIdentity] produces, so a `Z`-suffixed timestamp and an
  /// offset-suffixed one for the same moment still match. Returns null for
  /// anything unparseable, which then matches nothing.
  static int? identityOf(String pushedAt) {
    final parsed = DateTime.tryParse(pushedAt);
    return parsed == null ? null : messageIdentity(parsed);
  }
}
