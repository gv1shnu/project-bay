"""Proof-upload file/status guards + is_personal_commitment fast-reject branches."""
from app.utils import validation as v
from tests.conftest import register_and_login, create_bet, follow

PNG = b"\x89PNG\r\n\x1a\n"


def _active_with_challenger(client, cstake=5):
    ch = register_and_login(client, "creator")
    xh = register_and_login(client, "chal")
    bet_id = create_bet(client, ch, amount=cstake).json()["id"]
    follow(client, xh, "creator")
    client.post(f"/bets/{bet_id}/challenge", json={"amount": 3}, headers=xh)
    return ch, xh, bet_id


def _upload(client, headers, bet_id, filename, blob, ctype="image/png"):
    return client.post(
        f"/bets/{bet_id}/proof",
        data={"comment": "done"},
        files={"file": (filename, blob, ctype)},
        headers=headers,
    )


def test_proof_rejects_disallowed_extension(client):
    ch, xh, bet_id = _active_with_challenger(client)
    r = _upload(client, ch, bet_id, "proof.txt", b"not an image", "text/plain")
    assert r.status_code == 400
    assert "file type not allowed" in r.json()["detail"].lower()


def test_proof_rejects_oversized_file(client):
    ch, xh, bet_id = _active_with_challenger(client)
    big = PNG + b"0" * (10 * 1024 * 1024 + 1)  # just over the 10 MB cap
    r = _upload(client, ch, bet_id, "proof.png", big)
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()


def test_proof_rejected_when_bet_not_active(client):
    ch, xh, bet_id = _active_with_challenger(client)
    assert _upload(client, ch, bet_id, "proof.png", PNG).status_code == 200  # -> PENDING
    # A second upload: bet is now PENDING, not ACTIVE.
    r = _upload(client, ch, bet_id, "proof.png", PNG)
    assert r.status_code == 400
    assert "active" in r.json()["detail"].lower()


# ── is_personal_commitment fast-reject branches ────────────────────────────

def test_personal_commitment_accepts_first_person_goal():
    assert v.is_personal("I will run 5km today") is True


def test_personal_commitment_rejects_too_short():
    assert v.is_personal("run") is False


def test_personal_commitment_rejects_no_first_person_pronoun():
    # NB: the pronoun check is a naive substring match, so words like "ship"
    # (contains "i") would sneak past it — this string avoids all of i/we/my/me
    # to actually exercise the no-pronoun rejection branch.
    assert v.is_personal("Run fast today") is False
