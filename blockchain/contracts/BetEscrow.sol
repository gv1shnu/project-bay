// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title BetEscrow
 * @notice Handles the on-chain escrow, challenge, voting, and payout logic
 *         for Project Bay bets. Mirrors the Web2 logic in bet_service.py.
 *
 * Flow:
 *  1. Creator calls createBet()   → stakes ETH into escrow
 *  2. Challengers call challengeBet() → add ETH to the challenger pool
 *  3. Creator calls submitProof() → opens a 24h vote window
 *  4. Challengers call castVote() → approve or reject the proof
 *  5. Anyone calls resolve()      → majority wins; payouts fire automatically
 *
 * Failsafes (from IN_MY_OWN_WORDS.md):
 *  - If no challengers vote within 24h of proof submission → creator wins
 *  - Creator can cancel before proof submission → full refund
 *  - Challengers can withdraw before proof is submitted → full refund
 */
contract BetEscrow {
    // ─────────────────────────────────────────────
    //  Enums & Structs
    // ─────────────────────────────────────────────

    enum BetStatus {
        Active,      // accepting challenges
        Pending,     // proof submitted, voting open
        Won,         // creator won
        Lost,        // creator lost
        Cancelled    // cancelled before proof
    }

    struct Challenge {
        address challenger;
        uint256 amount;
        bool voted;
        bool approves; // true = creator wins, false = creator loses
        bool withdrawn;
    }

    struct Bet {
        address creator;
        uint256 stake;          // creator's locked ETH
        uint256 deadline;       // Unix timestamp — bet expires if proof not submitted
        uint256 proofAt;        // when proof was submitted
        uint256 voteWindow;     // seconds challengers have to vote after proof (default 24h)
        BetStatus status;
        uint256 challengerPool; // total ETH staked by challengers
        uint256 challengeCount;
    }

    // ─────────────────────────────────────────────
    //  Storage
    // ─────────────────────────────────────────────

    // betId (from Postgres) → Bet
    mapping(bytes32 => Bet) public bets;
    // betId → challenger index → Challenge
    mapping(bytes32 => mapping(uint256 => Challenge)) public challenges;
    // betId → challenger address → index (1-based; 0 = not a challenger)
    mapping(bytes32 => mapping(address => uint256)) public challengerIndex;

    uint256 public constant DEFAULT_VOTE_WINDOW = 24 hours;

    // ─────────────────────────────────────────────
    //  Events
    // ─────────────────────────────────────────────

    event BetCreated(bytes32 indexed betId, address indexed creator, uint256 stake, uint256 deadline);
    event BetChallenged(bytes32 indexed betId, address indexed challenger, uint256 amount);
    event ChallengeWithdrawn(bytes32 indexed betId, address indexed challenger, uint256 amount);
    event ProofSubmitted(bytes32 indexed betId, uint256 proofAt);
    event VoteCast(bytes32 indexed betId, address indexed voter, bool approves);
    event BetResolved(bytes32 indexed betId, BetStatus result);
    event BetCancelled(bytes32 indexed betId);

    // ─────────────────────────────────────────────
    //  Modifiers
    // ─────────────────────────────────────────────

    modifier betExists(bytes32 betId) {
        require(bets[betId].creator != address(0), "Bet does not exist");
        _;
    }

    modifier onlyCreator(bytes32 betId) {
        require(msg.sender == bets[betId].creator, "Not the bet creator");
        _;
    }

    modifier inStatus(bytes32 betId, BetStatus expected) {
        require(bets[betId].status == expected, "Invalid bet status for this action");
        _;
    }

    // ─────────────────────────────────────────────
    //  External Functions
    // ─────────────────────────────────────────────

    /**
     * @notice Creator locks ETH and registers the bet.
     * @param betId  The Postgres bet UUID (converted to bytes32 off-chain)
     * @param deadline Unix timestamp for the bet deadline
     */
    function createBet(bytes32 betId, uint256 deadline) external payable {
        require(bets[betId].creator == address(0), "Bet already exists");
        require(msg.value > 0, "Must stake some ETH");
        require(deadline > block.timestamp, "Deadline must be in the future");

        bets[betId] = Bet({
            creator: msg.sender,
            stake: msg.value,
            deadline: deadline,
            proofAt: 0,
            voteWindow: DEFAULT_VOTE_WINDOW,
            status: BetStatus.Active,
            challengerPool: 0,
            challengeCount: 0
        });

        emit BetCreated(betId, msg.sender, msg.value, deadline);
    }

    /**
     * @notice A challenger bets against the creator.
     * @param betId  The bet to challenge
     */
    function challengeBet(bytes32 betId)
        external
        payable
        betExists(betId)
        inStatus(betId, BetStatus.Active)
    {
        Bet storage bet = bets[betId];
        require(block.timestamp < bet.deadline, "Bet deadline has passed");
        require(msg.sender != bet.creator, "Creator cannot challenge own bet");
        require(msg.value > 0, "Must stake some ETH");
        require(challengerIndex[betId][msg.sender] == 0, "Already a challenger");

        bet.challengeCount++;
        uint256 idx = bet.challengeCount;
        challengerIndex[betId][msg.sender] = idx;

        challenges[betId][idx] = Challenge({
            challenger: msg.sender,
            amount: msg.value,
            voted: false,
            approves: false,
            withdrawn: false
        });

        bet.challengerPool += msg.value;

        emit BetChallenged(betId, msg.sender, msg.value);
    }

    /**
     * @notice A challenger pulls out before proof is submitted.
     * @param betId  The bet to withdraw from
     */
    function withdrawChallenge(bytes32 betId)
        external
        betExists(betId)
        inStatus(betId, BetStatus.Active)
    {
        uint256 idx = challengerIndex[betId][msg.sender];
        require(idx != 0, "Not a challenger");

        Challenge storage ch = challenges[betId][idx];
        require(!ch.withdrawn, "Already withdrawn");

        ch.withdrawn = true;
        bets[betId].challengerPool -= ch.amount;

        (bool sent, ) = msg.sender.call{value: ch.amount}("");
        require(sent, "Refund failed");

        emit ChallengeWithdrawn(betId, msg.sender, ch.amount);
    }

    /**
     * @notice Creator cancels the bet (full refund to everyone).
     * @param betId  The bet to cancel
     */
    function cancelBet(bytes32 betId)
        external
        betExists(betId)
        onlyCreator(betId)
        inStatus(betId, BetStatus.Active)
    {
        Bet storage bet = bets[betId];
        bet.status = BetStatus.Cancelled;

        // Refund all challengers
        for (uint256 i = 1; i <= bet.challengeCount; i++) {
            Challenge storage ch = challenges[betId][i];
            if (!ch.withdrawn && ch.amount > 0) {
                ch.withdrawn = true;
                (bool sent, ) = ch.challenger.call{value: ch.amount}("");
                require(sent, "Challenger refund failed");
            }
        }

        // Refund creator
        uint256 creatorRefund = bet.stake;
        bet.stake = 0;
        (bool ok, ) = bet.creator.call{value: creatorRefund}("");
        require(ok, "Creator refund failed");

        emit BetCancelled(betId);
    }

    /**
     * @notice Creator submits proof — starts the 24h vote window.
     * @param betId  The bet for which proof is being submitted
     */
    function submitProof(bytes32 betId)
        external
        betExists(betId)
        onlyCreator(betId)
        inStatus(betId, BetStatus.Active)
    {
        Bet storage bet = bets[betId];
        require(block.timestamp < bet.deadline, "Bet deadline has passed");

        bet.proofAt = block.timestamp;
        bet.status = BetStatus.Pending;

        emit ProofSubmitted(betId, block.timestamp);
    }

    /**
     * @notice A challenger votes on the proof.
     * @param betId    The bet
     * @param approves true = "proof is valid, creator wins"
     *                 false = "proof is invalid, creator loses"
     */
    function castVote(bytes32 betId, bool approves)
        external
        betExists(betId)
        inStatus(betId, BetStatus.Pending)
    {
        Bet storage bet = bets[betId];
        require(
            block.timestamp <= bet.proofAt + bet.voteWindow,
            "Vote window has closed"
        );

        uint256 idx = challengerIndex[betId][msg.sender];
        require(idx != 0, "Not a challenger");

        Challenge storage ch = challenges[betId][idx];
        require(!ch.withdrawn, "Challenger has withdrawn");
        require(!ch.voted, "Already voted");

        ch.voted = true;
        ch.approves = approves;

        emit VoteCast(betId, msg.sender, approves);
    }

    /**
     * @notice Resolves the bet after the vote window.
     *         Can be called by anyone once the window closes.
     *         Majority wins. Ties → creator wins (innocent until proven guilty).
     *         If no one voted → creator wins (failsafe).
     * @param betId  The bet to resolve
     */
    function resolve(bytes32 betId)
        external
        betExists(betId)
        inStatus(betId, BetStatus.Pending)
    {
        Bet storage bet = bets[betId];
        require(
            block.timestamp > bet.proofAt + bet.voteWindow,
            "Vote window still open"
        );

        // Tally votes (only from non-withdrawn challengers)
        uint256 approveVotes;
        uint256 rejectVotes;
        uint256 activeChallengers; // challengers who haven't withdrawn

        for (uint256 i = 1; i <= bet.challengeCount; i++) {
            Challenge storage ch = challenges[betId][i];
            if (!ch.withdrawn) {
                activeChallengers++;
                if (ch.voted) {
                    if (ch.approves) approveVotes++;
                    else rejectVotes++;
                }
            }
        }

        // Failsafe: no active challengers left → creator wins
        // Failsafe: no one voted → creator wins
        bool creatorWins = (activeChallengers == 0) ||
                           (approveVotes >= rejectVotes); // ties go to creator

        if (creatorWins) {
            _payoutCreatorWins(betId, bet);
        } else {
            _payoutCreatorLoses(betId, bet);
        }
    }

    /**
     * @notice Deadline failsafe — if creator never submitted proof, anyone can
     *         call this after the deadline to cancel and refund everyone.
     * @param betId  The expired bet
     */
    function expireBet(bytes32 betId)
        external
        betExists(betId)
        inStatus(betId, BetStatus.Active)
    {
        Bet storage bet = bets[betId];
        require(block.timestamp > bet.deadline, "Deadline not yet passed");

        // Same logic as cancel: refund everyone
        bet.status = BetStatus.Cancelled;

        for (uint256 i = 1; i <= bet.challengeCount; i++) {
            Challenge storage ch = challenges[betId][i];
            if (!ch.withdrawn && ch.amount > 0) {
                ch.withdrawn = true;
                (bool sent, ) = ch.challenger.call{value: ch.amount}("");
                require(sent, "Challenger refund failed");
            }
        }

        uint256 creatorRefund = bet.stake;
        bet.stake = 0;
        (bool ok, ) = bet.creator.call{value: creatorRefund}("");
        require(ok, "Creator refund failed");

        emit BetCancelled(betId);
    }

    // ─────────────────────────────────────────────
    //  View Functions
    // ─────────────────────────────────────────────

    function getBet(bytes32 betId) external view returns (Bet memory) {
        return bets[betId];
    }

    function getChallenge(bytes32 betId, uint256 idx)
        external
        view
        returns (Challenge memory)
    {
        return challenges[betId][idx];
    }

    function getMyChallengeIndex(bytes32 betId) external view returns (uint256) {
        return challengerIndex[betId][msg.sender];
    }

    // ─────────────────────────────────────────────
    //  Internal Payout Logic
    // ─────────────────────────────────────────────

    /**
     * @dev Creator wins: gets back stake + full challenger pool.
     */
    function _payoutCreatorWins(bytes32 betId, Bet storage bet) internal {
        bet.status = BetStatus.Won;

        uint256 total = bet.stake + bet.challengerPool;
        bet.stake = 0;
        bet.challengerPool = 0;

        (bool ok, ) = bet.creator.call{value: total}("");
        require(ok, "Creator payout failed");

        emit BetResolved(betId, BetStatus.Won);
    }

    /**
     * @dev Creator loses: stake split proportionally among active challengers
     *      based on their contribution to the pool.
     *
     *      Each challenger gets: their_amount + (their_amount / pool) * creator_stake
     *      Using integer math: payout = ch.amount + (ch.amount * stake) / pool
     */
    function _payoutCreatorLoses(bytes32 betId, Bet storage bet) internal {
        bet.status = BetStatus.Lost;

        uint256 creatorStake = bet.stake;
        uint256 pool = bet.challengerPool;
        bet.stake = 0;
        bet.challengerPool = 0;

        for (uint256 i = 1; i <= bet.challengeCount; i++) {
            Challenge storage ch = challenges[betId][i];
            if (!ch.withdrawn && ch.amount > 0) {
                // Proportional share of creator's stake
                uint256 profit = (ch.amount * creatorStake) / pool;
                uint256 payout = ch.amount + profit;

                (bool sent, ) = ch.challenger.call{value: payout}("");
                require(sent, "Challenger payout failed");
            }
        }

        emit BetResolved(betId, BetStatus.Lost);
    }
}
