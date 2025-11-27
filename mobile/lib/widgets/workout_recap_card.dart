import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/auth_service.dart';

/// Widget that displays a recap of logged workout sets with delete functionality
class WorkoutRecapCard extends StatefulWidget {
  final List<dynamic> loggedSets;
  final String backendUrl;

  const WorkoutRecapCard({
    Key? key,
    required this.loggedSets,
    required this.backendUrl,
  }) : super(key: key);

  @override
  State<WorkoutRecapCard> createState() => _WorkoutRecapCardState();
}

class _WorkoutRecapCardState extends State<WorkoutRecapCard> {
  late List<dynamic> sets;
  bool isDeleting = false;

  @override
  void initState() {
    super.initState();
    // Create a mutable copy of the sets list
    sets = List.from(widget.loggedSets);
  }

  /// Delete a specific set from the database
  Future<void> _deleteSet(int setId, int index) async {
    // Confirm deletion
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Set?'),
        content: const Text('Are you sure you want to delete this set?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => isDeleting = true);

    try {
      final userId = await AuthService().getUserId();

      if (userId == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Not logged in')),
          );
        }
        setState(() => isDeleting = false);
        return;
      }

      final response = await http.delete(
        Uri.parse('${widget.backendUrl}/delete-set'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'set_id': setId,
          'user_id': userId,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          setState(() {
            sets.removeAt(index);
          });

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Set deleted ✓'),
                backgroundColor: Colors.green,
                duration: Duration(seconds: 2),
              ),
            );
          }
        } else {
          throw Exception(data['error'] ?? 'Unknown error');
        }
      } else {
        throw Exception('Server returned ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error deleting set: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => isDeleting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // If all sets have been deleted, don't show the card
    if (sets.isEmpty) return const SizedBox.shrink();

    // Get the exercise name from the first set (all sets should be same exercise)
    final exerciseName = sets[0]['exercise'] ?? 'Exercise';

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(
                  Icons.check_circle,
                  color: Colors.green,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Logged your workout',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
              ],
            ),
            const Divider(height: 24),

            // Exercise name
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                exerciseName,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: Colors.blue[700],
                    ),
              ),
            ),

            // Sets list
            ...List.generate(sets.length, (index) {
              final set = sets[index];
              final setNumber = index + 1;
              final weight = set['weight'];
              final reps = set['reps'];
              final setCount = set['sets'];
              final unit = set['unit'] ?? 'lbs';

              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    // Set number badge
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: Colors.blue[600],
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          '$setNumber',
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),

                    // Set details
                    Expanded(
                      child: Text(
                        _formatSetDetails(weight, reps, setCount, unit),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),

                    // Delete button
                    IconButton(
                      icon: Icon(
                        Icons.delete_outline,
                        color: Colors.red[400],
                      ),
                      onPressed: isDeleting
                          ? null
                          : () => _deleteSet(set['id'], index),
                      tooltip: 'Delete this set',
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  /// Format the set details for display
  String _formatSetDetails(dynamic weight, dynamic reps, dynamic sets, String unit) {
    if (weight != null && reps != null) {
      if (sets != null && sets > 1) {
        return '$sets × ($weight $unit × $reps reps)';
      }
      return '$weight $unit × $reps reps';
    } else if (weight != null) {
      return '$weight $unit';
    } else if (reps != null) {
      return '$reps reps';
    }
    return 'Completed';
  }
}
