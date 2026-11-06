import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:url_launcher/url_launcher.dart';

import '../main.dart';
import '../ncfed/app_lock.dart';
import '../ncfed/capability_registration.dart';
import '../ncfed/push_registration.dart';
import '../ncfed/theme_preference.dart';

/// 109/research.md R5: human-readable labels for the fixed grace-period
/// choice set.
String describeGracePeriod(Duration d) {
  if (d == Duration.zero) return 'Immediately';
  if (d.inMinutes >= 1) {
    return '${d.inMinutes} minute${d.inMinutes == 1 ? '' : 's'}';
  }
  return '${d.inSeconds} seconds';
}

/// Human-readable explanation of why notifications are or aren't working.
/// Push failing is silent by design — the app is fully usable without it — so
/// without this the only symptom is notifications that never arrive.
({String title, String detail, IconData icon}) describePushStatus(
  PushStatus status,
) =>
    switch (status) {
      PushStatus.registered => (
          title: 'Notifications on',
          detail: 'Answers arrive even when the app is closed.',
          icon: Icons.notifications_active_outlined,
        ),
      PushStatus.notConfigured => (
          title: 'Notifications unavailable',
          detail: 'This build has no push configuration. '
              'Answers only arrive while the app is open.',
          icon: Icons.notifications_off_outlined,
        ),
      PushStatus.permissionDenied => (
          title: 'Notifications blocked',
          detail: 'You declined the notification permission. '
              'Turn it on in your device settings to be notified.',
          icon: Icons.notifications_paused_outlined,
        ),
      PushStatus.failed => (
          title: 'Notifications failed',
          detail: 'Push is configured but registration failed. '
              'Report this — it is a bug, not a setting.',
          icon: Icons.error_outline,
        ),
      PushStatus.unknown => (
          title: 'Notifications starting…',
          detail: 'Still registering.',
          icon: Icons.hourglass_empty,
        ),
    };

/// Per-type capture toggles (feature 068, US3/T019/FR-007a) — disabling a
/// type here means the Border can never even discover it as a possibility,
/// not merely have a request for it refused.
class SettingsScreen extends StatefulWidget {
  final CapabilityRegistration capabilities;
  final PushStatus pushStatus;

  /// 073/FR-020: the operator declined the local-notification permission
  /// prompt. Every other capability keeps working regardless — this just
  /// makes that limitation discoverable, non-nagging (a single static line,
  /// never a repeated dialog).
  final bool localNotificationsPermissionDenied;

  /// 105/US2/FR-005/FR-006: clears the persisted enrollment and returns to
  /// the enrollment gate, purely from local state — this callback is given
  /// no `EdgeClient`/Border access at all, so the removal it performs
  /// structurally cannot depend on a live connection.
  final Future<void> Function() onRemoveDevice;
  final Future<void> Function()? onRecoverConnection;

  /// Injectable so tests never touch the real biometric platform channel —
  /// mirrors `approval_confirmation.dart`'s own `authenticate` parameter and
  /// its default (105/FR-004: same security posture as approvals).
  final Future<bool> Function(String reason)? authenticate;

  /// Injectable so tests never touch the real secure-storage platform
  /// channel (109/FR-008, research.md R4).
  final AppLockPreference? appLockPreference;

  /// Injectable so tests never touch the real secure-storage platform
  /// channel (115/FR-008, research.md R6) — same pattern as
  /// [appLockPreference] above.
  final ThemePreference? themePreference;

