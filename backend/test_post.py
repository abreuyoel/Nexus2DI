import requests

def test_db_crash():
    url = "http://127.0.0.1:8000/auth/login"
    payload = {"username": "test", "password": "testpassword"}
    headers = {
        "Origin": "http://localhost:4200",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_db_crash()
