"""
End-to-end modular tests for the complete betting flow covering creation, challenging, proof upload, and resolution.
Follows the Arrange-Act-Assert pattern and relies on conftest.py fixtures for DB isolation.
"""
import pytest
from datetime import datetime, timedelta

def test_full_betting_flow_creator_wins(client, create_user_and_get_token):
    """
    Test scenario where the creator uploads proof, challengers vote 'cool',
    and the bet resolves to WON, giving the creator all staked points.
    """
    # ================= ARRANGE =================
    creator_token = create_user_and_get_token("creatorWinner", "cw@gmail.com")
    challenger1_token = create_user_and_get_token("chal1W", "c1w@gmail.com")
    challenger2_token = create_user_and_get_token("chal2W", "c2w@gmail.com")
    
    # ================= ACT =================
    # 1. Creator creates a bet (Stake: 7, Initial Balance: 10 -> New Balance: 3)
    deadline = (datetime.now() + timedelta(days=7)).isoformat()
    bet_data = {
        "title": "I will lose 1kg this week",
        "criteria": "Timestamped scale photo",
        "amount": 7,
        "deadline": deadline
    }
    create_res = client.post("/bets/", json=bet_data, headers={"Authorization": f"Bearer {creator_token}"})
    assert create_res.status_code == 201
    bet_id = create_res.json()["id"]
    
    # 2. Challengers bid on the bet (Stakes: 4 and 5)
    c1_res = client.post(f"/bets/{bet_id}/challenge", json={"amount": 4}, headers={"Authorization": f"Bearer {challenger1_token}"})
    assert c1_res.status_code == 201
    
    c2_res = client.post(f"/bets/{bet_id}/challenge", json={"amount": 5}, headers={"Authorization": f"Bearer {challenger2_token}"})
    assert c2_res.status_code == 201

    # 3. Creator uploads proof
    proof_files = {"file": ("proof.jpg", b"fake_image_content", "image/jpeg")}
    proof_data = {"comment": "Here is my scale photo!"}
    proof_res = client.post(f"/bets/{bet_id}/proof", data=proof_data, files=proof_files, headers={"Authorization": f"Bearer {creator_token}"})
    assert proof_res.status_code == 200
    assert proof_res.json()["status"] == "pending"

    # 4. Challengers vote 'cool' (Tribunal Verification)
    vote1_res = client.post(f"/bets/{bet_id}/vote?vote=cool", headers={"Authorization": f"Bearer {challenger1_token}"})
    assert vote1_res.status_code == 200
    
    vote2_res = client.post(f"/bets/{bet_id}/vote?vote=cool", headers={"Authorization": f"Bearer {challenger2_token}"})
    assert vote2_res.status_code == 200
    
    # ================= ASSERT =================
    # The second vote should trigger auto-resolution to WON
    assert vote2_res.json()["bet_status"] == "won"
    
    # Creator won! They should get their stake (7) back + the challenger pool (9). Total = 16.
    # Initial balance (10) - Stake (7) + Winnings & Refund (16) = 19
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {creator_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["points"] == 19

def test_full_betting_flow_creator_loses(client, create_user_and_get_token):
    """
    Test scenario where the creator uploads proof but challengers vote 'not_cool',
    causing the bet to resolve to LOST. The proportional payouts are verified.
    """
    # ================= ARRANGE =================
    creator_token = create_user_and_get_token("creatorLoser", "cl@gmail.com")
    challenger1_token = create_user_and_get_token("chal1L", "c1l@gmail.com")
    challenger2_token = create_user_and_get_token("chal2L", "c2l@gmail.com")
    
    # ================= ACT =================
    # 1. Creator creates a bet (Stake: 7)
    deadline = (datetime.now() + timedelta(days=7)).isoformat()
    create_res = client.post("/bets/", json={
        "title": "I will wake up at 6am everyday",
        "criteria": "Time lapse",
        "amount": 7,
        "deadline": deadline
    }, headers={"Authorization": f"Bearer {creator_token}"})
    bet_id = create_res.json()["id"]
    
    # 2. Challengers bid (stakes 4 and 5)
    c1_res = client.post(f"/bets/{bet_id}/challenge", json={"amount": 4}, headers={"Authorization": f"Bearer {challenger1_token}"})
    c1_challenge_id = c1_res.json()["id"]
    
    c2_res = client.post(f"/bets/{bet_id}/challenge", json={"amount": 5}, headers={"Authorization": f"Bearer {challenger2_token}"})
    c2_challenge_id = c2_res.json()["id"]
    
    
    # 3. Creator uploads bad proof
    proof_files = {"file": ("fake_proof.png", b"nothing_here", "image/png")}
    proof_data = {"comment": "overslept a bit"}
    client.post(f"/bets/{bet_id}/proof", data=proof_data, files=proof_files, headers={"Authorization": f"Bearer {creator_token}"})
    
    # 4. Challengers vote 'not_cool'
    client.post(f"/bets/{bet_id}/vote?vote=not_cool", headers={"Authorization": f"Bearer {challenger1_token}"})
    vote2_res = client.post(f"/bets/{bet_id}/vote?vote=not_cool", headers={"Authorization": f"Bearer {challenger2_token}"})
    
    # ================= ASSERT =================
    assert vote2_res.status_code == 200
    assert vote2_res.json()["bet_status"] == "lost"
    
    # 5. Verify Proportional payout model
    # C1 staked 4. Creator matched with 4. Total matched by creator to others = 9. 
    # C1 payout = 4 (stake returned) + floor((4/9)*7) (share of creator's stake) = 4 + 3 = 7.
    # Initial points for C1 = 10, gave 4, got 7 => 13
    me1_res = client.get("/auth/me", headers={"Authorization": f"Bearer {challenger1_token}"})
    assert me1_res.status_code == 200
    
    # Debug print to see what the actual points are
    print("CHALLENGER 1 POINTS: ", me1_res.json()["points"])
    assert me1_res.json()["points"] == 13
        
    # C2 staked 5. payout = 5 (stake returned) + floor((5/9)*7) (share of creator's) = 5 + floor(3.88) = 5 + 3 = 8.
    # Initial points for C2 = 10, gave 5, got 8 => 13
    me2_res = client.get("/auth/me", headers={"Authorization": f"Bearer {challenger2_token}"})
    assert me2_res.status_code == 200
    assert me2_res.json()["points"] == 13

def test_bet_cancellation_refunds(client, create_user_and_get_token):
    """
    Test scenario where the creator cancels the bet before the deadline,
    refunding all participants their original stakes.
    """
    # ================= ARRANGE =================
    creator_token = create_user_and_get_token("creatorCancel", "cc@gmail.com")
    challenger_token = create_user_and_get_token("chalCancel", "chc@gmail.com")
    
    # ================= ACT =================
    # 1. Create Bet
    deadline = (datetime.now() + timedelta(days=7)).isoformat()
    create_res = client.post("/bets/", json={
        "title": "I will read 10 pages",
        "criteria": "Summary notes",
        "amount": 5,
        "deadline": deadline
    }, headers={"Authorization": f"Bearer {creator_token}"})
    bet_id = create_res.json()["id"]
    
    # 2. Challenger bid (stake 3)
    c_res = client.post(f"/bets/{bet_id}/challenge", json={"amount": 3}, headers={"Authorization": f"Bearer {challenger_token}"})
    challenge_id = c_res.json()["id"]
    
    # 3. Creator cancels bet
    cancel_res = client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers={"Authorization": f"Bearer {creator_token}"})
    
    # ================= ASSERT =================
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify refunds (both should be completely refunded and back to 10 points)
    me_c = client.get("/auth/me", headers={"Authorization": f"Bearer {creator_token}"})
    assert me_c.status_code == 200
    assert me_c.json()["points"] == 10  # Started with 10, staked 5, staked 3 (to match challenger), got 8 refunded
        
    me_ch = client.get("/auth/me", headers={"Authorization": f"Bearer {challenger_token}"})
    assert me_ch.status_code == 200
    assert me_ch.json()["points"] == 10 # Started with 10, staked 3, got 3 refunded
