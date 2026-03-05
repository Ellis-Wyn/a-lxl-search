import requests
import json

# 测试搜索API
base_url = "http://localhost:8000"

print("=" * 60)
print("测试管线搜索功能")
print("=" * 60)

# 测试1: 搜索"肺癌"
print("\n1. 搜索 '肺癌':")
response = requests.get(f"{base_url}/api/pipeline/search", params={"keyword": "肺癌", "limit": 10})
print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   结果数量: {len(data)}")
    if data:
        print(f"   第一条: {data[0]['drug_code']} - {data[0]['company_name']} - {data[0]['indication']}")
else:
    print(f"   错误: {response.text}")

# 测试2: 搜索"百济"
print("\n2. 搜索 '百济':")
response = requests.get(f"{base_url}/api/pipeline/search", params={"keyword": "百济", "limit": 10})
print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   结果数量: {len(data)}")
    if data:
        print(f"   第一条: {data[0]['drug_code']} - {data[0]['company_name']}")

# 测试3: 搜索"BGB"
print("\n3. 搜索 'BGB' (英文):")
response = requests.get(f"{base_url}/api/pipeline/search", params={"keyword": "BGB", "limit": 10})
print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   结果数量: {len(data)}")
    if data:
        print(f"   第一条: {data[0]['drug_code']} - {data[0]['company_name']}")

# 测试4: 列出所有管线（前5条）
print("\n4. 列出所有管线 (limit=5):")
response = requests.get(f"{base_url}/api/pipeline", params={"limit": 5})
print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   结果数量: {len(data)}")
    for i, p in enumerate(data, 1):
        print(f"   {i}. {p['drug_code']} | {p['company_name']} | {p['indication']}")

print("\n" + "=" * 60)
