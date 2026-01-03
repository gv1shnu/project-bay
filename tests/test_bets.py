def test_create_bet_insufficient_funds(client, db):
    # 1. Create a user (logic would usually be in an auth test)
    # 2. Get a token
    # 3. Attempt to place a bet larger than 10.0 (the default points)

    # Mocking a login and then:
    response = client.post(
        "/bets/",
        json={"amount": 50.0, "description": "High stakes"},
        headers={"Authorization": "Bearer <mock_token>"}
    )
    # Depending on your router logic, this should fail
    # assert response.status_code == 400