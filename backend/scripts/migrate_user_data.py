#!/usr/bin/env python3
"""
Data Migration Script: Migrate existing data to authenticated user

This script:
1. Creates the target user account (oliveren88@gmail.com)
2. Migrates all existing data from demo@example.com to the new user
3. Updates all related records (institutions, goals, income sources, etc.)

Run this script from the backend directory:
    cd backend && python -m scripts.migrate_user_data
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models import User, Institution, UserProfile, Goal, IncomeSource, Insight, TransferRule
from app.models.models import generate_uuid

# Target user credentials
TARGET_EMAIL = "oliveren88@gmail.com"
TARGET_PASSWORD = "Ol@rjl88"
TARGET_NAME = "Oliver"


def migrate_user_data():
    """Run the migration."""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("FinTrack Data Migration Script")
        print("=" * 60)

        # Step 1: Check if target user already exists
        target_user = db.query(User).filter(User.email == TARGET_EMAIL).first()

        if target_user:
            print(f"\n[INFO] User {TARGET_EMAIL} already exists with ID: {target_user.id}")
            # Update password if not set
            if not target_user.hashed_password:
                target_user.hashed_password = get_password_hash(TARGET_PASSWORD)
                target_user.is_active = True
                print(f"[INFO] Updated password for existing user")
        else:
            # Create new user
            target_user = User(
                id=generate_uuid(),
                email=TARGET_EMAIL,
                name=TARGET_NAME,
                hashed_password=get_password_hash(TARGET_PASSWORD),
                is_active=True
            )
            db.add(target_user)
            db.commit()
            db.refresh(target_user)
            print(f"\n[SUCCESS] Created new user {TARGET_EMAIL}")
            print(f"          User ID: {target_user.id}")

        # Step 2: Find existing demo user(s) to migrate from
        demo_users = db.query(User).filter(
            User.id != target_user.id
        ).all()

        if not demo_users:
            print("\n[INFO] No other users found to migrate from")
        else:
            print(f"\n[INFO] Found {len(demo_users)} other users to migrate from")

        for demo_user in demo_users:
            print(f"\n--- Migrating data from user: {demo_user.email} (ID: {demo_user.id}) ---")

            # Migrate institutions (accounts and transactions follow via FK)
            institutions = db.query(Institution).filter(
                Institution.user_id == demo_user.id
            ).all()

            for inst in institutions:
                inst.user_id = target_user.id
                print(f"  [OK] Migrated institution: {inst.name}")

            if not institutions:
                print(f"  [SKIP] No institutions to migrate")

            # Migrate goals
            goals = db.query(Goal).filter(Goal.user_id == demo_user.id).all()
            for goal in goals:
                goal.user_id = target_user.id
            if goals:
                print(f"  [OK] Migrated {len(goals)} goals")

            # Migrate income sources
            income_sources = db.query(IncomeSource).filter(
                IncomeSource.user_id == demo_user.id
            ).all()
            for source in income_sources:
                source.user_id = target_user.id
            if income_sources:
                print(f"  [OK] Migrated {len(income_sources)} income sources")

            # Migrate insights
            insights = db.query(Insight).filter(Insight.user_id == demo_user.id).all()
            for insight in insights:
                insight.user_id = target_user.id
            if insights:
                print(f"  [OK] Migrated {len(insights)} insights")

            # Migrate user profile
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == demo_user.id
            ).first()
            if profile:
                # Check if target user already has a profile
                existing_profile = db.query(UserProfile).filter(
                    UserProfile.user_id == target_user.id
                ).first()
                if existing_profile:
                    # Delete the old one, keep the new one
                    db.delete(profile)
                    print(f"  [SKIP] Target user already has a profile")
                else:
                    profile.user_id = target_user.id
                    print(f"  [OK] Migrated user profile")

            # Migrate transfer rules
            rules = db.query(TransferRule).filter(
                TransferRule.user_id == demo_user.id
            ).all()
            for rule in rules:
                rule.user_id = target_user.id
            if rules:
                print(f"  [OK] Migrated {len(rules)} transfer rules")

            # Delete the old demo user (if it has no remaining data)
            remaining_institutions = db.query(Institution).filter(
                Institution.user_id == demo_user.id
            ).count()

            if remaining_institutions == 0:
                db.delete(demo_user)
                print(f"  [OK] Deleted demo user {demo_user.email}")
            else:
                print(f"  [WARN] Demo user still has {remaining_institutions} institutions")

        db.commit()
        print("\n" + "=" * 60)
        print("[SUCCESS] Migration completed!")
        print("=" * 60)
        print(f"\nYou can now log in with:")
        print(f"  Email:    {TARGET_EMAIL}")
        print(f"  Password: {TARGET_PASSWORD}")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_user_data()
