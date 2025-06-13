"""
Integration test runner for LuckyRobots with real simulator testing.

This script runs comprehensive integration tests against the actual LuckyWorld simulator.
Tests are organized into separate modules for better maintainability.

Test modules:
- test_simulator_lifecycle.py: Simulator startup, connection, shutdown
- test_remote_control.py: Remote control of the robot
- test_observation_data.py: Camera and sensor data processing
- test_utilities.py: Helper functions and configuration validation
- test_stress_cases.py: Stress tests and edge cases
- test_debug_helpers.py: Debug and development helpers

Usage:
    python run_tests.py                     # Run all tests
    python run_tests.py --test lifecycle    # Run specific category
    python run_tests.py --verbose           # Verbose output
    python run_tests.py --quick             # Skip slow tests
    python run_tests.py --check-env         # Check environment only
"""

import sys
import logging
logging.disable(logging.CRITICAL)

import subprocess
import argparse
import time
from pathlib import Path

from luckyrobots.utils.sim_manager import find_luckyworld_executable, is_luckyworld_running, stop_luckyworld
from luckyrobots.utils.helpers import get_robot_config


def check_dependencies():
    """Check if required test dependencies are installed."""
    required_packages = ["pytest", "pytest-asyncio", "pytest-timeout"]
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


def check_environment():
    """Check the test environment and simulator availability."""
    print("Environment Check")
    print("=" * 50)
    
    # Check LuckyRobots installation
    try:
        import luckyrobots
        version = getattr(luckyrobots, '__version__', 'unknown')
        print(f"✓ LuckyRobots installed (version: {version})")
    except ImportError:
        print("✗ LuckyRobots not installed or not in path")
        return False
    
    # Check for simulator executable
    executable = find_luckyworld_executable()
    if executable:
        print(f"✓ LuckyWorld executable found: {executable}")
    else:
        print("✗ LuckyWorld executable not found")
        print("  Set LUCKYWORLD_PATH or LUCKYWORLD_HOME environment variable")
        return False
    
    # Check if simulator is already running
    if is_luckyworld_running():
        print("⚠ LuckyWorld is currently running - will be stopped for tests")
    else:
        print("✓ No LuckyWorld instance currently running")
    
    # Check robot configuration
    try:
        config = get_robot_config("so100")
        print("✓ Robot configuration loaded successfully")
    except Exception as e:
        print(f"✗ Error loading robot configuration: {e}")
        return False
    
    print("\n✓ Environment check passed")
    return True


def run_pytest(test_pattern, test_dir, verbose=False, capture=True, markers=None, timeout=None):
    """Run pytest with specific parameters and return detailed results."""
    cmd = ["python", "-m", "pytest"]
    
    # Add pytest options
    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-q")
    
    if not capture:
        cmd.append("-s")
    
    # Add async support
    cmd.append("--asyncio-mode=auto")
    
    # Add timeout
    if timeout:
        cmd.extend(["--timeout", str(timeout)])
    
    # Add markers (e.g., to skip slow tests)
    if markers:
        cmd.extend(["-m", markers])
    
    # Add test pattern
    if test_pattern:
        test_path = test_dir / test_pattern
        cmd.append(str(test_path))
    else:
        cmd.append(str(test_dir))
    
    try:
        start_time = time.time()
        
        result = subprocess.run(
            cmd, check=True, capture_output=capture, text=True, cwd=test_dir
        )
        end_time = time.time()
        
        # Parse the output to count passed/failed tests
        output = result.stdout if capture else ""
        passed_count, failed_count, skipped_count = parse_pytest_output(output)
        
        return True, output, end_time - start_time, passed_count, failed_count, skipped_count
        
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        error_output = e.stdout if capture and e.stdout else e.stderr if capture else ""
        
        # Try to parse failed output too
        passed_count, failed_count, skipped_count = parse_pytest_output(error_output)
        
        return False, error_output, end_time - start_time, passed_count, failed_count, skipped_count


