import requests

base_url = "http://localhost:8000"

# 1. Login
login_data = {
    "username": "Dev",
    "password": "abcd1234*"
}

try:
    # Intentamos /auth/login (según main.py y auth.py)
    login_resp = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if login_resp.status_code == 200:
        token = login_resp.json().get("access_token")
        print(f"Token obtained: {token[:10]}...")
        
        # 2. Call endpoint
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{base_url}/api/visits/with-balances", headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    else:
        print(f"Login failed: {login_resp.status_code} - {login_resp.text}")
except Exception as e:
    print(f"Error: {e}")
