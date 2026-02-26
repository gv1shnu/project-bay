const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

// Utility: convert a Postgres UUID string to bytes32
function uuidToBytes32(uuid) {
    const hex = uuid.replace(/-/g, "");
    return "0x" + hex.padEnd(64, "0");
}

describe("BetEscrow", function () {
    let escrow;
    let creator, challengerB, challengerC, stranger;

    const BET_ID = uuidToBytes32("aaaabbbb-cccc-dddd-eeee-ffffffffffff");
    const ONE_ETH = ethers.parseEther("1.0");
    const HALF_ETH = ethers.parseEther("0.5");
    const WEEK = 7 * 24 * 60 * 60; // seconds

    beforeEach(async function () {
        [creator, challengerB, challengerC, stranger] = await ethers.getSigners();
        const BetEscrow = await ethers.getContractFactory("BetEscrow");
        escrow = await BetEscrow.deploy();
    });

    // ─────────────────────────────────────────────
    //  Helpers
    // ─────────────────────────────────────────────
    async function createBet(overrides = {}) {
        const deadline = (await time.latest()) + WEEK;
        return escrow.connect(creator).createBet(BET_ID, deadline, {
            value: ONE_ETH,
            ...overrides,
        });
    }

    // ─────────────────────────────────────────────
    //  createBet
    // ─────────────────────────────────────────────
    describe("createBet", function () {
        it("should lock ETH and emit BetCreated", async function () {
            const deadline = (await time.latest()) + WEEK;
            await expect(
                escrow.connect(creator).createBet(BET_ID, deadline, { value: ONE_ETH })
            )
                .to.emit(escrow, "BetCreated")
                .withArgs(BET_ID, creator.address, ONE_ETH, deadline);

            const bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(0); // Active
            expect(bet.stake).to.equal(ONE_ETH);
        });

        it("should reject zero stake", async function () {
            const deadline = (await time.latest()) + WEEK;
            await expect(
                escrow.connect(creator).createBet(BET_ID, deadline, { value: 0 })
            ).to.be.revertedWith("Must stake some ETH");
        });

        it("should reject duplicate betId", async function () {
            await createBet();
            const deadline = (await time.latest()) + WEEK;
            await expect(
                escrow.connect(creator).createBet(BET_ID, deadline, { value: ONE_ETH })
            ).to.be.revertedWith("Bet already exists");
        });
    });

    // ─────────────────────────────────────────────
    //  challengeBet
    // ─────────────────────────────────────────────
    describe("challengeBet", function () {
        beforeEach(createBet);

        it("should allow challengers to lock ETH", async function () {
            await expect(
                escrow.connect(challengerB).challengeBet(BET_ID, { value: HALF_ETH })
            )
                .to.emit(escrow, "BetChallenged")
                .withArgs(BET_ID, challengerB.address, HALF_ETH);

            const bet = await escrow.getBet(BET_ID);
            expect(bet.challengerPool).to.equal(HALF_ETH);
            expect(bet.challengeCount).to.equal(1);
        });

        it("should reject duplicate challengers", async function () {
            await escrow.connect(challengerB).challengeBet(BET_ID, { value: HALF_ETH });
            await expect(
                escrow.connect(challengerB).challengeBet(BET_ID, { value: HALF_ETH })
            ).to.be.revertedWith("Already a challenger");
        });

        it("should not allow creator to challenge own bet", async function () {
            await expect(
                escrow.connect(creator).challengeBet(BET_ID, { value: HALF_ETH })
            ).to.be.revertedWith("Creator cannot challenge own bet");
        });
    });

    // ─────────────────────────────────────────────
    //  withdrawChallenge
    // ─────────────────────────────────────────────
    describe("withdrawChallenge", function () {
        beforeEach(async function () {
            await createBet();
            await escrow.connect(challengerB).challengeBet(BET_ID, { value: HALF_ETH });
        });

        it("should refund challenger who pulls out", async function () {
            const before = await ethers.provider.getBalance(challengerB.address);
            const tx = await escrow.connect(challengerB).withdrawChallenge(BET_ID);
            const receipt = await tx.wait();
            const gasUsed = receipt.gasUsed * tx.gasPrice;
            const after = await ethers.provider.getBalance(challengerB.address);

            expect(after).to.be.closeTo(before + HALF_ETH, ethers.parseEther("0.001"));

            const bet = await escrow.getBet(BET_ID);
            expect(bet.challengerPool).to.equal(0);
        });

        it("should reject double withdraw", async function () {
            await escrow.connect(challengerB).withdrawChallenge(BET_ID);
            await expect(
                escrow.connect(challengerB).withdrawChallenge(BET_ID)
            ).to.be.revertedWith("Already withdrawn");
        });
    });

    // ─────────────────────────────────────────────
    //  cancelBet
    // ─────────────────────────────────────────────
    describe("cancelBet", function () {
        it("should refund everyone on cancel", async function () {
            await createBet();
            await escrow.connect(challengerB).challengeBet(BET_ID, { value: HALF_ETH });

            const creatorBefore = await ethers.provider.getBalance(creator.address);
            const bBefore = await ethers.provider.getBalance(challengerB.address);

            await escrow.connect(creator).cancelBet(BET_ID);

            const creatorAfter = await ethers.provider.getBalance(creator.address);
            const bAfter = await ethers.provider.getBalance(challengerB.address);

            expect(creatorAfter).to.be.gt(creatorBefore); // got stake back (minus gas)
            expect(bAfter).to.equal(bBefore + HALF_ETH);

            const bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(4); // Cancelled
        });

        it("should reject cancel from non-creator", async function () {
            await createBet();
            await expect(
                escrow.connect(stranger).cancelBet(BET_ID)
            ).to.be.revertedWith("Not the bet creator");
        });
    });

    // ─────────────────────────────────────────────
    //  Full Happy Path: Creator Wins
    // ─────────────────────────────────────────────
    describe("Scenario: Creator Wins (A Wins)", function () {
        it("should pay creator the full pot when challengers approve", async function () {
            await createBet(); // 1 ETH
            await escrow.connect(challengerB).challengeBet(BET_ID, {
                value: ethers.parseEther("0.4"),
            });
            await escrow.connect(challengerC).challengeBet(BET_ID, {
                value: ethers.parseEther("0.5"),
            });

            // Creator submits proof
            await escrow.connect(creator).submitProof(BET_ID);
            let bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(1); // Pending

            // Both challengers approve
            await escrow.connect(challengerB).castVote(BET_ID, true);
            await escrow.connect(challengerC).castVote(BET_ID, true);

            // Fast-forward past vote window (24 hours)
            await time.increase(24 * 60 * 60 + 1);

            const creatorBefore = await ethers.provider.getBalance(creator.address);
            await escrow.connect(stranger).resolve(BET_ID); // anyone can trigger
            const creatorAfter = await ethers.provider.getBalance(creator.address);

            // Creator should have received 1 + 0.4 + 0.5 = 1.9 ETH
            expect(creatorAfter - creatorBefore).to.be.closeTo(
                ethers.parseEther("1.9"),
                ethers.parseEther("0.01")
            );

            bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(2); // Won
        });
    });

    // ─────────────────────────────────────────────
    //  Full Happy Path: Creator Loses
    // ─────────────────────────────────────────────
    describe("Scenario: Creator Loses (A Fumbles)", function () {
        it("should pay challengers proportionally when majority rejects", async function () {
            await createBet(); // 1 ETH stake (A)
            await escrow.connect(challengerB).challengeBet(BET_ID, {
                value: ethers.parseEther("0.4"), // B: 4/9 of pool
            });
            await escrow.connect(challengerC).challengeBet(BET_ID, {
                value: ethers.parseEther("0.5"), // C: 5/9 of pool
            });

            await escrow.connect(creator).submitProof(BET_ID);

            // Both challengers reject
            await escrow.connect(challengerB).castVote(BET_ID, false);
            await escrow.connect(challengerC).castVote(BET_ID, false);

            await time.increase(24 * 60 * 60 + 1);

            const bBefore = await ethers.provider.getBalance(challengerB.address);
            const cBefore = await ethers.provider.getBalance(challengerC.address);

            await escrow.connect(stranger).resolve(BET_ID);

            const bAfter = await ethers.provider.getBalance(challengerB.address);
            const cAfter = await ethers.provider.getBalance(challengerC.address);

            // B should get 0.4 + (0.4/0.9)*1 ≈ 0.844 ETH
            expect(bAfter - bBefore).to.be.closeTo(
                ethers.parseEther("0.844"),
                ethers.parseEther("0.01")
            );
            // C should get 0.5 + (0.5/0.9)*1 ≈ 1.055 ETH
            expect(cAfter - cBefore).to.be.closeTo(
                ethers.parseEther("1.055"),
                ethers.parseEther("0.01")
            );

            const bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(3); // Lost
        });
    });

    // ─────────────────────────────────────────────
    //  Failsafe: No Votes → Creator Wins
    // ─────────────────────────────────────────────
    describe("Failsafe: No votes → Creator wins", function () {
        it("should auto-award creator if no challenger votes in 24h", async function () {
            await createBet();
            await escrow.connect(challengerB).challengeBet(BET_ID, {
                value: ethers.parseEther("0.4"),
            });

            await escrow.connect(creator).submitProof(BET_ID);

            // Nobody votes — fast forward past window
            await time.increase(24 * 60 * 60 + 1);

            const creatorBefore = await ethers.provider.getBalance(creator.address);
            await escrow.connect(stranger).resolve(BET_ID);
            const creatorAfter = await ethers.provider.getBalance(creator.address);

            // Creator should get full pot (1 + 0.4 = 1.4 ETH)
            expect(creatorAfter - creatorBefore).to.be.closeTo(
                ethers.parseEther("1.4"),
                ethers.parseEther("0.01")
            );

            const bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(2); // Won
        });
    });

    // ─────────────────────────────────────────────
    //  Failsafe: Deadline Expired → expireBet
    // ─────────────────────────────────────────────
    describe("Failsafe: Deadline passed, no proof → expireBet", function () {
        it("should allow anyone to trigger refund after deadline", async function () {
            await createBet();
            await escrow.connect(challengerB).challengeBet(BET_ID, {
                value: HALF_ETH,
            });

            // Fast-forward past the bet deadline
            await time.increase(WEEK + 1);

            await escrow.connect(stranger).expireBet(BET_ID);

            const bet = await escrow.getBet(BET_ID);
            expect(bet.status).to.equal(4); // Cancelled
        });
    });
});
