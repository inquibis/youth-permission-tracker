import pytest
from auth import hash_password, verify_password, create_token, decode_token
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_hash_and_verify_password():
    raw = "mypassword123"
    hashed = hash_password(raw)
    assert verify_password(raw, hashed)
    assert not verify_password("wrong", hashed)

def test_create_and_decode_token():
    data = {"username": "testuser", "role": "admin", "is_guardian": 0}
    token = create_token(data)
    decoded = decode_token(token)
    assert decoded.username == "testuser"
    assert decoded.role == "admin"