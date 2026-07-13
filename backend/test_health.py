import requests
import time

def test_health():
    try:
        start = time.time()
        print("Sending GET to http://localhost:8000/health")
        resp = requests.get("http://localhost:8000/health", timeout=5)
        end = time.time()
        print(f"Status: {resp.status_code}")
        print(f"Time: {end - start:.2f}s")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_health()
