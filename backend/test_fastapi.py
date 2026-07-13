import sys
import traceback
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_endpoint():
    try:
        print("Testing /auth/login with test client...")
        response = client.post(
            "/auth/login",
            json={"username": "test_user", "password": "test_password"},
            headers={"Origin": "http://localhost:4200"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        print(f"Body: {response.text}")
    except Exception as e:
        print("EXCEPTION RAISED:")
        traceback.print_exc()

if __name__ == "__main__":
    test_login_endpoint()
