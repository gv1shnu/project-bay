"""
Seed script to populate the database with sample bets for showcase purposes.
Run this script to add random bets to the database.

Usage:
    python seed_data.py
"""

import random
from app.database import SessionLocal, engine
from app.models import Base, User, Bet, BetStatus
from app.auth import get_password_hash, get_user_by_username

# Sample bet descriptions for showcase
SAMPLE_BET_DESCRIPTIONS = [
    "I commit to running 5 kilometers every single day for the next 30 days. No excuses, rain or shine!",
    "Complete digital detox from all social media platforms including Instagram, Twitter, Facebook, and TikTok for 2 weeks.",
    "I will write at least 1000 words every day on my novel. Consistency is key to finishing this project.",
    "Building a meditation habit with 20 minutes of mindfulness practice every morning before work.",
    "Dedicating one hour every day to learning Spanish through apps, videos, and conversation practice.",
    "I will read one book per week for the next month. No skipping, no excuses!",
    "Going to the gym 5 times a week for the next 6 weeks. Tracking all workouts.",
    "No junk food or fast food for 30 days. Only home-cooked meals and healthy snacks.",
    "I will wake up at 6 AM every weekday for the next month. No snooze button!",
    "Complete a coding project by building a full-stack application in 2 weeks.",
    "I will practice guitar for 30 minutes daily for the next 21 days.",
    "No alcohol for the entire month. Staying completely sober.",
    "I will call or video chat with a family member or friend every day for 2 weeks.",
    "Learning to cook 10 new recipes this month. Documenting each one with photos.",
    "I will save $500 this month by cutting unnecessary expenses.",
    "Complete a 10K run by the end of the month. Training starts now!",
    "I will journal every evening for the next 30 days, reflecting on the day.",
    "No online shopping for non-essentials for the entire month.",
    "I will complete an online course and get certified by the end of the month.",
    "Practice yoga or stretching for 20 minutes every morning for 30 days.",
]

# Sample usernames
SAMPLE_USERNAMES = [
    "fitness_fanatic",
    "bookworm_reader",
    "code_master",
    "yoga_enthusiast",
    "music_lover",
    "health_warrior",
    "creative_writer",
    "adventure_seeker",
    "mindful_meditator",
    "goal_crusher",
]


def create_sample_users(db):
    """Create sample users if they don't exist"""
    users = []
    raw_password = "password123"

    # Ensure password is <= 72 bytes for bcrypt
    password_bytes = raw_password.encode("utf-8")[:72]
    password = password_bytes.decode("utf-8")

    # Hash password once for all users
    hashed_password = get_password_hash(password)

    for username in SAMPLE_USERNAMES:
        existing_user = get_user_by_username(db, username)
        if not existing_user:
            email = f"{username}@example.com"
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                points=100.0
            )
            db.add(user)
            users.append(user)
            print(f"Created user: {username}")
        else:
            users.append(existing_user)
            print(f"User already exists: {username}")

    db.commit()
    return users


def create_sample_bets(db, users):
    """Create sample bets for showcase"""
    if not users:
        print("No users available to create bets")
        return
    
    # Check if bets already exist
    existing_bets = db.query(Bet).count()
    if existing_bets > 0:
        print(f"Database already has {existing_bets} bets. Skipping bet creation.")
        print("To recreate bets, delete the existing bets first.")
        return
    
    bet_count = 0
    for i, description in enumerate(SAMPLE_BET_DESCRIPTIONS):
        # Randomly assign to a user
        user = random.choice(users)
        
        # Random bet amount between 5 and 50 points
        amount = round(random.uniform(5.0, 50.0), 2)
        
        # Random status (mostly pending for showcase, some won/lost)
        status_weights = [0.7, 0.15, 0.1, 0.05]  # 70% pending, 15% won, 10% lost, 5% cancelled
        status = random.choices(
            [BetStatus.PENDING, BetStatus.WON, BetStatus.LOST, BetStatus.CANCELLED],
            weights=status_weights
        )[0]
        
        bet = Bet(
            user_id=user.id,
            amount=amount,
            description=description,
            status=status
        )
        db.add(bet)
        bet_count += 1
    
    db.commit()
    print(f"Created {bet_count} sample bets!")
    print(f"Bets are distributed among {len(users)} users.")


def main():
    """Main function to seed the database"""
    print("Starting database seeding...")
    print("-" * 50)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create sample users
        print("\n1. Creating sample users...")
        create_sample_users(db)
        
        # Get all users (including newly created ones)
        users = db.query(User).all()
        
        # Create sample bets
        print("\n2. Creating sample bets...")
        create_sample_bets(db, users)
        
        print("\n" + "-" * 50)
        print("Database seeding completed!")
        print("\nSample users created with default password: 'password123'")
        print("You can login with any of the created usernames.")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

