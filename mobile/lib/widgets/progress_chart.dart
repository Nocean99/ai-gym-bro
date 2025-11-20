import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class ProgressChart extends StatelessWidget {
  final Map<String, dynamic> chartData;

  const ProgressChart({
    Key? key,
    required this.chartData,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final exercise = chartData['exercise'] ?? 'Exercise';
    final dataPoints = chartData['data_points'] as List<dynamic>;

    if (dataPoints.isEmpty) {
      return Card(
        margin: const EdgeInsets.all(12),
        color: Colors.grey[850],
        child: const Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'No data available',
            style: TextStyle(color: Colors.white),
          ),
        ),
      );
    }

    if (dataPoints.length == 1) {
      return Card(
        margin: const EdgeInsets.all(12),
        color: Colors.grey[850],
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.info_outline, color: Colors.orange, size: 24),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '$exercise Progress',
                      style: const TextStyle(
                        color: Colors.orange,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'You need at least 2 workouts to see a progress chart!',
                style: TextStyle(color: Colors.grey[300], fontSize: 16),
              ),
              const SizedBox(height: 8),
              Text(
                'Current: ${dataPoints[0]['max_weight']} lbs',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Keep logging to see your progress over time! 💪',
                style: TextStyle(color: Colors.grey[400], fontSize: 14),
              ),
            ],
          ),
        ),
      );
    }

    // Reverse so oldest is first (left side of chart)
    final reversedData = dataPoints.reversed.toList();

    // Convert data to chart spots
    List<FlSpot> spots = [];
    double minY = double.infinity;
    double maxY = double.negativeInfinity;

    for (int i = 0; i < reversedData.length; i++) {
      final point = reversedData[i];
      final weight = (point['max_weight'] as num?)?.toDouble() ?? 0;
      spots.add(FlSpot(i.toDouble(), weight));
      
      if (weight < minY) minY = weight;
      if (weight > maxY) maxY = weight;
    }

    // Add padding to Y axis
    // Handle edge case where all values are the same
    if (minY == maxY) {
      minY = (minY - 10).clamp(0, double.infinity);
      maxY = maxY + 10;
    } else {
      final yPadding = (maxY - minY) * 0.1;
      minY = (minY - yPadding).clamp(0, double.infinity);
      maxY = maxY + yPadding;
    }

    return Card(
      margin: const EdgeInsets.all(12),
      color: Colors.grey[850],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.show_chart, color: Colors.orange, size: 24),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '$exercise Progress',
                    style: const TextStyle(
                      color: Colors.orange,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Chart
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  minY: minY,
                  maxY: maxY,
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: (maxY - minY) > 0 ? (maxY - minY) / 5 : 1,
                    getDrawingHorizontalLine: (value) {
                      return FlLine(
                        color: Colors.grey[700],
                        strokeWidth: 1,
                      );
                    },
                  ),
                  titlesData: FlTitlesData(
                    show: true,
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            '${value.toInt()}',
                            style: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 12,
                            ),
                          );
                        },
                        reservedSize: 40,
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index >= 0 && index < reversedData.length) {
                            final date = reversedData[index]['date'] as String;
                            final parts = date.split('-');
                            if (parts.length >= 3) {
                              return Padding(
                                padding: const EdgeInsets.only(top: 8.0),
                                child: Text(
                                  '${parts[1]}/${parts[2]}',
                                  style: TextStyle(
                                    color: Colors.grey[400],
                                    fontSize: 10,
                                  ),
                                ),
                              );
                            }
                          }
                          return const Text('');
                        },
                        reservedSize: 30,
                        interval: reversedData.length > 7 ? 2 : 1,
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: Colors.orange,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: FlDotData(
                        show: true,
                        getDotPainter: (spot, percent, barData, index) {
                          return FlDotCirclePainter(
                            radius: 4,
                            color: Colors.orange,
                            strokeWidth: 2,
                            strokeColor: Colors.grey[850]!,
                          );
                        },
                      ),
                      belowBarData: BarAreaData(
                        show: true,
                        color: Colors.orange.withOpacity(0.2),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            _buildStats(reversedData),
          ],
        ),
      ),
    );
  }

  Widget _buildStats(List<dynamic> dataPoints) {
    final firstWeight = dataPoints.first['max_weight'] as num?;
    final lastWeight = dataPoints.last['max_weight'] as num?;
    final change = lastWeight != null && firstWeight != null
        ? lastWeight - firstWeight
        : 0;
    final percentChange = firstWeight != null && firstWeight > 0
        ? (change / firstWeight * 100)
        : 0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[800],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem('Start', '${firstWeight ?? 0} lbs'),
          _buildStatItem('Current', '${lastWeight ?? 0} lbs'),
          _buildStatItem(
            'Change',
            '${change >= 0 ? '+' : ''}${change.toStringAsFixed(0)} lbs (${percentChange.toStringAsFixed(1)}%)',
            color: change >= 0 ? Colors.green : Colors.red,
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, {Color? color}) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.grey[400],
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            color: color ?? Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}