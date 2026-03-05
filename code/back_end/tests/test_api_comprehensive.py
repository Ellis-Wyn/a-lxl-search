"""
API 接口综合测试脚本
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_endpoint(name: str, method: str, path: str, **kwargs) -> Dict[str, Any]:
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=kwargs.get("params"), timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=kwargs.get("json"), timeout=10)
        else:
            return {"status": "skip", "reason": f"Unsupported method: {method}"}

        if response.status_code == 200:
            return {
                "status": "pass",
                "response": response.json(),
                "count": len(response.json()) if isinstance(response.json(), list) else 1
            }
        else:
            return {
                "status": "fail",
                "status_code": response.status_code,
                "error": response.text
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    print("=" * 60)
    print("API 接口综合测试")
    print("=" * 60)
    print()

    # 测试用例
    tests = [
        # Targets API
        ("Targets - 列表", "GET", "/api/v1/targets", {"params": {"limit": 3}}),
        ("Targets - 统计", "GET", "/api/v1/targets/stats", {}),
        ("Targets - 详情", "GET", "/api/v1/targets/c1ab2cc6-060f-4eba-8bf7-fc96c071a2b8", {}),

        # Publications API
        ("Publications - 列表", "GET", "/api/v1/publications", {"params": {"limit": 3}}),
        ("Publications - 统计", "GET", "/api/v1/publications/stats", {}),
        ("Publications - 详情", "GET", "/api/v1/publications/41544643", {}),

        # Pipeline API
        ("Pipeline - 列表", "GET", "/api/pipeline", {"params": {"limit": 3}}),
        ("Pipeline - 统计", "GET", "/api/pipeline/statistics", {}),

        # Health Check
        ("Health Check", "GET", "/health", {}),
    ]

    results = []
    passed = 0
    failed = 0

    for name, method, path, kwargs in tests:
        print(f"Testing: {name}... ", end="", flush=True)
        result = test_endpoint(name, method, path, **kwargs)
        results.append((name, result))

        if result["status"] == "pass":
            print(f"✅ PASS ({result['count']} items)")
            passed += 1
        elif result["status"] == "fail":
            print(f"❌ FAIL (HTTP {result.get('status_code')})")
            failed += 1
        else:
            print(f"⚠️  {result['status'].upper()}: {result.get('reason', result.get('error'))}")

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败, {len(tests) - passed - failed} 跳过/错误")
    print("=" * 60)

    # 详细错误信息
    if failed > 0:
        print()
        print("失败详情:")
        for name, result in results:
            if result["status"] == "fail":
                print(f"  ❌ {name}: HTTP {result.get('status_code')}")

if __name__ == "__main__":
    main()
