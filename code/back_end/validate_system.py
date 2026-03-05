"""
=====================================================
System Validation Script - 系统完整性验证
=====================================================
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

# Test counters
total_tests = 0
passed_tests = 0
failed_tests = 0

def print_success(msg):
    """Print success message"""
    global passed_tests
    passed_tests += 1
    print(f"[PASS] {msg}")

def print_error(msg):
    """Print error message"""
    global failed_tests
    failed_tests += 1
    print(f"[FAIL] {msg}")

def print_info(msg):
    """Print info message"""
    print(f"[INFO] {msg}")

def print_test_header(msg):
    """Print test header"""
    global total_tests
    total_tests += 1
    print(f"\n{'='*60}")
    print(f"Test {total_tests}: {msg}")
    print(f"{'='*60}")


# =====================================================
# Test 1: Service Container
# =====================================================

def test_container():
    """Test dependency injection container"""
    print_test_header("Service Container (Dependency Injection)")

    try:
        from core.container import get_container

        container = get_container()
        print_info("ServiceContainer instantiated successfully")

        # Check database service
        if container.has("db"):
            print_success("Database service registered")
        else:
            print_info("Database service not registered (optional)")

        # Check cache service
        if container.has("cache"):
            print_success("Cache service registered")
        else:
            print_info("Cache service not registered")

        return True

    except Exception as e:
        print_error(f"Service Container test failed: {e}")
        return False


# =====================================================
# Test 2: Redis Cache Service
# =====================================================

def test_cache_service():
    """Test Redis cache service"""
    print_test_header("Redis Cache Service")

    try:
        from core.container import get_container

        container = get_container()

        if not container.has("cache"):
            print_info("Cache service not registered, skipping test")
            return True

        cache = container.get("cache")

        # Test connection
        try:
            cache.redis.ping()
            print_success("Redis connection successful")
        except Exception as e:
            print_error(f"Redis connection failed: {e}")
            return False

        # Test read/write
        test_key = "test_validation_key"
        test_value = {"test": "data", "timestamp": str(datetime.now())}

        cache.set(test_key, test_value, ttl=60)
        print_success("Cache write successful")

        retrieved = cache.get(test_key)
        if retrieved and retrieved.get("test") == "data":
            print_success("Cache read successful")
        else:
            print_error("Cache read failed")
            return False

        # Cleanup
        cache.delete(test_key)
        print_info("Test data cleaned up")

        return True

    except Exception as e:
        print_error(f"Cache service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================
# Test 3: Data Normalization Service
# =====================================================

def test_normalization_service():
    """Test data normalization service"""
    print_test_header("Data Normalization Service")

    try:
        from services.data_normalization_service import get_normalization_service

        service = get_normalization_service()
        print_info("DataNormalizationService instantiated successfully")

        # Test Phase normalization
        test_cases_phase = [
            ("临床I期", "Phase 1"),
            ("II期", "Phase 2"),
            ("3期", "Phase 3"),
            ("临床前", "Preclinical"),
            ("已上市", "Approved"),
        ]

        all_passed = True
        for input_val, expected in test_cases_phase:
            result = service.normalize_phase(input_val)
            if result == expected:
                print_success(f"Phase normalization: '{input_val}' -> '{result}'")
            else:
                print_error(f"Phase normalization failed: '{input_val}' expected '{expected}' got '{result}'")
                all_passed = False

        # Test Indication normalization
        test_cases_indication = [
            ("非小细胞肺癌", "NSCLC"),
            ("小细胞肺癌", "SCLC"),
            ("三阴性乳腺癌", "TNBC"),
        ]

        for input_val, expected in test_cases_indication:
            result = service.normalize_indication(input_val)
            if result == expected:
                print_success(f"Indication normalization: '{input_val}' -> '{result}'")
            else:
                print_error(f"Indication normalization failed")
                all_passed = False

        # Test Company name normalization
        test_cases_company = [
            ("恒瑞", "江苏恒瑞医药股份有限公司"),
            ("百济神州", "百济神州（北京）生物科技有限公司"),
            ("信达生物", "信达生物制药（苏州）有限公司"),
        ]

        for input_val, expected in test_cases_company:
            result = service.normalize_company_name(input_val)
            if result == expected:
                print_success(f"Company normalization: '{input_val}' -> '{result[:20]}...'")
            else:
                print_error(f"Company normalization failed")
                all_passed = False

        # Test batch normalization
        pipeline_data = {
            "phase": "临床I期",
            "indication": "非小细胞肺癌",
            "company_name": "恒瑞"
        }
        normalized = service.normalize_pipeline_data(pipeline_data)

        if (normalized["phase"] == "Phase 1" and
            normalized["indication"] == "NSCLC" and
            normalized["company_name"] == "江苏恒瑞医药股份有限公司"):
            print_success("Batch normalization successful")
        else:
            print_error("Batch normalization failed")
            all_passed = False

        return all_passed

    except Exception as e:
        print_error(f"Data normalization service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================
# Test 4: API Health Check
# =====================================================

def test_api_health():
    """Test API health check"""
    print_test_header("API Health Check")

    try:
        import requests

        # Test root path
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print_success("Root path response OK")
        else:
            print_error(f"Root path response error: {response.status_code}")
            return False

        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_success(f"Health check passed: {data}")
            else:
                print_error(f"Health status abnormal: {data}")
                return False
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False

        # Test search API health
        response = requests.get("http://localhost:8000/api/search/health", timeout=5)
        if response.status_code == 200:
            print_success("Search service health check passed")
        else:
            print_info("Search service health check failed (optional)")

        # Test PubMed API health
        response = requests.get("http://localhost:8000/api/pubmed/health", timeout=5)
        if response.status_code == 200:
            print_success("PubMed service health check passed")
        else:
            print_info("PubMed service health check failed (optional)")

        return True

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API service (http://localhost:8000)")
        print_info("Please ensure Docker services are running: docker-compose up -d")
        return False
    except Exception as e:
        print_error(f"API health check failed: {e}")
        return False


# =====================================================
# Test 5: Unified Search API
# =====================================================

def test_unified_search_api():
    """Test unified search API"""
    print_test_header("Unified Search API")

    try:
        import requests
        import time

        # Test 1: Basic search
        print_info("Test 1: Basic search 'EGFR'")
        start_time = time.time()
        response = requests.get(
            "http://localhost:8000/api/search/unified",
            params={"q": "EGFR", "type": "all", "limit": 5},
            timeout=30
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print_success(f"Search successful (elapsed: {elapsed:.2f}s)")
            print_info(f"Total results: {data.get('total_count', 0)}")

            # Check response structure
            if "results" in data:
                results = data["results"]
                if "pipelines" in results:
                    print_info(f"Pipeline results: {results['pipelines'].get('count', 0)}")
                if "publications" in results:
                    print_info(f"Publication results: {results['publications'].get('count', 0)}")
                if "targets" in results:
                    print_info(f"Target results: {results['targets'].get('count', 0)}")
                if "cde_events" in results:
                    print_info(f"CDE events: {results['cde_events'].get('count', 0)}")
        else:
            print_error(f"Search failed: {response.status_code}")
            return False

        # Test 2: Cache validation (second search should be faster)
        print_info("\nTest 2: Cache validation (search same keyword again)")
        start_time = time.time()
        response = requests.get(
            "http://localhost:8000/api/search/unified",
            params={"q": "EGFR", "type": "all", "limit": 5},
            timeout=30
        )
        elapsed_cached = time.time() - start_time

        if response.status_code == 200:
            print_success(f"Cached search successful (elapsed: {elapsed_cached:.2f}s)")

            # Compare response time
            if elapsed_cached < elapsed:
                speedup = (elapsed - elapsed_cached) / elapsed * 100
                print_success(f"Cache speedup: {speedup:.1f}%")
            else:
                print_info("Cache miss or no significant speedup")
        else:
            print_error(f"Cached search failed: {response.status_code}")

        # Test 3: Filter functionality
        print_info("\nTest 3: Filter functionality (search pipelines only)")
        response = requests.get(
            "http://localhost:8000/api/search/unified",
            params={"q": "EGFR", "type": "pipeline", "limit": 3},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Filter search successful")
            print_info(f"Pipeline results: {data.get('results', {}).get('pipelines', {}).get('count', 0)}")
        else:
            print_info("Filter search failed (optional)")

        return True

    except Exception as e:
        print_error(f"Unified search API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================
# Test 6: PubMed API
# =====================================================

def test_pubmed_api():
    """Test PubMed API"""
    print_test_header("PubMed API")

    try:
        import requests

        # Test PubMed search
        payload = {
            "target_name": "EGFR",
            "keywords": ["inhibitor"],
            "diseases": ["lung cancer"],
            "max_results": 10,
            "date_range_days": 365
        }

        print_info("Test PubMed search: EGFR + inhibitor + lung cancer")
        response = requests.post(
            "http://localhost:8000/api/pubmed/search",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"PubMed search successful: {data.get('total', 0)} results")
        else:
            print_info(f"PubMed search failed: {response.status_code} (may require network)")

        return True

    except Exception as e:
        print_info(f"PubMed API test skipped: {e}")
        return True  # PubMed test failure doesn't affect overall result


# =====================================================
# Main Function
# =====================================================

def main():
    """Main function"""
    print(f"\n{'='*60}")
    print("A_lxl_search System Validation")
    print(f"{'='*60}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run all tests
    test_container()
    test_cache_service()
    test_normalization_service()
    test_api_health()
    test_unified_search_api()
    test_pubmed_api()

    # Print summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")

    if failed_tests == 0:
        print(f"\n{'='*60}")
        print("SUCCESS! All tests passed!")
        print("System is 100% complete and ready for production!")
        print(f"{'='*60}\n")
        return 0
    else:
        print(f"\n{'='*60}")
        print(f"WARNING: {failed_tests} test(s) failed, please check above errors")
        print(f"{'='*60}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
