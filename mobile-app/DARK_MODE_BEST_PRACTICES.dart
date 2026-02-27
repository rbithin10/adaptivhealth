/*
Light Mode Best Practices & Common Mistakes

This document lists common pitfalls and how to avoid them
when implementing light mode in screens.
*/

// =============================================================================
// ❌ COMMON MISTAKES (and how to fix them)
// =============================================================================

// MISTAKE 1: Hard-coded Colors
// ❌ WRONG
class BadVitalCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,  // ❌ BREAKS IN LIGHT MODE
      child: Text(
        'HR: 72',
        style: TextStyle(color: Colors.black),  // ❌ Invisible in some cases
      ),
    );
  }
}

// ✅ CORRECT
class GoodVitalCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AdaptivColors.primaryLight,  // ✅
      child: Text(
        'HR: 72',
        style: TextStyle(
          color: AdaptivColors.primaryDark,  // ✅
        ),
      ),
    );
  }
}

// =============================================================================

// MISTAKE 2: Assuming Default Background
// ❌ WRONG
class BadAlert extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.red,  // ❌
      child: Text(
        'Alert!',
        style: TextStyle(color: Colors.white),
      ),
    );
  }
}

// ✅ CORRECT
class GoodAlert extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AdaptivColors.critical,
      child: Text(
        'Alert!',
        style: TextStyle(color: AdaptivColors.criticalText),
      ),
    );
  }
}

// =============================================================================

// MISTAKE 3: Forgetting Semantics for Accessibility
// ❌ WRONG - Screen readers won't know this is interactive
class BadButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {},
      child: Container(
        color: Colors.blue,
        child: Text('Custom Button'),  // No semantic info
      ),
    );
  }
}

// ✅ CORRECT - Screen readers know this is a button
class GoodButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      enabled: true,
      label: 'Custom Button',
      onTap: () {},
      child: GestureDetector(
        onTap: () {},
        child: Container(
          color: Colors.blue,
          child: Text('Custom Button'),
        ),
      ),
    );
  }
}

// =============================================================================

// MISTAKE 4: Tap Targets Too Small
// ❌ WRONG - Tap target < 48x48 logical pixels
class BadIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(4),  // ❌ Too little padding
      child: IconButton(
        icon: Icon(Icons.heart),
        onPressed: () {},
        iconSize: 20,  // ❌ Too small
      ),
    );
  }
}

// ✅ CORRECT - Tap target 48x48+
class GoodIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),  // ✅ Proper padding
      child: IconButton(
        icon: Icon(Icons.heart),
        onPressed: () {},
        iconSize: 32,  // ✅ Readable size
        tooltip: 'Add to favorites',  // ✅ Accessibility
      ),
    );
  }
}

// =============================================================================

// MISTAKE 5: Using Theme Colors Without Checking Contrast
// ❌ WRONG - Assumes specific contrast
class BadRiskBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Color(0xFFFF3B30),  // Red
      child: Text(
        'High',
        style: TextStyle(color: Color(0xFFFFB300)),  // Amber on red ❌
      ),
    );
  }
}

// ✅ CORRECT - Uses verified WCAG AA colors
class GoodRiskBadge extends StatelessWidget {
  final String riskLevel;
  
  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    
    return Container(
      color: AdaptivColors.getRiskColorForBrightness(
        riskLevel,
        brightness,
      ),  // ✅ Verified color
      child: Text(
        riskLevel.toUpperCase(),
        style: TextStyle(
          color: Colors.white,  // ✅ White always works on clinical colors
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

// =============================================================================
// ✅ BEST PRACTICES
// =============================================================================

/// PRACTICE 1: Always read brightness at the top of build()
class GoodScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // ✅ Get brightness first
    final brightness = MediaQuery.of(context).platformBrightness;
    
    // ✅ Define all colors upfront
    final bgColor = AdaptivColors.getBackgroundColor(brightness);
    final textColor = AdaptivColors.getTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    
    return Scaffold(
      backgroundColor: bgColor,
      body: Column(
        children: [
          // ✅ Reuse colors throughout
          Container(color: surfaceColor),
          Text('Hello', style: TextStyle(color: textColor)),
        ],
      ),
    );
  }
}

/// PRACTICE 2: Create helper variables for related colors
class GoodForm extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    
    // ✅ Group related colors
    final (bgColor, textColor, borderColor) = (
      AdaptivColors.getSurfaceColor(brightness),
      AdaptivColors.getTextColor(brightness),
      AdaptivColors.getBorderColor(brightness),
    );
    
    return TextField(
      decoration: InputDecoration(
        filled: true,
        fillColor: bgColor,
        border: OutlineInputBorder(
          borderSide: BorderSide(color: borderColor),
        ),
        labelStyle: TextStyle(color: textColor),
      ),
    );
  }
}

/// PRACTICE 3: Extract theme-aware widgets
// ✅ Reusable, testable component
class ThemeAwareCard extends StatelessWidget {
  final String title;
  final Widget child;
  
  const ThemeAwareCard({required this.title, required this.child});
  
  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    
    return Card(
      color: AdaptivColors.getSurfaceColor(brightness),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: AdaptivColors.getTextColor(brightness),
              ),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

// Usage:
class GoodRiskCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ThemeAwareCard(
      title: 'Risk Assessment',
      child: Text('High Risk'),
    );
  }
}

/// PRACTICE 4: Add semantics to important elements
class GoodHeartRateDisplay extends StatelessWidget {
  final int heartRate;
  
  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    final isDanger = heartRate > 180;
    
    return Semantics(
      label: 'Heart rate: $heartRate BPM${isDanger ? ' - DANGER' : ''}',
      button: false,
      enabled: true,
      child: Container(
        color: isDanger
            ? AdaptivColors.getRiskColorForBrightness('critical', brightness)
            : AdaptivColors.getPrimaryColor(brightness),
        child: Text(
          '$heartRate BPM',
          style: Theme.of(context).textTheme.displayMedium?.copyWith(
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

/// PRACTICE 5: Test in both modes
void main() {
  group('Dark mode tests', () {
    testWidgets('Card is visible in dark mode', (WidgetTester tester) async {
      // ✅ Set up dark mode
      final provider = ThemeProvider();
      await provider.setThemeMode(AppThemeMode.dark);
      
      await tester.pumpWidget(
        ChangeNotifierProvider.value(
          value: provider,
          child: MaterialApp(
            theme: buildAdaptivHealthTheme(Brightness.light),
            darkTheme: buildAdaptivHealthTheme(Brightness.dark),
            themeMode: provider.flutterThemeMode,
            home: const MyScreen(),
          ),
        ),
      );
      
      // ✅ Verify dark background is used
      expect(
        find.byWidgetPredicate((widget) =>
          widget is Container &&
          widget.color == AdaptivColors.background900
        ),
        findsWidgets,
      );
    });
  });
}

// =============================================================================
// 🎯 QUICK REFERENCE CHECKLIST
// =============================================================================

/*
When updating a screen for dark mode, verify:

[ ] Get brightness: `final brightness = MediaQuery.of(context).platformBrightness`
[ ] No hard-coded colors in UI (replace with AdaptivColors.get*())
[ ] Text is readable in both light and dark (contrast ≥ 4.5:1)
[ ] Buttons are ≥ 48x48 logical pixels (or use IconButton)
[ ] Clinical colors use brightness-aware variants
[ ] Key interactive elements have Semantics annotations
[ ] Tested in both light and dark modes
[ ] Images/graphics visible in both modes
[ ] Borders/shadows work in both modes

Result: Screen works in light, dark, and system themes! ✅
*/
