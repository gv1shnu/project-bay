import { ethers } from "hardhat";

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying BetEscrow with account:", deployer.address);
    console.log(
        "Account balance:",
        ethers.formatEther(await ethers.provider.getBalance(deployer.address)),
        "ETH"
    );

    const BetEscrow = await ethers.getContractFactory("BetEscrow");
    const escrow = await BetEscrow.deploy();
    await escrow.waitForDeployment();

    const address = await escrow.getAddress();
    console.log("BetEscrow deployed to:", address);
    console.log("");
    console.log("Add this to your .env files:");
    console.log(`CONTRACT_ADDRESS=${address}`);
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error(err);
        process.exit(1);
    });
