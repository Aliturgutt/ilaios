import 'package:flutter/foundation.dart';

@immutable
class EvidenceRecord {
  const EvidenceRecord({
    required this.sequence,
    required this.executionId,
    required this.artifactDigest,
    required this.action,
    required this.previousHash,
    required this.recordHash,
  });

  final int sequence;
  final String executionId;
  final String artifactDigest;
  final String action;
  final String previousHash;
  final String recordHash;

  factory EvidenceRecord.fromJson(Map<String, dynamic> json) {
    final sequence = json['sequence'];
    final executionId = json['execution_id'];
    final artifactDigest = json['artifact_digest'];
    final action = json['action'];
    final previousHash = json['previous_hash'];
    final recordHash = json['record_hash'];
    if (sequence is! int ||
        executionId is! String ||
        artifactDigest is! String ||
        action is! String ||
        previousHash is! String ||
        recordHash is! String ||
        executionId.isEmpty ||
        artifactDigest.isEmpty ||
        action.isEmpty ||
        recordHash.isEmpty) {
      throw const FormatException('Malformed verified evidence record');
    }
    return EvidenceRecord(
      sequence: sequence,
      executionId: executionId,
      artifactDigest: artifactDigest,
      action: action,
      previousHash: previousHash,
      recordHash: recordHash,
    );
  }
}
