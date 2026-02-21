from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from datetime import datetime, timedelta
import sys

# Create tables for testing
Base.metadata.create_all(bind=engine)
from datetime import datetime, timedelta
import sys

import uuid
def get_token(client, username, email):
    username = username + str(uuid.uuid4())[:4]
    email = str(uuid.uuid4())[:4] + email
    
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123"
    })
    
    login_res = client.post("/auth/login", data={
        "username": username,
        "password": "password123"
    })
    
    data = login_res.json()
    if "access_token" not in data:
        raise RuntimeError(f"Login failed: {data}")
        
    return data["access_token"]

client = TestClient(app)

creator_token = get_token(client, "creatorWinner", "cw@gmail.com")
chal1_token = get_token(client, "chal1W", "c1w@gmail.com")
chal2_token = get_token(client, "chal2W", "c2w@gmail.com")

bet_res = client.post("/bets/", json={"title": "I will walk for 3kms today. " + str(uuid.uuid4()), "criteria": "And a valid long criteria constraint that is also very long", "amount": 7, "deadline": (datetime.now() + timedelta(days=7)).isoformat()}, headers={"Authorization": f"Bearer {creator_token}"})
if bet_res.status_code != 201:
    print("BET ERROR:", bet_res.status_code, bet_res.json())
    import sys
    sys.exit(1)
bet_id = bet_res.json()["id"]

client.post(f"/bets/{bet_id}/challenge", json={"amount": 4}, headers={"Authorization": f"Bearer {chal1_token}"})
client.post(f"/bets/{bet_id}/challenge", json={"amount": 5}, headers={"Authorization": f"Bearer {chal2_token}"})

proof_res = client.post(f"/bets/{bet_id}/proof", data={"comment": "c"}, files={"file": ("fake.jpg", b"123", "image/jpeg")}, headers={"Authorization": f"Bearer {creator_token}"})
client.post(f"/bets/{bet_id}/vote?vote=cool", headers={"Authorization": f"Bearer {chal1_token}"})
v2 = client.post(f"/bets/{bet_id}/vote?vote=cool", headers={"Authorization": f"Bearer {chal2_token}"})

print("VOTE 2 JSON:", v2.json())

me = client.get("/auth/me", headers={"Authorization": f"Bearer {creator_token}"})
print("CREATOR POINTS:", me.json()["points"], "EXPECTED: 19")
