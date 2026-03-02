"""
Test Email System
Run this to verify email configuration and templates
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.email import (
    send_welcome_email,
    send_password_reset_email,
    send_model_approved_email,
    send_purchase_confirmation_email,
    send_new_sale_email,
    send_wallet_deposit_email,
    send_bounty_application_approved_email,
    send_support_ticket_created_email
)


async def test_all_emails():
    """Test all email templates"""
    
    test_email = input("Enter your email address to receive test emails: ")
    
    print("\n🧪 Testing Email System...\n")
    
    tests = [
        {
            "name": "Welcome Email",
            "func": send_welcome_email,
            "args": (test_email, "TestUser", "https://sdmodels.com/verify/test123")
        },
        {
            "name": "Password Reset",
            "func": send_password_reset_email,
            "args": (test_email, "TestUser", "https://sdmodels.com/reset/test123")
        },
        {
            "name": "Model Approved",
            "func": send_model_approved_email,
            "args": (test_email, "TestUser", "Sci-Fi Character", "https://sdmodels.com/models/123")
        },
        {
            "name": "Purchase Confirmation",
            "func": send_purchase_confirmation_email,
            "args": (
                test_email, "TestUser", "TXN123456",
                [{"title": "Model 1", "creator": "Artist1", "price": 29.99}],
                29.99, "https://sdmodels.com/downloads/TXN123456"
            )
        },
        {
            "name": "New Sale",
            "func": send_new_sale_email,
            "args": (
                test_email, "TestUser", "Sci-Fi Character",
                29.99, 2.25, 27.74, "TXN123456", "https://sdmodels.com/dashboard"
            )
        },
        {
            "name": "Wallet Deposit",
            "func": send_wallet_deposit_email,
            "args": (
                test_email, "TestUser", 100.00, "DEP123456",
                "Paystack", "2024-03-15 10:30 AM", 250.00, "https://sdmodels.com/wallet"
            )
        },
        {
            "name": "Bounty Application Approved",
            "func": send_bounty_application_approved_email,
            "args": (
                test_email, "TestUser", "Create 3D Character",
                500.00, "2024-03-22", "PosterName", "https://sdmodels.com/bounties/123"
            )
        },
        {
            "name": "Support Ticket Created",
            "func": send_support_ticket_created_email,
            "args": (
                test_email, "TestUser", "TICK123",
                "Payment Issue", "high", "open", "https://sdmodels.com/support/TICK123"
            )
        }
    ]
    
    results = []
    
    for test in tests:
        try:
            print(f"📧 Sending {test['name']}...", end=" ")
            result = await test['func'](*test['args'])
            if result:
                print("✅ Success")
                results.append((test['name'], True))
            else:
                print("❌ Failed")
                results.append((test['name'], False))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((test['name'], False))
    
    print("\n" + "="*50)
    print("📊 Test Results Summary")
    print("="*50)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print("="*50)
    print(f"Success Rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 All emails sent successfully!")
        print(f"📬 Check your inbox at {test_email}")
    else:
        print("\n⚠️  Some emails failed. Check your SMTP configuration in .env")


async def test_single_email():
    """Test a single email"""
    test_email = input("Enter your email address: ")
    
    print("\n📧 Sending test welcome email...")
    
    try:
        result = await send_welcome_email(
            user_email=test_email,
            username="TestUser",
            verify_url="https://sdmodels.com/verify/test123"
        )
        
        if result:
            print("✅ Email sent successfully!")
            print(f"📬 Check your inbox at {test_email}")
        else:
            print("❌ Failed to send email")
            print("Check your SMTP configuration in .env")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check SMTP credentials in .env")
        print("2. Gmail users: Use App Password, not regular password")
        print("3. Verify SMTP_HOST and SMTP_PORT are correct")


async def main():
    print("="*50)
    print("SDModels Email System Test")
    print("="*50)
    print("\nOptions:")
    print("1. Test single email (quick)")
    print("2. Test all email templates (comprehensive)")
    
    choice = input("\nEnter your choice (1 or 2): ")
    
    if choice == "1":
        await test_single_email()
    elif choice == "2":
        await test_all_emails()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
