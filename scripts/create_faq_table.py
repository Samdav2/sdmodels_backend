import asyncio
from sqlalchemy import text
from app.db.session import get_session


async def create_faq_table():
    """Create FAQ table"""
    async for session in get_session():
        try:
            # Create FAQ table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS faqs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    category VARCHAR NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    "order" INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    views INTEGER DEFAULT 0,
                    helpful_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await session.commit()
            print("✓ FAQ table created successfully")
            
            # Insert sample FAQs
            await session.execute(text("""
                INSERT INTO faqs (category, question, answer, "order") VALUES
                ('Payment', 'How do I deposit funds?', 'You can deposit funds using Paystack (NGN) or crypto payments (BTC, ETH, USDT). Go to Wallet > Deposit and choose your preferred method.', 1),
                ('Payment', 'How long does withdrawal take?', 'Paystack withdrawals are processed within 24 hours. Crypto withdrawals are processed within 1-2 hours.', 2),
                ('Payment', 'What payment methods are supported?', 'We support Paystack for NGN payments and NOWPayments for crypto (BTC, ETH, USDT, and 100+ cryptocurrencies).', 3),
                ('Technical', 'How do I upload a 3D model?', 'Go to Dashboard > Upload Model. Fill in the details, upload your files (GLB, FBX, OBJ), add images, and submit for review.', 1),
                ('Technical', 'What file formats are supported?', 'We support GLB, FBX, OBJ, BLEND, MAX, and other common 3D formats. Maximum file size is 500MB.', 2),
                ('Account', 'How do I verify my account?', 'Check your email for the verification link sent during registration. Click the link to verify your account.', 1),
                ('Account', 'How do I reset my password?', 'Click "Forgot Password" on the login page. Enter your email and follow the instructions sent to your inbox.', 2),
                ('Refund', 'What is your refund policy?', 'Refunds are available within 7 days of purchase if the model has significant issues. Contact support with details.', 1),
                ('Refund', 'How long does refund processing take?', 'Refunds are processed within 3-5 business days after approval. Funds will be returned to your wallet.', 2)
                ON CONFLICT DO NOTHING
            """))
            
            await session.commit()
            print("✓ Sample FAQs inserted")
            
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()
        
        break


if __name__ == "__main__":
    asyncio.run(create_faq_table())
