"""
CDE Implementation Verification Test
"""

import sys
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("CDE Implementation Verification Test")
print("=" * 70)
print()

# Test 1: Import CDEEvent model
print("Test 1: Import CDEEvent model...")
try:
    from models.cde_event import CDEEvent
    print("[OK] CDEEvent model imported")

    # Check key fields
    required_fields = [
        'id', 'acceptance_no', 'event_type', 'drug_name', 'applicant',
        'public_page_url', 'source_urls', 'is_active',
        'first_seen_at', 'last_seen_at'
    ]

    for field in required_fields:
        if not hasattr(CDEEvent, field):
            print(f"[FAIL] Missing field: {field}")
            sys.exit(1)

    print("[OK] All required fields exist")
    print()

except Exception as e:
    print(f"[FAIL] CDEEvent model import failed: {e}")
    sys.exit(1)

# Test 2: Import CDESpider
print("Test 2: Import CDESpider...")
try:
    from crawlers.cde_spider import CDESpider, CDEEventData
    print("[OK] CDESpider and CDEEventData imported")

    # Check key methods
    required_methods = ['run', 'fetch_event_list', 'fetch_event_detail', 'save_to_database']

    for method in required_methods:
        if not hasattr(CDESpider, method):
            print(f"[FAIL] Missing method: {method}")
            sys.exit(1)

    print("[OK] All required methods exist")
    print()

except Exception as e:
    print(f"[FAIL] CDESpider import failed: {e}")
    sys.exit(1)

# Test 3: Import unified search service
print("Test 3: Import unified search service...")
try:
    from services.unified_search_service import UnifiedSearchService
    print("[OK] UnifiedSearchService imported")

    # Check CDE search methods
    if not hasattr(UnifiedSearchService, 'search_cde_events'):
        print("[FAIL] Missing method: search_cde_events")
        sys.exit(1)

    if not hasattr(UnifiedSearchService, '_calculate_cde_event_relevance'):
        print("[FAIL] Missing method: _calculate_cde_event_relevance")
        sys.exit(1)

    print("[OK] CDE search methods exist")
    print()

except Exception as e:
    print(f"[FAIL] UnifiedSearchService import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Import API routes
print("Test 4: Import API routes...")
try:
    from api.cde import router as cde_router
    from api.search import router as search_router
    print("[OK] CDE and Search routers imported")

    # Check router tags
    if cde_router.tags != ["CDE"]:
        print(f"[FAIL] CDE router tags incorrect: {cde_router.tags}")
        sys.exit(1)

    print("[OK] Router configuration correct")
    print()

except Exception as e:
    print(f"[FAIL] API router import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check configuration
print("Test 5: Check configuration...")
try:
    from config import settings

    required_configs = [
        'CDE_CRAWLER_ENABLED',
        'CDE_CRAWLER_BASE_URL',
        'CDE_CRAWLER_INFO_URL',
        'CDE_CRAWLER_INTERVAL_HOURS',
        'CDE_CRAWLER_RATE_LIMIT'
    ]

    for config in required_configs:
        if not hasattr(settings, config):
            print(f"[FAIL] Missing config: {config}")
            sys.exit(1)

    print("[OK] All CDE configs exist")
    print()

except Exception as e:
    print(f"[FAIL] Configuration check failed: {e}")
    sys.exit(1)

# Test 6: Verify data class
print("Test 6: Verify CDEEventData dataclass...")
try:
    from crawlers.cde_spider import CDEEventData

    # Create test instance
    test_event = CDEEventData(
        acceptance_no="TEST001",
        event_type="IND",
        drug_name="Test Drug",
        applicant="Test Company",
        public_page_url="https://example.com/test",
        source_urls=["https://example.com/list", "https://example.com/test"]
    )

    print("[OK] CDEEventData instance created")
    print(f"  - Acceptance No: {test_event.acceptance_no}")
    print(f"  - Event Type: {test_event.event_type}")
    print(f"  - Drug Name: {test_event.drug_name}")
    print(f"  - Applicant: {test_event.applicant}")
    print(f"  - Source URLs: {len(test_event.source_urls)} items")
    print()

except Exception as e:
    print(f"[FAIL] CDEEventData verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Verify factory function
print("Test 7: Verify factory function...")
try:
    from models import create_cde_event

    test_event = create_cde_event(
        acceptance_no="TEST002",
        event_type="NDA",
        drug_name="Test Drug 2",
        applicant="Test Company 2",
        public_page_url="https://example.com/test2"
    )

    print("[OK] create_cde_event factory function works")
    print(f"  - Created event: {test_event.drug_name} - {test_event.event_type}")
    print()

except Exception as e:
    print(f"[FAIL] Factory function verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# =====================================================
# Test Summary
# =====================================================

print("=" * 70)
print("[OK] ALL TESTS PASSED!")
print("=" * 70)
print()
print("Verification Results:")
print("  [OK] CDEEvent data model defined correctly")
print("  [OK] CDESpider crawler class defined correctly")
print("  [OK] UnifiedSearchService supports CDE search")
print("  [OK] API routes configured correctly")
print("  [OK] Configuration items complete")
print("  [OK] Data classes available")
print("  [OK] Factory functions available")
print()
print("Next Steps:")
print("  1. Run database initialization: python scripts/init_db.py")
print("  2. Start API service: python main.py")
print("  3. Visit API documentation: http://localhost:8000/docs")
print("  4. Test CDE spider (requires manual exploration of CDE website)")
print("=" * 70)
