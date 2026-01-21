"""
Bitcoin service for BTC address and xpub balance fetching.
"""

import re
import logging
from typing import Dict, Optional

from akitafolio.http_client import HTTPClient
from akitafolio.cache import cached, balance_cache
from akitafolio.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BitcoinService:
    """Service for Bitcoin balance fetching."""
    
    BLOCKCHAIN_INFO_URL = "https://blockchain.info"
    
    # Address patterns
    BTC_LEGACY_PATTERN = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$')
    BTC_SEGWIT_PATTERN = re.compile(r'^bc1[a-z0-9]{39,59}$', re.IGNORECASE)
    XPUB_PREFIXES = ('xpub', 'ypub', 'zpub', 'tpub', 'upub', 'vpub')
    
    @classmethod
    def is_valid_btc_address(cls, address: str) -> bool:
        """Validate Bitcoin address format."""
        if not address:
            return False
        return bool(
            cls.BTC_LEGACY_PATTERN.match(address) or
            cls.BTC_SEGWIT_PATTERN.match(address)
        )
    
    @classmethod
    def is_valid_xpub(cls, xpub: str) -> bool:
        """Validate xpub/ypub/zpub format."""
        if not xpub:
            return False
        if not any(xpub.startswith(prefix) for prefix in cls.XPUB_PREFIXES):
            return False
        return 100 <= len(xpub) <= 120
    
    @classmethod
    @cached(cache=balance_cache, ttl=60.0, key_prefix="btc_balance")
    async def get_address_balance(cls, address: str) -> Dict:
        """Fetch Bitcoin balance for a single address."""
        if not cls.is_valid_btc_address(address):
            return {"error": "Invalid Bitcoin address", "address": address}
        
        try:
            url = f"{cls.BLOCKCHAIN_INFO_URL}/q/addressbalance/{address}"
            response_text = await HTTPClient.get_text(url, timeout=10)
            
            balance_satoshi = int(response_text)
            balance_btc = balance_satoshi / 100_000_000
            
            return {
                "success": True,
                "address": address,
                "balance": balance_btc,
                "currency": "BTC"
            }
        except Exception as e:
            logger.error(f"Error fetching Bitcoin balance for {address}: {e}")
            return {
                "error": f"Failed to fetch balance: {str(e)}",
                "address": address
            }
    
    @classmethod
    @cached(cache=balance_cache, ttl=120.0, key_prefix="xpub_balance")
    async def get_xpub_balance(cls, xpub: str) -> Dict:
        """Fetch Bitcoin HD wallet balance using xpub."""
        if not cls.is_valid_xpub(xpub):
            return {"error": "Invalid xpub format", "xpub": xpub}
        
        try:
            url = f"{cls.BLOCKCHAIN_INFO_URL}/balance?active={xpub}"
            data = await HTTPClient.get(url, timeout=20)
            
            if xpub not in data:
                return {"error": "xpub not found in response", "xpub": xpub}
            
            xpub_data = data[xpub]
            
            return {
                "success": True,
                "xpub": xpub,
                "balance": xpub_data.get('final_balance', 0) / 100_000_000,
                "total_received": xpub_data.get('total_received', 0) / 100_000_000,
                "total_sent": xpub_data.get('total_sent', 0) / 100_000_000,
                "transaction_count": xpub_data.get('n_tx', 0),
                "currency": "BTC"
            }
        except Exception as e:
            logger.error(f"Error fetching xpub balance: {e}")
            return {
                "error": f"Failed to fetch xpub balance: {str(e)}",
                "xpub": xpub
            }
    
    @classmethod
    async def get_total_btc_balance(
        cls,
        addresses: list,
        xpubs: list
    ) -> Dict:
        """Get total BTC balance from addresses and xpubs."""
        import asyncio
        
        total_single = 0.0
        total_xpub = 0.0
        errors = []
        
        # Fetch address balances
        if addresses:
            tasks = [cls.get_address_balance(addr) for addr in addresses]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result.get('success'):
                    total_single += result.get('balance', 0)
                elif result.get('error'):
                    errors.append(result['error'])
        
        # Fetch xpub balances
        if xpubs:
            tasks = [cls.get_xpub_balance(xpub) for xpub in xpubs]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result.get('success'):
                    total_xpub += result.get('balance', 0)
                elif result.get('error'):
                    errors.append(result['error'])
        
        return {
            "total_single": total_single,
            "total_xpub": total_xpub,
            "total_combined": total_single + total_xpub,
            "errors": errors if errors else None
        }