def parse_pytest_output(output):
    """Parse pytest output to extract test counts."""
    import re
    
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    
    if not output:
        return passed_count, failed_count, skipped_count
    
    # Look for summary line like "5 passed, 2 failed, 1 skipped in 10.5s"
    summary_pattern = r'(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped|(\d+)\s+error'
    
    # Split into lines and look for the summary
    lines = output.split('\n')
    
    for line in lines:
        # Look for lines with test results
        if 'passed' in line or 'failed' in line or 'skipped' in line:
            # Extract numbers before keywords
            passed_match = re.search(r'(\d+)\s+passed', line)
            failed_match = re.search(r'(\d+)\s+failed', line)
            skipped_match = re.search(r'(\d+)\s+skipped', line)
            error_match = re.search(r'(\d+)\s+error', line)
            
            if passed_match:
                passed_count = int(passed_match.group(1))
            if failed_match:
                failed_count = int(failed_match.group(1))
            if skipped_match:
                skipped_count = int(skipped_match.group(1))
            if error_match:
                failed_count += int(error_match.group(1))  # Count errors as failures
    
    # Alternative parsing for verbose output
    if passed_count == 0 and failed_count == 0:
        # Count PASSED and FAILED lines in verbose output
        passed_count = len(re.findall(r'PASSED', output))
        failed_count = len(re.findall(r'FAILED', output))
        skipped_count = len(re.findall(r'SKIPPED', output))
    
    return passed_count, failed_count, skipped_count


def cleanup_environment():
    """Clean up the test environment."""
    print("Cleaning up test environment...")
    
    # Stop any running simulator
    if is_luckyworld_running():
        print("Stopping LuckyWorld simulator...")
        try:
            stop_luckyworld()
            time.sleep(3)
            if is_luckyworld_running():
                print("Warning: LuckyWorld may still be running")
            else:
                print("✓ LuckyWorld stopped successfully")
        except Exception as e:
            print(f"Error stopping LuckyWorld: {e}")


