import requests
import time

def test_login():
    try:
        url = "http://localhost:8000/auth/login"
        payload = {"username": "test", "password": "testpassword"}
        headers = {
            "Origin": "http://localhost:4200",
            "Content-Type": "application/json"
        }
        print(f"Sending POST to {url}")
        start = time.time()
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        end = time.time()
        
        print(f"Status: {resp.status_code}")
        print(f"Time: {end - start:.2f}s")
        print(f"Headers: {resp.headers}")
        print(f"Body: {resp.text}")
        
        if "Access-Control-Allow-Origin" in resp.headers:
            print("CORS Header Present!")
        else:
            print("CORS Header MISSING!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
