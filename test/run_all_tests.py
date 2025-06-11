"""
High-level test runner for LuckyRobots test suite.

This script runs all the critical tests for LuckyRobots simulator interactions.
It provides a simple interface to run all tests or specific test categories.

Usage:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --test luckyworld  # Run specific category
    python run_all_tests.py --verbose          # Verbose output
    python run_all_tests.py --no-capture       # Don't capture print statements
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path


def check_dependencies():
    """Check if required test dependencies are installed."""
    required_packages = ["pytest", "pytest-asyncio"]
    missing = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        print("Missing required test dependencies:")
        for package in missing:
            print(f"   - {package}")
        print("\nInstall with: pip install " + " ".join(missing))
        return False

    return True


def run_pytest(test_file, test_dir, verbose=False, capture=True):
    """Run pytest on a specific test file."""
    cmd = ["python", "-m", "pytest"]

    # Add pytest options
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    if not capture:
        cmd.append("-s")

    # Add async support
    cmd.append("--asyncio-mode=auto")

    test_file_path = test_dir / test_file
    cmd.append(str(test_file_path))

    try:
        start_time = time.time()

        result = subprocess.run(
            cmd, check=True, capture_output=capture, text=True, cwd=test_dir
        )
        end_time = time.time()

        return True, result.stdout if capture else "", end_time - start_time
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        error_output = e.stdout if capture and e.stdout else e.stderr if capture else ""
        return False, error_output, end_time - start_time


def print_test_info():
    """Print information about the test suite."""
    print("Test Categories:")
    print("   luckyworld  - LuckyWorld startup, connection, shutdown")
    print("   realtime    - Realtime reset and step requests")
    print("   observation - Camera and sensor data processing")
    print()


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run LuckyRobots test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_tests.py                    # Run all tests
  python run_all_tests.py --test luckyworld  # Run luckyworld tests only
  python run_all_tests.py -v                 # Verbose output
  python run_all_tests.py -s                 # Don't capture print statements
        """,
    )

    parser.add_argument(
        "--test",
        choices=["all", "luckyworld", "realtime", "observation"],
        default="all",
        help="Which tests to run (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed test output"
    )
    parser.add_argument(
        "--no-capture",
        "-s",
        action="store_true",
        help="Don't capture output (useful for debugging tests)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show information about test categories and exit",
    )

    args = parser.parse_args()

    if args.info:
        print_test_info()
        return

    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)

    # Get the test directory
    test_dir = Path(__file__).parent

    # Check if conftest.py exists
    conftest_path = test_dir / "conftest.py"
    if not conftest_path.exists():
        print("conftest.py not found in tests directory!")
        sys.exit(1)

    # Define test files (just filenames)
    test_files = {
        "luckyworld": "test_luckyworld_lifecycle.py",
        "realtime": "test_realtime_control.py",
        "observation": "test_observation_data.py",
    }

    print("LuckyRobots Test Suite")
    print("=" * 50)

    if args.test == "all":
        tests_to_run = test_files.items()
        print("Running all tests...")
    else:
        tests_to_run = [(args.test, test_files[args.test])]

    if args.verbose:
        print_test_info()

    print()

    results = {}
    total_passed = 0
    total_failed = 0
    total_time = 0

    for test_name, test_file in tests_to_run:
        print(f"Running {test_name} tests...", end="", flush=True)

        test_file_path = test_dir / test_file
        if not test_file_path.exists():
            print(f"\nTest file not found: {test_file_path}")
            results[test_name] = (False, 0)
            total_failed += 1
            continue

        success, output, duration = run_pytest(
            test_file, test_dir, verbose=args.verbose, capture=not args.no_capture
        )

        total_time += duration

        if success:
            print(f"PASSED ({duration:.1f}s)")
            total_passed += 1
        else:
            print(f"FAILED ({duration:.1f}s)")
            if output and (args.verbose or not args.no_capture):
                print(f"Error output:\n{output}")
            total_failed += 1

        results[test_name] = (success, duration)

    print()

    print("Test Results Summary")
    print("=" * 30)

    for test_name, (passed, duration) in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name:12} {status:10} ({duration:.1f}s)")

    print(f"\nTime: {total_time:.1f}s total")
    print(f"Results: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("Please check the output above for details.\n")
        sys.exit(1)
    else:
        print("\nAll tests passed!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
