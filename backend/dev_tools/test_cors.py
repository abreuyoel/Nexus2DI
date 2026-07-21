import requests

def test_options():
    url = "http://localhost:8000/auth/login"
    headers = {
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "POST",
    }
    print(f"Sending OPTIONS to {url}")
    try:
        resp = requests.options(url, headers=headers)
        print(f"Status: {resp.status_code}")
        print("Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_options()
