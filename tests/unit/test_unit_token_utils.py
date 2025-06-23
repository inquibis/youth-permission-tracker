from api.contact import generate_token

def test_generate_token_length():
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) >= 43  # token_urlsafe(32) yields at least 43 characters
