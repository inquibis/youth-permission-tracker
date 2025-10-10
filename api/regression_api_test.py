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
print("Checking base data")
print("Verify user roles list")
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


print("Verify activity list")
resp = get(endpoint="/activity-ideas",payload={})
assert resp.json() == [
  "Airport Tour",
  "Alpine skiing",
  "Archery",
  "Arts",
  "Assist the disabled",
  "Auto mechanics & repair",
  "Aviation",
  "Backpacking",
  "Barbecue party",
  "Beach party",
  "Block party",
  "Bowling",
  "Camping trip",
  "Canoeing",
  "Car wash",
  "Career clinic",
  "Chemistry",
  "Child care",
  "Christmas party",
  "Cinematography",
  "Civil defense",
  "College panel discussion",
  "Communications",
  "Community cleanup proj.",
  "Conservation proj.",
  "Cooking",
  "COPE",
  "Cross-country skiing",
  "Cycling",
  "Dance",
  "Dating panel",
  "Diet & nutrition",
  "Emergency prep.",
  "Energy",
  "Ethics debate",
  "Fashion show",
  "Financial investing",
  "Fire safety",
  "First aid/CPR/EMT",
  "Fishing",
  "Food drive",
  "Genealogy",
  "Go-carts",
  "Gourmet cooking",
  "Halloween party",
  "Ham radio",
  "Home repairs",
  "Horseback riding",
  "How to buy a car",
  "Hunting",
  "Ice-skating",
  "Job interview skills",
  "Leadership skills",
  "Leave no Trace",
  "Lifesaving",
  "Long boat cruise",
  "Military obstacle course",
  "Mountaineering",
  "Olympics",
  "Orienteering",
  "Part-time job clinic",
  "Photography",
  "Physical fitness",
  "Picnic",
  "Pistol shooting",
  "Planetarium",
  "Plants & wildlife",
  "Produce a play",
  "Public speaking",
  "Rappelling",
  "Rifle shooting",
  "River rafting",
  "Road rally",
  "Rock climbing",
  "Rocketry",
  "Sailing/cruise",
  "Scholarships",
  "Scuba",
  "Service projects",
  "Shotgun shooting",
  "Snorkeling",
  "Spelunking",
  "Sports day/Olympics",
  "Sports medicine",
  "Swim meet",
  "Swimming party",
  "Tennis clinic",
  "Train trip",
  "University visit",
  "Visit a court",
  "Visit ballet",
  "Visit opera",
  "Visit symphony",
  "Water skiing",
  "Watercraft",
  "Wilderness survival",
  "Winter sports"
]



##########
###  USER SECTION
print("Verify current user")
resp = get(endpoint="/current-user",payload={})
assert resp.json() == {
  "role": "tester",
  "is_guardian": 1,
  "username": "tester",
  "exp": 1760124213
}


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
resp = post(endpoint="/activity",payload=payload)
assert resp.json()["id"] == 1


print("verify activity was created")
payload = {
    "id":1
}
resp = get(endpoint="/activity",payload=payload)


print("Testing new activity creation method")
payload = {
  "activity_name": "my new activity",
  "description": "activity testing",
  "groups": [
    "priest","young men"
  ],
  "drivers": [
    "mr. shabo"
  ],
  "budget": [
    {
      "item": "monkey",
      "amount": 1200
    }
  ],
  "date_start": "2025-10-10",
  "date_end": "2025-10-10",
  "purpose": "to have fun"
}
resp = post(endpoint="/activity-information",payload=payload)
assert resp.json()["id"] == 1


print("Verify activity created")
payload = {
    "activity_id":1,
    "activity_name":"my new activity"
}
resp = get(endpoint="/activity-information",payload=payload)


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
