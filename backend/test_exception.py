import requests

def test_http_exception():
    url = "http://127.0.0.1:8000/auth/login"
    payload = {"username": "test_crash", "password": "testpassword"}
    headers = {
        "Origin": "http://localhost:4200",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    print(f"Body: {resp.text}")

if __name__ == "__main__":
    test_http_exception()
