#!/usr/bin/env python
"""
Test runner for Eden ORM

Runs all test suites and reports results.
"""

import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)


async def run_unit_tests():
    """Run unit tests."""
    print("\n" + "="*70)
    print("PHASE 1-2: CORE & RELATIONSHIPS UNIT TESTS")
    print("="*70 + "\n")
    
    try:
        from test_relationships import run_tests as run_relationship_tests
        relationship_success = await run_relationship_tests()
    except Exception as e:
        print(f"Failed to run relationship tests: {e}")
        relationship_success = False
    
    return relationship_success


async def run_comprehensive_tests():
    """Run comprehensive tests."""
    print("\n" + "="*70)
    print("PHASE 3-5: COMPREHENSIVE TESTS")
    print("="*70 + "\n")
    
    try:
        from test_comprehensive import run_all_tests
        comprehensive_success = await run_all_tests()
    except Exception as e:
        print(f"Failed to run comprehensive tests: {e}")
        comprehensive_success = False
    
    return comprehensive_success


async def main():
    """Run all test suites."""
    logger.info("Starting Eden ORM test suite")
    
    unit_success = await run_unit_tests()
    comprehensive_success = await run_comprehensive_tests()
    
    # Summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    print(f"Unit Tests (Phase 1-2):        {'✓ PASSED' if unit_success else '✗ FAILED'}")
    print(f"Comprehensive Tests (Phase 3-5): {'✓ PASSED' if comprehensive_success else '✗ FAILED'}")
    print("="*70 + "\n")
    
    success = unit_success and comprehensive_success
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
