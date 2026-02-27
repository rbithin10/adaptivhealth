"""
Generate test coverage report for AdaptivHealth backend.

This script:
1. Runs pytest with coverage
2. Parses coverage data
3. Updates TEST_COVERAGE_REPORT.md with results

Usage:
    python run_coverage.py
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# ANSI colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text):
    """Print colored header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def check_dependencies():
    """Verify pytest and pytest-cov are installed."""
    try:
        import pytest
        import pytest_cov
        print(f"{GREEN}✓{RESET} pytest and pytest-cov installed")
        return True
    except ImportError as e:
        print(f"{RED}✗{RESET} Missing dependency: {e}")
        print(f"\nInstall with: pip install pytest pytest-cov")
        return False

def run_pytest_coverage():
    """Run pytest with coverage reporting."""
    print_header("Running Test Suite with Coverage")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=json",
        "-v"
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        # Print stdout
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"\n{YELLOW}⚠{RESET} Some tests failed (see output above)")
            print(result.stderr)
        else:
            print(f"\n{GREEN}✓{RESET} All tests passed!")
        
        return result.returncode == 0, result.stdout
    
    except Exception as e:
        print(f"{RED}✗{RESET} Error running pytest: {e}")
        return False, ""

def parse_coverage_output(output):
    """Parse pytest coverage output to extract metrics."""
    lines = output.split('\n')
    coverage_data = {}
    
    # Find coverage table
    in_coverage_section = False
    for i, line in enumerate(lines):
        if 'Name' in line and 'Stmts' in line:
            in_coverage_section = True
            continue
        
        if in_coverage_section:
            if '----' in line:
                continue
            if 'TOTAL' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage_data['total'] = {
                        'statements': parts[1],
                        'missing': parts[2],
                        'coverage': parts[3].rstrip('%')
                    }
                break
            
            # Parse individual file lines
            if line.strip() and 'app/' in line:
                parts = line.split()
                if len(parts) >= 4:
                    filename = parts[0]
                    coverage_data[filename] = {
                        'statements': parts[1],
                        'missing': parts[2],
                        'coverage': parts[3].rstrip('%')
                    }
    
    return coverage_data

def generate_summary(coverage_data):
    """Generate summary statistics."""
    if not coverage_data or 'total' not in coverage_data:
        return None
    
    total = coverage_data['total']
    total_pct = float(total['coverage'])
    
    # Categorize files by coverage
    high_coverage = []  # >= 80%
    medium_coverage = []  # 60-79%
    low_coverage = []  # < 60%
    
    for filename, data in coverage_data.items():
        if filename == 'total':
            continue
        
        pct = float(data['coverage'])
        if pct >= 80:
            high_coverage.append((filename, pct))
        elif pct >= 60:
            medium_coverage.append((filename, pct))
        else:
            low_coverage.append((filename, pct))
    
    return {
        'total': total,
        'total_pct': total_pct,
        'high': sorted(high_coverage, key=lambda x: x[1], reverse=True),
        'medium': sorted(medium_coverage, key=lambda x: x[1], reverse=True),
        'low': sorted(low_coverage, key=lambda x: x[1])
    }

def print_summary(summary):
    """Print coverage summary to terminal."""
    if not summary:
        print(f"{RED}✗{RESET} Could not parse coverage data")
        return
    
    print_header("Coverage Summary")
    
    # Overall stats
    total = summary['total']
    total_pct = summary['total_pct']
    
    status_icon = GREEN if total_pct >= 80 else YELLOW if total_pct >= 60 else RED
    print(f"Overall Coverage: {status_icon}{total_pct}%{RESET}")
    print(f"Total Statements: {total['statements']}")
    print(f"Missing Lines: {total['missing']}\n")
    
    # High coverage files
    if summary['high']:
        print(f"{GREEN}High Coverage{RESET} (≥80%):")
        for filename, pct in summary['high'][:5]:
            print(f"  {GREEN}✓{RESET} {filename:<40} {pct:.1f}%")
        if len(summary['high']) > 5:
            print(f"  ... and {len(summary['high']) - 5} more\n")
        else:
            print()
    
    # Low coverage files (needs attention)
    if summary['low']:
        print(f"{RED}Low Coverage{RESET} (<60% - needs attention):")
        for filename, pct in summary['low']:
            print(f"  {RED}✗{RESET} {filename:<40} {pct:.1f}%")
        print()
    
    # Recommendations
    print(f"{BLUE}Recommendations:{RESET}")
    if total_pct >= 80:
        print(f"  {GREEN}✓{RESET} Excellent coverage! Ready for demo.")
    elif total_pct >= 60:
        print(f"  {YELLOW}⚠{RESET} Good coverage, but consider adding tests for low-coverage files.")
    else:
        print(f"  {RED}!{RESET} Coverage below 60%. Prioritize testing critical endpoints.")
    
    if summary['low']:
        print(f"\n  Focus on adding tests for:")
        for filename, pct in summary['low'][:3]:
            module = filename.replace('app/', '').replace('.py', '')
            print(f"    - {module}")

def main():
    """Main entry point."""
    print_header("AdaptivHealth Test Coverage Generator")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        return 1
    
    # Step 2: Run pytest with coverage
    success, output = run_pytest_coverage()
    
    # Step 3: Parse coverage data
    coverage_data = parse_coverage_output(output)
    
    # Step 4: Generate summary
    summary = generate_summary(coverage_data)
    
    # Step 5: Print summary
    print_summary(summary)
    
    # Step 6: Show next steps
    print_header("Next Steps")
    print(f"1. View detailed HTML report:")
    print(f"   {BLUE}start htmlcov/index.html{RESET} (Windows)")
    print(f"   {BLUE}open htmlcov/index.html{RESET} (Mac)")
    print()
    print(f"2. Update TEST_COVERAGE_REPORT.md with results")
    print()
    print(f"3. Focus on improving coverage for low-coverage files")
    print()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