def print_test_info():
    """Print information about available test categories."""
    print("Test Categories:")
    print("   lifecycle    - Simulator startup, connection, shutdown")
    print("   remote       - Remote control of the robot") 
    print("   observation  - Camera and sensor data processing")
    print("   utilities    - Helper functions and configuration")
    print("   stress       - Stress tests and edge cases")
    print("   debug        - Debug and development helpers")
    print()
    print("Test Files:")
    print("   test_simulator_lifecycle.py - Simulator lifecycle management")
    print("   test_remote_control.py      - Remote control of the robot")
    print("   test_observation_data.py    - Observation data processing")
    print("   test_utilities.py           - Utility functions")
    print("   test_stress_cases.py        - Stress testing")
    print("   test_debug_helpers.py       - Debug helpers")
    print()
    print("Test Markers:")
    print("   slow         - Tests that take longer to run")
    print("   integration  - Integration tests")
    print("   simulator    - Tests requiring the simulator")
    print()


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run LuckyRobots integration tests against real simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --test lifecycle   # Run lifecycle tests only
  python run_tests.py -v                 # Verbose output
  python run_tests.py --quick            # Skip slow tests
  python run_tests.py --check-env        # Check environment only
        """,
    )

    parser.add_argument(
        "--test",
        choices=["all", "lifecycle", "control", "observation", "utilities", "stress", "debug"],
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
        help="Don't capture output (useful for debugging)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout per test in seconds (default: 120)"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment and exit"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show information about test categories and exit",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up environment and exit"
    )

    args = parser.parse_args()

    if args.info:
        print_test_info()
        return

    if args.cleanup:
        cleanup_environment()
        return

    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)

    # Check environment
    if not check_environment():
        if args.check_env:
            sys.exit(1)
        print("\nEnvironment check failed. Use --check-env for details.")
        sys.exit(1)

    if args.check_env:
        print("\nEnvironment check passed! Ready to run tests.")
        return

    # Get the test directory
    test_dir = Path(__file__).parent

    # Define test files mapping to actual files
    test_files = {
        "lifecycle": "test_simulator_lifecycle.py",
        "remote": "test_remote_control.py", 
        "observation": "test_observation_data.py",
        "utilities": "test_utilities.py",
        "stress": "test_stress_cases.py",
        "debug": "test_debug_helpers.py",
    }

    print("LuckyRobots Integration Test Suite (Real Simulator)")
    print("=" * 60)

    # Clean up any existing simulator instance
    cleanup_environment()

    # Determine which tests to run
    if args.test == "all":
        tests_to_run = list(test_files.items())
        print("Running all integration tests...")
    else:
        tests_to_run = [(args.test, test_files[args.test])]

    if args.verbose:
        print_test_info()

    print()

    # Configure test markers
    markers = None
    if args.quick:
        markers = "not slow"
        print("Skipping slow tests (--quick mode)")

    results = {}
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_time = 0

    for test_name, test_file in tests_to_run:
        print(f"Running {test_name} tests ({test_file})...", end="", flush=True)

        # Check if test file exists
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f" SKIPPED (file not found)")
            results[test_name] = (True, 0, 0, 0, 1)  # success, duration, passed, failed, skipped
            total_skipped += 1
            continue

        success, output, duration, passed_count, failed_count, skipped_count = run_pytest(
            test_file,
            test_dir,
            verbose=args.verbose,
            capture=not args.no_capture,
            markers=markers,
            timeout=args.timeout
        )

        total_time += duration
        total_passed += passed_count
        total_failed += failed_count
        total_skipped += skipped_count

        if success:
            status_detail = f"PASSED ({passed_count}✓"
            if failed_count > 0:
                status_detail += f", {failed_count}✗"
            if skipped_count > 0:
                status_detail += f", {skipped_count}⊝"
            status_detail += f", {duration:.1f}s)"
            print(f" {status_detail}")
        else:
            status_detail = f"FAILED ({passed_count}✓, {failed_count}✗"
            if skipped_count > 0:
                status_detail += f", {skipped_count}⊝"
            status_detail += f", {duration:.1f}s)"
            print(f" {status_detail}")
            
            if output and (args.verbose or not args.no_capture):
                print(f"Error output:\n{output}")

        results[test_name] = (success, duration, passed_count, failed_count, skipped_count)

        # Brief pause between test categories
        time.sleep(1)

    print()

    print("Test Results Summary")
    print("=" * 60)
    print(f"{'Suite':<12} {'Status':<8} {'Passed':<6} {'Failed':<6} {'Skipped':<7} {'Time':<8}")
    print("-" * 60)

    for test_name, (success, duration, passed_count, failed_count, skipped_count) in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_name:<12} {status:<8} {passed_count:<6} {failed_count:<6} {skipped_count:<7} {duration:.1f}s")

    print("-" * 60)
    print(f"{'TOTALS':<12} {'':<8} {total_passed:<6} {total_failed:<6} {total_skipped:<7} {total_time:.1f}s")
    print()

    # Summary message
    total_suites = len(results)
    passed_suites = sum(1 for success, _, _, _, _ in results.values() if success)
    failed_suites = total_suites - passed_suites

    print(f"Suite Summary: {passed_suites}/{total_suites} test suites passed")
    print(f"Test Summary: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")

    # Final cleanup
    cleanup_environment()

    if total_failed > 0:
        print(f"\n⚠ {total_failed} test(s) failed across {len([r for r in results.values() if not r[0]])} suite(s).")
        print("Tips:")
        print("  - Ensure LuckyWorld executable is accessible")
        print("  - Try running with --verbose for more details")
        print("  - Check system resources (CPU, memory)")
        print("  - Run individual test files to isolate issues")
        sys.exit(1)
    else:
        print(f"\n✓ All {total_passed} tests passed across {len(results)} test suites!")
        print("Integration test suite completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        cleanup_environment()
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        cleanup_environment()
        sys.exit(1)