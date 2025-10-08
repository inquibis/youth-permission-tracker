import requests
import pytest

base_url = "localhost"
headers = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

def post(endpoint:str, payload:dict={})->Response:
    resp = requests.post(url=f"{base_url}/users", payload=payload, verify=False, headers=header)
    if resp.ok is False:
        print(f"Test failed.  {resp.status_code} {resp.text}")
    return resp


def get(endpoint:str, payload:dict={})->str:
    resp = requests.post(url=f"{base_url}/users", params=payload, verify=False, headers = header)
    if resp.ok is False:
        print(f"Test failed.  {resp.status_code} {resp.text}")
    return resp


print("Get token")
payload = {
    "first_name": "tester",
    "last_name": "testing123"
}
resp = post(endpoint="/token", payload=payload)
token = resp.json()["access_token"]
header = {"Authorization": f"Bearer {token}"}

####################
###  base data
print("Verify user groups")
resp = post(endpoint="/list-roles")
assert list(resp.text) == ["admin",
  "bishopric",
  "guardian",
  "presidency",
  "tester",
  "youth"]


print("Test Group list")
resp = get(endpoint="/list-groups")
assert list(resp.text) == [
  "Deacon",
  "Teacher",
  "Priest",
  "Young Man",
  "Young Woman",
  "Young Woman-younger",
  "Young Woman-older"
]

print("verify user list")
resp = get(endpoint="/users")
assert len(list(resp.text)) == 2

print("create user")
payload = {
  "first_name": "sam",
  "last_name": "smith",
  "guardian_name": "luke smith",
  "guardian_email": "smith@email.com",
  "guardian_cell": "8017038187",
  "user_email": "sam@email.com",
  "user_cell": "8015604223",
  "is_active": True,
  "groups": [
    "priest"
  ],
  "role": "counselor",
  "guardian_password": "p123"
}

##################
## SIGNATORS
print("Verify current signator information")
resp = get(endpoint="/contact",payload={"level":1})
assert dict(resp.text) == {
  "text_number": 888,
  "lvl": 1,
  "name": "vers"
}

print("verify signator can be updated")
payload = {
  "text_number": 8017038187,
  "lvl": 1,
  "name": "ltodd"
}
resp = post(endpoint="/contact",payload=payload)
assert resp.json == {
  "status": "Updated"
}

print("Verify signator information updated")
resp = get(endpoint="/contact",payload={"level":1})
assert resp.json == {
  "text_number": 8017038187,
  "lvl": 1,
  "name": "ltodd"
}

####################
## activities
print("Verify actifity list to begin is empty")
resp = get(endpoint="/activity-all")
assert resp.text == "[]"

print("Create an activity")
payload = {
  "activity_name": "my first activity",
  "date_start": "2025-10-08T03:25:55.236Z",
  "date_end": "2025-10-08T03:25:55.236Z",
  "drivers": [
    "john samson"
  ],
  "description": "fun activity doing fun stuff",
  "groups": [
    "priests","young men"
  ]
}



####################
## calling
print("Call signator")
payload = {
    "level":1,
    "acitvity_id":16
}
resp = post(endpoint="/contact/call",payload=payload)
assert resp.json == {
  "status": "Done"
}

print("Contact guardian")
