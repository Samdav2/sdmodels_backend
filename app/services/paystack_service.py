"""
Paystack payment service for fiat deposits and withdrawals
"""
import hmac
import hashlib
import httpx
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.config import settings
from app.models.payment import Payment
from app.schemas.payment import (
    PaystackInitializeResponse,
    PaystackVerifyResponse,
    PaystackRecipientRequest,
    PaystackTransferRequest
)


class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
    
    async def initialize_transaction(
        self,
        session: AsyncSession,
        user_id: UUID,
        wallet_id: UUID,
        email: str,
        amount: Decimal,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaystackInitializeResponse:
        """Initialize a Paystack payment transaction"""
        url = f"{self.BASE_URL}/transaction/initialize"
        
        # Paystack amount is in kobo (smallest currency unit)
        amount_kobo = int(amount * 100)
        
        # Prepare metadata
        payment_metadata = {
            "user_id": str(user_id),
            "wallet_id": str(wallet_id),
            "payment_type": "deposit"
        }
        if metadata:
            payment_metadata.update(metadata)
        
        payload = {
            "email": email,
            "amount": amount_kobo,
            "callback_url": callback_url,
            "metadata": payment_metadata
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Paystack initialization failed: {response.text}"
                )
            
            data = response.json()["data"]
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                wallet_id=wallet_id,
                reference=data["reference"],
                amount=amount,
                currency="NGN",
                status="pending",
                payment_type="deposit",
                payment_metadata=json.dumps(payment_metadata)
            )
            
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            
            return PaystackInitializeResponse(**data)
    
    async def verify_transaction(
        self,
        session: AsyncSession,
        reference: str
    ) -> PaystackVerifyResponse:
        """Verify a Paystack transaction"""
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Paystack verification failed: {response.text}"
                )
            
            data = response.json()["data"]
            
            # Update payment record
            statement = select(Payment).where(Payment.reference == reference)
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
            
            if payment:
                # Verify amount matches
                expected_amount_kobo = int(payment.amount * 100)
                if data["amount"] != expected_amount_kobo:
                    print(f"Warning: Payment amount mismatch. Expected: {expected_amount_kobo}, Got: {data['amount']}")
                    return PaystackVerifyResponse(
                        status="failed",
                        message="Payment amount mismatch",
                        data=data
                    )
                
                if data["status"] == "success":
                    payment.status = "success"
                    # Parse paid_at and convert to naive datetime (remove timezone info)
                    if data.get("paid_at"):
                        paid_at_aware = datetime.fromisoformat(
                            data["paid_at"].replace("Z", "+00:00")
                        )
                        payment.paid_at = paid_at_aware.replace(tzinfo=None)
                    else:
                        payment.paid_at = None
                    payment.channel = data.get("channel")
                    payment.updated_at = datetime.utcnow()
                    
                    session.add(payment)
                    await session.commit()
                    await session.refresh(payment)
            
            return PaystackVerifyResponse(
                status=data["status"],
                message=response.json()["message"],
                data=data
            )
    
    async def create_transfer_recipient(
        self,
        recipient_data: PaystackRecipientRequest
    ) -> Dict[str, Any]:
        """Create a transfer recipient for withdrawals"""
        url = f"{self.BASE_URL}/transferrecipient"
        
        payload = recipient_data.dict()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create recipient: {response.text}"
                )
            
            return response.json()["data"]
    
    async def initiate_transfer(
        self,
        session: AsyncSession,
        user_id: UUID,
        wallet_id: UUID,
        amount: Decimal,
        recipient_code: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate a transfer (withdrawal)"""
        url = f"{self.BASE_URL}/transfer"
        
        # Amount in kobo
        amount_kobo = int(amount * 100)
        
        payload = {
            "source": "balance",
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reason": reason or "Withdrawal from wallet"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transfer failed: {response.text}"
                )
            
            data = response.json()["data"]
            
            # Create payment record for withdrawal
            payment = Payment(
                user_id=user_id,
                wallet_id=wallet_id,
                reference=data["reference"],
                amount=amount,
                currency="NGN",
                status="pending",
                payment_type="withdrawal",
                payment_metadata=json.dumps({
                    "recipient_code": recipient_code,
                    "transfer_code": data.get("transfer_code")
                })
            )
            
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            
            return data
    
    async def verify_transfer(
        self,
        session: AsyncSession,
        reference: str
    ) -> Dict[str, Any]:
        """Verify a transfer status"""
        url = f"{self.BASE_URL}/transfer/verify/{reference}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transfer verification failed: {response.text}"
                )
            
            data = response.json()["data"]
            
            # Update payment record
            statement = select(Payment).where(Payment.reference == reference)
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
            
            if payment:
                if data["status"] == "success":
                    payment.status = "success"
                elif data["status"] == "failed":
                    payment.status = "failed"
                
                payment.updated_at = datetime.utcnow()
                session.add(payment)
                await session.commit()
            
            return data
    
    async def list_banks(self, country: str = "nigeria") -> list:
        """List available banks"""
        url = f"{self.BASE_URL}/bank"
        
        params = {"country": country}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch banks: {response.text}"
                )
            
            return response.json()["data"]
    
    async def resolve_account_number(
        self,
        account_number: str,
        bank_code: str
    ) -> Dict[str, Any]:
        """Resolve account number to get account name"""
        url = f"{self.BASE_URL}/bank/resolve"
        
        params = {
            "account_number": account_number,
            "bank_code": bank_code
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to resolve account: {response.text}"
                )
            
            return response.json()["data"]
    
    async def handle_webhook(
        self,
        session: AsyncSession,
        request_body: bytes,
        signature: str
    ) -> Dict[str, str]:
        """Handle Paystack webhook"""
        # Verify signature
        hash_value = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            request_body,
            hashlib.sha512
        ).hexdigest()
        
        if hash_value != signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
        
        event = json.loads(request_body)
        
        if event["event"] == "charge.success":
            data = event["data"]
            reference = data["reference"]
            
            statement = select(Payment).where(Payment.reference == reference)
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
            
            if payment and payment.status != "success":
                payment.status = "success"
                payment.paid_at = datetime.fromisoformat(
                    data["paid_at"].replace("Z", "+00:00")
                ) if data.get("paid_at") else None
                payment.channel = data.get("channel")
                payment.updated_at = datetime.utcnow()
                
                session.add(payment)
                await session.commit()
        
        elif event["event"] == "transfer.success":
            data = event["data"]
            reference = data["reference"]
            
            statement = select(Payment).where(Payment.reference == reference)
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = "success"
                payment.updated_at = datetime.utcnow()
                
                session.add(payment)
                await session.commit()
        
        elif event["event"] == "transfer.failed":
            data = event["data"]
            reference = data["reference"]
            
            statement = select(Payment).where(Payment.reference == reference)
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = "failed"
                payment.updated_at = datetime.utcnow()
                
                session.add(payment)
                await session.commit()
        
        return {"status": "success"}


paystack_service = PaystackService()
