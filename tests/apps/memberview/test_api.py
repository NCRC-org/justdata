"""Test the search API endpoints."""
import requests
import json

BASE_URL = "http://127.0.0.1:8082"

print("=" * 60)
print("Testing MemberView Search API")
print("=" * 60)

# Test states endpoint
print("\n1. Testing /search/api/states")
try:
    r = requests.get(f"{BASE_URL}/search/api/states")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        states = r.json()
        print(f"   States returned: {len(states)}")
        print(f"   First 5 states: {states[:5]}")
    else:
        print(f"   Error: {r.text}")
except Exception as e:
    print(f"   Exception: {e}")

# Test members endpoint with California
print("\n2. Testing /search/api/members?state=California")
try:
    r = requests.get(f"{BASE_URL}/search/api/members", params={"state": "California"})
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        total = data.get("total", 0)
        members = data.get("members", [])
        print(f"   Total members: {total}")
        print(f"   Members in response: {len(members)}")
        if members:
            print(f"   First member:")
            print(f"     - ID: {members[0].get('id')}")
            print(f"     - Name: {members[0].get('name')}")
            print(f"     - Status: {members[0].get('status')}")
            print(f"     - City: {members[0].get('city')}")
            print(f"     - State: {members[0].get('state')}")
    else:
        print(f"   Error: {r.text[:500]}")
except Exception as e:
    print(f"   Exception: {e}")

# Test members endpoint with California and metro
print("\n3. Testing /search/api/members?state=California&metro=41500")
try:
    r = requests.get(f"{BASE_URL}/search/api/members", params={"state": "California", "metro": "41500"})
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        total = data.get("total", 0)
        members = data.get("members", [])
        print(f"   Total members: {total}")
        print(f"   Members in response: {len(members)}")
    else:
        print(f"   Error: {r.text[:500]}")
except Exception as e:
    print(f"   Exception: {e}")

print("\n" + "=" * 60)




