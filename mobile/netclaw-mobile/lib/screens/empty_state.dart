import 'package:flutter/material.dart';

/// Shared "nothing here yet" layout for Feed/Approvals — a small brand
/// illustration above the existing plain-text message, not a replacement
/// for it.
class EmptyState extends StatelessWidget {
  final String asset;
  final String text;

  const EmptyState({super.key, required this.asset, required this.text});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Image.asset(asset, width: 140),
          const SizedBox(height: 16),
          Text(text, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}
