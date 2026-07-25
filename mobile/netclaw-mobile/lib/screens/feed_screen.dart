import 'dart:convert';

import 'package:flutter/material.dart';

import '../ncfed/message_feed.dart';
import 'empty_state.dart';

/// Renders messages the Border has explicitly pushed (US2/T026), in
/// chronological order. `voice` playback is out of scope here (shown as a
/// placeholder chip) — a dedicated audio player is a follow-up, not part of
/// this feature's minimum feed rendering requirement.
class FeedScreen extends StatefulWidget {
  final MessageFeedStore store;

  /// When a push notification is tapped (T032, `NotificationDeepLink`), the
  /// message it referred to is scrolled into view and highlighted. Identified
  /// by `pushedAt` because that is the field the FCM/APNs `data` payload
  /// carries — see `findMessageForNotificationData`.
  final DateTime? highlightPushedAt;

  const FeedScreen({super.key, required this.store, this.highlightPushedAt});

  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  bool _loading = true;
  final _highlightKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    widget.store.load().then((_) {
      if (mounted) setState(() => _loading = false);
      _scrollToHighlight();
    });
  }

  @override
  void didUpdateWidget(FeedScreen old) {
    super.didUpdateWidget(old);
    // A second notification tap while the feed is already open.
    if (widget.highlightPushedAt != old.highlightPushedAt) _scrollToHighlight();
  }

  /// Deferred to the next frame: the target tile only has a render object
  /// once the list has been laid out.
  void _scrollToHighlight() {
    if (widget.highlightPushedAt == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = _highlightKey.currentContext;
      if (ctx != null) Scrollable.ensureVisible(ctx, alignment: 0.3);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final messages = List.of(widget.store.messages)
      ..sort((a, b) => a.pushedAt.compareTo(b.pushedAt));
    if (messages.isEmpty) {
      return const EmptyState(
        asset: 'assets/illustrations/empty_feed.png',
        text: 'No messages from the Border yet.',
      );
    }
    return ListView.builder(
      itemCount: messages.length,
      itemBuilder: (context, index) {
        final message = messages[index];
        final highlighted = widget.highlightPushedAt != null &&
            message.pushedAt == widget.highlightPushedAt;
        return _MessageTile(
          key: highlighted ? _highlightKey : null,
          message: message,
          highlighted: highlighted,
        );
      },
    );
  }
}

class _MessageTile extends StatelessWidget {
  final EdgeMessage message;
  final bool highlighted;

  const _MessageTile({super.key, required this.message, this.highlighted = false});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      color: highlighted ? scheme.secondaryContainer : null,
      shape: highlighted
          ? RoundedRectangleBorder(
              side: BorderSide(color: scheme.secondary, width: 2),
              borderRadius: BorderRadius.circular(12),
            )
          : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${message.designatedBy} · ${message.pushedAt.toLocal()}',
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(height: 8),
            _content(context),
          ],
        ),
      ),
    );
  }

  Widget _content(BuildContext context) {
    switch (message.contentType) {
      case MessageContentType.text:
        return Text(message.content);
      case MessageContentType.image:
        try {
          return Image.memory(base64Decode(message.content));
        } catch (_) {
          return const Text('[image could not be decoded]');
        }
      case MessageContentType.voice:
        return const Chip(
          avatar: Icon(Icons.mic, size: 18),
          label: Text('Voice message'),
        );
    }
  }
}
