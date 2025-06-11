"""
LuckyRobots Test Suite

This test suite covers the most critical functionality of the LuckyRobots
simulator interface:

1. Simulator Lifecycle - startup, connection, shutdown
2. Robot Control - reset and step operations
3. Observation Data - camera and sensor data processing

Usage:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --test lifecycle   # Run specific test category
    python run_all_tests.py --verbose          # Verbose output

Or use pytest directly:
    pytest test_simulator_lifecycle.py -v
    pytest test_robot_control.py -v
    pytest test_observation_data.py -v
"""

__version__ = "1.0.0"
