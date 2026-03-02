"""
NOWPayments service for crypto deposits and withdrawals
"""
import httpx
import hmac
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.payment import CryptoPayment
from app.schemas.payment import (
    NOWPaymentsInvoiceRequest,
    NOWPaymentsPaymentRequest,
    NOWPaymentsIPNPayload,
    CryptoPaymentCreate,
    CryptoPaymentUpdate
)


class NOWPaymentsService:
    def __init__(self):
        self.api_key = settings.NOWPAYMENTS_API_KEY
        self.api_url = settings.NOWPAYMENTS_API_URL
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to NOWPayments API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.api_url}/{endpoint}",
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
                
                try:
                    return response.json()
                except Exception:
                    if not response.content or response.text.strip() == "OK":
                        return {}
                    raise Exception(f"Invalid JSON response: {response.text}")
            
            except httpx.TimeoutException:
                raise Exception("NOWPayments API timeout")
            except httpx.HTTPStatusError as e:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("message", e.response.text)
                except:
                    error_msg = e.response.text
                raise Exception(f"NOWPayments API error: {error_msg}")
            except httpx.RequestError as e:
                raise Exception(f"NOWPayments API connection error: {str(e)}")
    
    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to NOWPayments API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/{endpoint}",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                try:
                    return response.json()
                except Exception:
                    if not response.content:
                        return {}
                    raise Exception(f"Invalid JSON response: {response.text}")
            
            except httpx.TimeoutException:
                raise Exception("NOWPayments API timeout")
            except httpx.HTTPStatusError as e:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("message", e.response.text)
                except:
                    error_msg = e.response.text
                raise Exception(f"NOWPayments API error: {error_msg}")
            except httpx.RequestError as e:
                raise Exception(f"NOWPayments API connection error: {str(e)}")
    
    async def get_api_status(self) -> Dict[str, Any]:
        """Get NOWPayments API status"""
        return await self._get("status")
    
    async def get_available_currencies(self) -> List[Dict[str, Any]]:
        """Get available cryptocurrencies"""
        response = await self._get("currencies")
        return response.get("currencies", [])
    
    async def get_minimum_amount(
        self,
        currency_from: str,
        currency_to: Optional[str] = None,
        is_fixed_rate: bool = False,
        is_fee_paid_by_user: bool = False
    ) -> Dict[str, Any]:
        """Get minimum amount for transaction"""
        params = {
            "currency_from": currency_from,
            "currency_to": currency_to or currency_from,
            "is_fixed_rate": str(is_fixed_rate).lower(),
            "is_fee_paid_by_user": str(is_fee_paid_by_user).lower()
        }
        return await self._get("min-amount", params=params)
    
    async def get_estimated_price(
        self,
        amount: float,
        currency_from: str,
        currency_to: str
    ) -> Dict[str, Any]:
        """Get estimated price"""
        params = {
            "amount": amount,
            "currency_from": currency_from,
            "currency_to": currency_to
        }
        return await self._get("estimate", params=params)
    
    async def create_invoice(
        self,
        session: AsyncSession,
        invoice_data: NOWPaymentsInvoiceRequest,
        user_id: UUID,
        wallet_id: UUID
    ) -> CryptoPayment:
        """Create an invoice and save to DB"""
        payload = invoice_data.dict(exclude_none=True)
        response = await self._post("invoice", payload)
        
        # Parse created_at
        created_at_str = response.get("created_at")
        created_at = None
        if created_at_str:
            try:
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str[:-1] + '+00:00'
                created_at_aware = datetime.fromisoformat(created_at_str)
                created_at = created_at_aware.replace(tzinfo=None)
            except ValueError:
                created_at = datetime.utcnow()
        
        # Create payment record
        payment = CryptoPayment(
            user_id=user_id,
            wallet_id=wallet_id,
            payment_id=str(response.get("id")),
            invoice_id=str(response.get("id")),
            order_id=invoice_data.order_id,
            order_description=invoice_data.order_description,
            price_amount=invoice_data.price_amount,
            price_currency=invoice_data.price_currency,
            pay_currency=invoice_data.pay_currency,
            ipn_callback_url=invoice_data.ipn_callback_url,
            invoice_url=response.get("invoice_url"),
            is_fixed_rate=invoice_data.is_fixed_rate,
            is_fee_paid_by_user=invoice_data.is_fee_paid_by_user,
            payment_status="waiting",
            payment_type="deposit",
            created_at=created_at
        )
        
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        return payment
    
    async def create_payment(
        self,
        session: AsyncSession,
        payment_data: NOWPaymentsPaymentRequest,
        user_id: UUID,
        wallet_id: UUID
    ) -> CryptoPayment:
        """Create a payment and save to DB"""
        payload = payment_data.dict(exclude_none=True)
        response = await self._post("payment", payload)
        
        # Parse created_at
        created_at_str = response.get("created_at")
        created_at = None
        if created_at_str:
            try:
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str[:-1] + '+00:00'
                created_at_aware = datetime.fromisoformat(created_at_str)
                created_at = created_at_aware.replace(tzinfo=None)
            except ValueError:
                created_at = datetime.utcnow()
        
        # Create payment record
        payment = CryptoPayment(
            user_id=user_id,
            wallet_id=wallet_id,
            payment_id=str(response.get("payment_id")),
            order_id=payment_data.order_id,
            order_description=payment_data.order_description,
            price_amount=payment_data.price_amount,
            price_currency=payment_data.price_currency,
            pay_amount=Decimal(str(response.get("pay_amount"))) if response.get("pay_amount") else None,
            pay_currency=payment_data.pay_currency,
            pay_address=response.get("pay_address"),
            payin_extra_id=response.get("payin_extra_id"),
            ipn_callback_url=payment_data.ipn_callback_url,
            is_fixed_rate=payment_data.is_fixed_rate,
            is_fee_paid_by_user=payment_data.is_fee_paid_by_user,
            payment_status=response.get("payment_status", "waiting"),
            payment_type="deposit",
            created_at=created_at
        )
        
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        return payment
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status from API"""
        return await self._get(f"payment/{payment_id}")
    
    async def get_user_payments(
        self,
        session: AsyncSession,
        user_id: UUID
    ) -> List[CryptoPayment]:
        """Get all payments for a user"""
        statement = select(CryptoPayment).where(
            CryptoPayment.user_id == user_id
        ).order_by(CryptoPayment.created_at.desc())
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    async def get_payment_by_id(
        self,
        session: AsyncSession,
        payment_id: UUID
    ) -> Optional[CryptoPayment]:
        """Get payment by DB ID"""
        statement = select(CryptoPayment).where(CryptoPayment.id == payment_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()
    
    async def process_ipn_callback(
        self,
        session: AsyncSession,
        payload: NOWPaymentsIPNPayload,
        signature: str
    ) -> Optional[CryptoPayment]:
        """Process IPN callback from NOWPayments"""
        # Verify signature
        if not settings.NOWPAYMENTS_IPN_SECRET:
            raise Exception("NOWPAYMENTS_IPN_SECRET not configured")
        
        message = payload.dict(exclude_none=True)
        sorted_msg = json.dumps(message, separators=(',', ':'), sort_keys=True)
        
        digest = hmac.new(
            str(settings.NOWPAYMENTS_IPN_SECRET).encode(),
            sorted_msg.encode(),
            hashlib.sha512
        )
        calculated_signature = digest.hexdigest()
        
        if calculated_signature != signature:
            raise Exception(f"Invalid NOWPayments signature")
        
        # Find payment
        payment = None
        if payload.payment_id:
            statement = select(CryptoPayment).where(
                CryptoPayment.payment_id == str(payload.payment_id)
            )
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
        
        if not payment and payload.invoice_id:
            statement = select(CryptoPayment).where(
                CryptoPayment.invoice_id == str(payload.invoice_id)
            )
            result = await session.execute(statement)
            payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        # Update payment
        payment.payment_status = payload.payment_status
        payment.pay_address = payload.pay_address or payment.pay_address
        payment.pay_amount = payload.pay_amount or payment.pay_amount
        payment.actually_paid = payload.actually_paid
        payment.payin_extra_id = payload.payin_extra_id or payment.payin_extra_id
        payment.outcome_amount = payload.outcome_amount
        payment.outcome_currency = payload.outcome_currency
        payment.updated_at = datetime.utcnow()
        
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        return payment
    
    async def validate_address(
        self,
        address: str,
        currency: str,
        extra_id: Optional[str] = None
    ) -> bool:
        """Validate a crypto address"""
        payload = {
            "address": address,
            "currency": currency,
            "extra_id": extra_id
        }
        
        try:
            await self._post("payout/validate-address", payload)
            return True
        except:
            return False
    
    async def create_payout(
        self,
        session: AsyncSession,
        user_id: UUID,
        wallet_id: UUID,
        address: str,
        currency: str,
        amount: Decimal,
        extra_id: Optional[str] = None,
        ipn_callback_url: Optional[str] = None
    ) -> CryptoPayment:
        """Create a payout (withdrawal)"""
        withdrawals = [{
            "address": address,
            "currency": currency,
            "amount": float(amount),
            "extra_id": extra_id
        }]
        
        payload = {
            "withdrawals": withdrawals,
            "ipn_callback_url": ipn_callback_url
        }
        
        response = await self._post("payout", payload)
        
        # Create payment record
        payment = CryptoPayment(
            user_id=user_id,
            wallet_id=wallet_id,
            payout_id=str(response.get("id")),
            order_id=f"withdrawal_{user_id}_{datetime.now().timestamp()}",
            order_description="Wallet withdrawal",
            price_amount=amount,
            price_currency=currency,
            pay_amount=amount,
            pay_currency=currency,
            payout_address=address,
            payout_extra_id=extra_id,
            payment_status="waiting",
            payment_type="withdrawal",
            ipn_callback_url=ipn_callback_url
        )
        
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        return payment
    
    async def get_payout_status(self, payout_id: str) -> Dict[str, Any]:
        """Get status of a payout"""
        return await self._get(f"payout/{payout_id}")


nowpayments_service = NOWPaymentsService()