  const SettingsScreen({
    super.key,
    required this.capabilities,
    required this.onRemoveDevice,
    this.onRecoverConnection,
    this.pushStatus = PushStatus.unknown,
    this.localNotificationsPermissionDenied = false,
    this.authenticate,
    this.appLockPreference,
    this.themePreference,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  static const _labels = {
    'camera.capture': 'Photo capture',
    'camera.record_video': 'Video capture',
    'audio.record': 'Audio recording',
  };

  String? _error;

  late final AppLockPreference _appLock = widget.appLockPreference ?? AppLockPreference();
  bool _appLockEnabled = false;
  Duration _gracePeriod = defaultGracePeriod;
  bool _appLockLoaded = false;

  late final ThemePreference _themePreference = widget.themePreference ?? ThemePreference();

  @override
  void initState() {
    super.initState();
    _loadAppLock();
  }

  Future<void> _loadAppLock() async {
    final enabled = await _appLock.isEnabled();
    final grace = await _appLock.gracePeriod();
    if (mounted) {
      setState(() {
        _appLockEnabled = enabled;
        _gracePeriod = grace;
        _appLockLoaded = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        if (widget.onRecoverConnection != null)
          ListTile(
            leading: const Icon(Icons.sync),
            title: const Text('Recover connection'),
            subtitle: const Text(
              'Verify a replacement port for this enrolled Border',
            ),
            onTap: widget.onRecoverConnection,
          ),
        if (_error != null)
          Container(
            width: double.infinity,
            color: Colors.red.shade50,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Text(_error!, style: TextStyle(color: Colors.red.shade900)),
          ),
        for (final capability in kAllCaptureCapabilities)
          SwitchListTile(
            title: Text(_labels[capability] ?? capability),
            subtitle: const Text('The Border can request this while disconnected too'),
            value: widget.capabilities.enabled.contains(capability),
            onChanged: (value) async {
              setState(() => _error = null);
              try {
                await widget.capabilities.setEnabled(capability, value);
              } catch (e) {
                if (mounted) setState(() => _error = 'Could not update: $e');
              }
              if (mounted) setState(() {});
            },
          ),
        const Divider(),
        Builder(builder: (context) {
          final push = describePushStatus(widget.pushStatus);
          return ListTile(
            leading: Icon(push.icon),
            title: Text(push.title),
            subtitle: Text(push.detail),
          );
        }),
        if (widget.localNotificationsPermissionDenied)
          const ListTile(
            leading: Icon(Icons.notifications_off_outlined),
            title: Text('Local notifications blocked'),
            subtitle: Text(
              'You declined the notification permission, so banners, the app '
              'badge, and watch mirroring are unavailable. Everything else — '
              'Feed, Chat, Approvals, History — still works normally. Turn it '
              'on in your device settings to be notified.',
            ),
          ),
        const Divider(),
        if (_appLockLoaded) ...[
          SwitchListTile(
            title: const Text('Require Face ID to open NetClaw'),
            subtitle: const Text(
              'Locks the app on launch and after being backgrounded past the '
              'grace period below. Off by default.',
            ),
            value: _appLockEnabled,
            onChanged: (value) async {
              await _appLock.setEnabled(value);
              if (mounted) setState(() => _appLockEnabled = value);
            },
          ),
          if (_appLockEnabled)
            ListTile(
              title: const Text('Grace period'),
              subtitle: const Text('How long the app stays unlocked after backgrounding'),
              trailing: DropdownButton<Duration>(
                value: _gracePeriod,
                items: [
                  for (final choice in gracePeriodChoices)
                    DropdownMenuItem(value: choice, child: Text(describeGracePeriod(choice))),
                ],
                onChanged: (value) async {
                  if (value == null) return;
                  await _appLock.setGracePeriod(value);
                  if (mounted) setState(() => _gracePeriod = value);
                },
              ),
            ),
          const Divider(),
        ],
        ValueListenableBuilder<ThemeMode>(
          valueListenable: NetClawMobileApp.themeMode,
          builder: (context, mode, _) => ListTile(
            title: const Text('Appearance'),
            subtitle: const Text('Light, Dark, or follow this device\'s system setting'),
            trailing: DropdownButton<ThemeMode>(
              value: mode,
              items: const [
                DropdownMenuItem(value: ThemeMode.system, child: Text('System')),
                DropdownMenuItem(value: ThemeMode.light, child: Text('Light')),
                DropdownMenuItem(value: ThemeMode.dark, child: Text('Dark')),
              ],
              onChanged: (value) async {
                if (value == null) return;
                await _themePreference.save(value);
                NetClawMobileApp.themeMode.value = value;
              },
            ),
          ),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.privacy_tip_outlined),
          title: const Text('Privacy Policy'),
          onTap: () => launchUrl(
            Uri.parse('https://automateyournetwork.github.io/netclaw/privacy-policy.html'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        const Divider(),
        ListTile(
          leading: Icon(Icons.logout, color: Colors.red.shade700),
          title: Text('Remove this device', style: TextStyle(color: Colors.red.shade700)),
          subtitle: const Text(
            'Clears this enrollment and returns to the QR-scan screen. '
            'Works even if your Border is unreachable.',
          ),
          onTap: _removeDevice,
        ),
      ],
    );
  }

  /// 105/US2/FR-004: the biometric prompt itself IS the confirmation step —
  /// same convention `approval_confirmation.dart` already established for
  /// every other destructive/irreversible action in this app, no separate
  /// "are you sure?" dialog on top of it.
  Future<void> _removeDevice() async {
    final auth = widget.authenticate ??
        (String reason) => LocalAuthentication().authenticate(localizedReason: reason);
    final bool authenticated;
    try {
      authenticated = await auth('Confirm removing this device\'s enrollment');
    } catch (_) {
      return; // unavailable/errored -- do nothing, same as a failed attempt
    }
    if (!authenticated) return; // cancelled/failed -- do nothing
    await widget.onRemoveDevice();
  }
}
