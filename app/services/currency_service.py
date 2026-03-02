"""
Currency conversion service
Converts between different currencies using exchange rates
"""
from decimal import Decimal
import httpx
from typing import Optional
from app.core.config import settings


class CurrencyService:
    """Service for currency conversion"""
    
    # Fallback exchange rates (updated periodically)
    FALLBACK_RATES = {
        "NGN_TO_USD": Decimal("0.00065"),  # 1 NGN = 0.00065 USD (approx 1540 NGN = 1 USD)
        "USD_TO_NGN": Decimal("1540.00"),   # 1 USD = 1540 NGN
    }
    
    def __init__(self):
        self.api_key = getattr(settings, "EXCHANGE_RATE_API_KEY", None)
        self.use_live_rates = bool(self.api_key)
    
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate from one currency to another
        
        Args:
            from_currency: Source currency code (e.g., "NGN")
            to_currency: Target currency code (e.g., "USD")
        
        Returns:
            Exchange rate as Decimal
        """
        if from_currency == to_currency:
            return Decimal("1.0")
        
        # Try to get live rate if API key is configured
        if self.use_live_rates:
            try:
                rate = await self._fetch_live_rate(from_currency, to_currency)
                if rate:
                    return rate
            except Exception as e:
                print(f"Failed to fetch live exchange rate: {e}")
        
        # Fall back to hardcoded rates
        return self._get_fallback_rate(from_currency, to_currency)
    
    async def _fetch_live_rate(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Fetch live exchange rate from API
        Using exchangerate-api.com (free tier available)
        """
        if not self.api_key:
            return None
        
        url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/pair/{from_currency}/{to_currency}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rate = data.get("conversion_rate")
                    return Decimal(str(rate))
        
        return None
    
    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get fallback exchange rate from hardcoded values"""
        rate_key = f"{from_currency}_TO_{to_currency}"
        
        if rate_key in self.FALLBACK_RATES:
            return self.FALLBACK_RATES[rate_key]
        
        # Try reverse rate
        reverse_key = f"{to_currency}_TO_{from_currency}"
        if reverse_key in self.FALLBACK_RATES:
            return Decimal("1.0") / self.FALLBACK_RATES[reverse_key]
        
        # Default to 1:1 if no rate found
        print(f"Warning: No exchange rate found for {from_currency} to {to_currency}, using 1:1")
        return Decimal("1.0")
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
        
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
        
        rate = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate
        
        # Round to 2 decimal places
        return converted.quantize(Decimal("0.01"))
    
    async def ngn_to_usd(self, amount_ngn: Decimal) -> Decimal:
        """Convert Nigerian Naira to US Dollars"""
        return await self.convert(amount_ngn, "NGN", "USD")
    
    async def usd_to_ngn(self, amount_usd: Decimal) -> Decimal:
        """Convert US Dollars to Nigerian Naira"""
        return await self.convert(amount_usd, "USD", "NGN")


# Singleton instance
currency_service = CurrencyService()
