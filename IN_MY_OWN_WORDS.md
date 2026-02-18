# Project Bay: In my words

## Chapter 1: The Philosophy
I realized that self-improvement is lonely and easy to quit. 
However, if your friends are invested, it's kind of an indirect motivation to perform better. 
The pressure hits different. 
Positive Development!

## Chapter 2: The Core Loop
All registered users begin with an initial 10 points, for now.

### 1. Creation
User A (The Protagonist) decides to lock in.
- The Goal: "Lose 1kg this week."
- The Stake: A bets 7 points on themselves.
- The Terms: A defines what proof looks like (e.g., "Timestamped scale photo").
- Status: Active

#### Initial Check (impt)
- Spam classifier to be integrated to check content solely as a first person commitment rather than betting on external events of the world which poster cannot control. Llama was too slow and buggy, switching to API is preferred by me.
- Static posts i.e, bets that dont promote actions (make up and stuff) wouldnt be encouraged.
- Abuse classifier to be added to make this platform unfriendly to nsfw and darkness. This project is meant to be competitive and positive contributing to real growth.

Though all these may turn the platform absurd and uninteresting, I didn't intend it that way since the beginning and people can always use this repo to make better version for themselves, haha. 
Too much serious tone right, not my style, anyway continuing.

### 2. Challenges
User B sees the post and hits "Bet."
- B throws 4 points into the pot.
- B drags User C into the chat.
- User C pulls up and drops 5 points.

The Pot Logic:
- A's Stake: 7
- Challenger Pool: 9 (4+5)
- Total Locked: 16 points sitting on the table.

### 3. Cancellation
- If A realizes they love pizza too much, he can cancel before the deadline.
Everyone gets a full refund. No harm, no foul. Status: Cancelled
- Challengers B or C also can pull their funds out anytime before the deadline if they get bored.

## Chapter 3: The Verification System
No trust in the challengers (they want more), and we don't want to spam random users unless we have to.
I intend to use a hybrid jury duty model for this phase.

### Level 1: The Trust Check
- A uploads proof. B & C get a ping. They have 24 hours to review. Status: Pending.
- If they vote "Cool": Immediate payout. A wins. Game over. Status: Won.
- If they vote "Not Cool": The dispute flag is raised. Now we have drama. 
Status: Disputed.

### Level 2: The Tribunal
- The disputed proof goes to a public feed for Random Users (D, E, F, G).
- The Incentive: The winner of the bet pays a 5% "Court Fee" from the pot. 
This fee is equally split among the jurors who voted with the majority.
- The Consensus: First side to get a 3-vote majority wins.
Status: Won/Lost.

#### Users check
If the platform doesn’t have interested parties or don’t have that many users, this dispute can be forwarded to an AI, invoking API call to verify.  I personally, I don’t want this.

### Level 3: The Fail-Safe
- If B & C ignore the proof for 24 hours? A Wins Automatically.
- If the Dispute goes to the Jury and nobody votes? A Wins Automatically.
- Rule: Innocent until proven guilty. We never trap user funds.


## Chapter 4: The Payouts
I intend to use a Proportional Risk Model, and reward challengers proportionate to the points they put on the bet.

### Scenario 1: The Comeback (A Wins)
A uploads valid proof.
- A gets their 7 points back (Refund).
- A takes the entire 9 point challenger pool.
- Total: 16 points.
- B & C: Get nothing. Zero. Should've believed in the homie.

### Scenario 2: The Fumble (A Loses)
A fails to upload or the proof is fake.
- A loses their 7 points.
- B & C get paid based on skin in the game:
- User B -> Gets their 4 back + ~3 points profit.
- User C -> Gets their 5 back + ~4 points profit.

## Chapter 5: The Aspiration
The end game isn't just a webapp; it's a Trust Protocol.

Current State: Web2 (Postgres + Points).
Future State: Web3 (Blockchain + Crypto).

Moving from virtual to real world stakes makes this project grounded to our character.
However, trading in crypto will be made optional, since not everyone would wanna pour their hard earned trading funds into a personality challenge app. 

Open to ideas, still building MVP.
