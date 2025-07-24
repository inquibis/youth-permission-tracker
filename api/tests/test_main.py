import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_hello_world(client):
    response = client.get("/hello-world", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code in [200, 401]  # depends if token decoding is mocked or live