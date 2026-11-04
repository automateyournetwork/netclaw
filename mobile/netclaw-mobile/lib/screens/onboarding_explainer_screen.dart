import 'package:flutter/material.dart';
import 'cloud_owner_screen.dart';

/// 105/US1/FR-001/FR-002: shown before `EnrollmentScreen`'s QR scanner on
/// every launch where nothing is enrolled yet (an "unenrolled-state" screen,
/// not a "seen once, never again" one — see spec.md's edge cases). Never
/// shown once a valid enrollment is persisted. Makes no camera, network, or
/// permission calls of its own — purely explanatory copy plus one action.
///
/// Also carries the AI-data-sharing disclosure required before any question
/// or capture is ever sent (App Review Guidelines 5.1.1(i)/5.1.2(i)): the
/// operator's Border forwards typed/spoken questions, and any photo/video/
/// audio the operator chooses to send, to whichever AI model the Border
/// operator chose at setup -- entirely the operator's own decision, made at
/// installation time, and NOT something NetClaw itself enforces, defaults,
/// or controls. That may be a third-party provider (e.g. this project's own
/// reference config/openclaw.json happens to reference Anthropic, but that
/// is only this repo's own example configuration, not a requirement) or a
/// locally-run, fully offline/private model with no third-party data
/// sharing at all. Requiring the checkbox below before the primary action
/// is enabled is this app's one point of explicit, affirmative consent,
/// since it is the one screen every device sees exactly once, before any
/// data-sending feature becomes reachable.
class OnboardingExplainerScreen extends StatefulWidget {
  final VoidCallback onContinue;

  const OnboardingExplainerScreen({super.key, required this.onContinue});

  @override
  State<OnboardingExplainerScreen> createState() => _OnboardingExplainerScreenState();
}

class _OnboardingExplainerScreenState extends State<OnboardingExplainerScreen> {
  bool _acknowledged = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.hub_outlined, size: 64),
              const SizedBox(height: 24),
              const Text(
                'NetClaw Mobile is a companion app',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              const Text(
                'It connects to a self-hosted NetClaw Border server that you '
                '(or your operator) already run — it does not work as a '
                'standalone consumer app, and there is no NetClaw service to '
                'sign up for.\n\n'
                "If you don't already have a Border running, set one up "
                'first, then come back here to scan its enrollment QR code.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 16),
              const Text(
                'Any question you type or speak, and any photo, video, or '
                'audio you choose to send, is forwarded by your Border to '
                'whichever AI model your Border operator chose at setup — '
                'their own decision, not something NetClaw requires or '
                'controls. That may be a third-party provider, or a '
                'locally-run, fully offline/private model with no '
                'third-party sharing at all. See the Privacy Policy in '
                'Settings for details.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              CheckboxListTile(
                value: _acknowledged,
                onChanged: (value) => setState(() => _acknowledged = value ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text(
                  'I understand my questions and captures may be sent to a '
                  'third-party AI service',
                  style: TextStyle(fontSize: 14),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _acknowledged ? widget.onContinue : null,
                child: const Text('Agree and Continue'),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const CloudOwnerScreen())),
                child: const Text('Connect as cloud Border owner'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
