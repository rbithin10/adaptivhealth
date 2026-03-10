/*
Week View Widget.

Shows a horizontal row of 7 days (Monday to Sunday) for the current week.
The user can tap any day to select it. The selected day is highlighted
in the app's primary color. Used on screens that show daily data.
*/

import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';

// A row of 7 day buttons representing the current week
class WeekView extends StatelessWidget {
  // Which day is currently selected (highlighted)
  final DateTime selectedDate;
  // Called when the user taps a different day
  final ValueChanged<DateTime> onDateSelected;

  const WeekView({
    super.key,
    required this.selectedDate,
    required this.onDateSelected,
  });

  @override
  Widget build(BuildContext context) {
    // Get today's date and time
    final now = DateTime.now();
    // Find Monday of this week by going back from today (weekday 1 = Monday)
    final startOfWeek = now.subtract(Duration(days: now.weekday - 1));
    // Create a list of all 7 days: Monday, Tuesday, ... Sunday
    final days = List.generate(7, (i) => startOfWeek.add(Duration(days: i)));

    // Lay out 7 responsive day tiles that scale to available width.
    return Row(
      children: days.map((date) {
        // Check if this day is the one the user selected (compare day, month, and year)
        final isSelected = date.day == selectedDate.day && date.month == selectedDate.month && date.year == selectedDate.year;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: GestureDetector(
              // When tapped, tell the parent screen which day was picked
              onTap: () => onDateSelected(date),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  // Selected day gets the primary color, others get a light background
                  color: isSelected ? AdaptivColors.primary : AdaptivColors.bg200,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    // Day abbreviation: M, T, W, T, F, S, S (weekday 1=Mon through 7=Sun)
                    Text(
                      ['M', 'T', 'W', 'T', 'F', 'S', 'S'][date.weekday - 1],
                      style: AdaptivTypography.label.copyWith(
                        // White text on selected day, grey on others
                        color: isSelected ? Colors.white : AdaptivColors.text600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    // The day number (1-31)
                    Text(
                      date.day.toString(),
                      style: AdaptivTypography.metricValue.copyWith(
                        color: isSelected ? Colors.white : AdaptivColors.text900,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
