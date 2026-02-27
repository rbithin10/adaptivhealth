#!/usr/bin/env python3
"""
Validate branch coverage additions.

This script summarizes the test additions made and provides a checklist
for verification.
"""

import os
from pathlib import Path

TEST_FILES = {
    "tests/test_auth_extended.py": {
        "classes_added": ["TestAuthenticateUserHelper", "TestGetCurrentUserBranches", "TestConfirmPasswordResetAdditional"],
        "test_count": 9
    },
    "tests/test_main.py": {
        "classes_added": ["TestLifespan", "TestLogRequestsMiddlewareAdditional"],
        "test_count": 8
    },
    "tests/test_rbac_consent.py": {
        "classes_added": ["TestConsentWorkflowBranches"],
        "test_count": 6
    },
    "tests/test_vital_signs.py": {
        "classes_added": ["TestVitalSignsBranchCoverage"],
        "test_count": 5
    },
    "tests/test_activity.py": {
        "classes_added": ["TestActivityBranchCoverage"],
        "test_count": 1
    },
    "tests/test_predict_api.py": {
        "classes_added": ["TestPredictApiBranchCoverage"],
        "test_count": 5
    },
    "tests/test_user_api.py": {
        "classes_added": ["TestUserApiBranchCoverage"],
        "test_count": 4
    },
    "tests/test_models.py": {
        "classes_added": ["TestModelBranchCoverage"],
        "test_count": 4
    },
    "tests/test_schemas.py": {
        "classes_added": ["TestSchemaBranchCoverage"],
        "test_count": 7
    },
}

def verify_test_files():
    """Verify all test files exist and check they contain expected classes."""
    print("\n" + "="*80)
    print("BRANCH COVERAGE VERIFICATION CHECKLIST")
    print("="*80 + "\n")
    
    total_tests = 0
    files_verified = 0
    
    for filepath, info in TEST_FILES.items():
        abs_path = Path("c:\\Users\\hp\\Desktop\\AdpativHealth") / filepath
        
        exists = abs_path.exists()
        print(f"{'✓' if exists else '✗'} {filepath}")
        
        if exists:
            content = abs_path.read_text()
            found_classes = []
            found_tests = 0
            
            for class_name in info["classes_added"]:
                if f"class {class_name}" in content:
                    found_classes.append(class_name)
            
            # Count def test_ methods
            found_tests = content.count("def test_")
            
            print(f"    Classes found: {len(found_classes)}/{len(info['classes_added'])}")
            print(f"    Test methods: {found_tests}")
            
            if len(found_classes) == len(info["classes_added"]):
                print(f"    Status: ✓ COMPLETE")
                files_verified += 1
            else:
                print(f"    Status: ⚠ Partial")
                print(f"    Missing classes: {set(info['classes_added']) - set(found_classes)}")
            
            total_tests += found_tests
        else:
            print(f"    Status: ✗ FILE NOT FOUND")
        
        print()
    
    print("="*80)
    print(f"SUMMARY")
    print("="*80)
    print(f"Files verified: {files_verified}/{len(TEST_FILES)}")
    print(f"Total test methods added: {total_tests}")
    print(f"Expected: {sum(info['test_count'] for info in TEST_FILES.values())}")
    print()
    
    if files_verified == len(TEST_FILES):
        print("✓ ALL TEST FILES VERIFIED - Ready to run pytest!")
    else:
        print("⚠ Some files not verified - Check above for details")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
1. Run all tests to verify they execute without errors:
   
   pytest tests/ -v --tb=short

2. Run with coverage report:
   
   pytest tests/ --cov=app --cov-report=term-missing

3. Generate HTML coverage report:
   
   pytest tests/ --cov=app --cov-report=html

4. View coverage summary:
   
   pytest --cov=app --cov-report=term-missing --tb=no -q 2>/dev/null | tail -10

5. (Optional) Run specific test file:
   
   pytest tests/test_auth_extended.py -v
   pytest tests/test_main.py -v
   pytest tests/test_rbac_consent.py::TestConsentWorkflowBranches -v
    """)

if __name__ == "__main__":
    verify_test_files()
