import sys
import requests

def test_500_cors():
    print("Testing /auth/login with a forced 500 scenario...")
    # I'll just send a bad JSON syntax to see if 400/500 gets CORS.
    # Wait, 422 got CORS. What if I send a valid user but force a 500?
    # Let's hit a non-existent endpoint first to check 404 CORS.
    url = "http://localhost:8000/auth/login"
    headers = {
        "Origin": "http://localhost:4200",
        "Content-Type": "application/json"
    }
    
    # Let's see if the backend logs any errors when a real POST happens.
    # Actually, let's just make a GET request to see if the server is alive.
    try:
        resp = requests.get("http://localhost:8000/health", headers=headers)
        print(f"Health: {resp.status_code} - {resp.headers.get('access-control-allow-origin')}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_500_cors()
