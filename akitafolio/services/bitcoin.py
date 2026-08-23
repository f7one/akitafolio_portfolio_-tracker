"""
Bitcoin service for BTC address and xpub balance fetching.
Includes xpub/ypub/zpub conversion for SegWit wallet support.
Supports BIP-44, BIP-49, and BIP-84 address derivation from xpub.
"""

import hashlib
import logging
import re
from typing import Dict, List, Optional, Tuple

from akitafolio.cache import balance_cache, cached
from akitafolio.http_client import HTTPClient

logger = logging.getLogger(__name__)

# Try to import hdwallet for address derivation
try:
    from hdwallet import HDWallet
    from hdwallet.symbols import BTC

    HDWALLET_AVAILABLE = True
except ImportError:
    HDWALLET_AVAILABLE = False
    logger.warning("hdwallet not installed - xpub address derivation disabled")


# Base58 alphabet used by Bitcoin
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# Extended public key version bytes (mainnet)
XPUB_VERSIONS = {
    "xpub": bytes.fromhex("0488B21E"),  # BIP-44 Legacy (P2PKH)
    "ypub": bytes.fromhex("049D7CB2"),  # BIP-49 SegWit wrapped (P2SH-P2WPKH)
    "zpub": bytes.fromhex("04B24746"),  # BIP-84 Native SegWit (P2WPKH)
    # Testnet versions
    "tpub": bytes.fromhex("043587CF"),
    "upub": bytes.fromhex("044A5262"),
    "vpub": bytes.fromhex("045F1CF6"),
}


def base58_decode(s: str) -> bytes:
    """Decode a Base58Check encoded string to bytes."""
    num = 0
    for char in s:
        num = num * 58 + BASE58_ALPHABET.index(char)

    # Convert to bytes
    result = []
    while num > 0:
        result.append(num % 256)
        num //= 256
    result.reverse()

    # Add leading zeros for leading '1's in input
    leading_ones = len(s) - len(s.lstrip("1"))
    return bytes([0] * leading_ones + result)


def base58_encode(data: bytes) -> str:
    """Encode bytes to Base58Check string."""
    num = int.from_bytes(data, "big")

    result = []
    while num > 0:
        num, remainder = divmod(num, 58)
        result.append(BASE58_ALPHABET[remainder])

    # Add leading '1's for leading zero bytes
    leading_zeros = len(data) - len(data.lstrip(b"\x00"))

    return "1" * leading_zeros + "".join(reversed(result))


def convert_xpub(xpub: str, target_prefix: str) -> Optional[str]:
    """
    Convert an extended public key to a different format.

    Converts between xpub/ypub/zpub by replacing the version bytes.
    The underlying key data remains the same - only the prefix changes,
    which tells wallets how to derive addresses.

    Args:
        xpub: The source extended public key (xpub, ypub, or zpub)
        target_prefix: The target format ('xpub', 'ypub', or 'zpub')

    Returns:
        The converted key, or None if conversion fails
    """
    if target_prefix not in XPUB_VERSIONS:
        return None

    try:
        # Decode the original key
        decoded = base58_decode(xpub)

        # Verify checksum (last 4 bytes)
        payload = decoded[:-4]
        checksum = decoded[-4:]

        expected_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        if checksum != expected_checksum:
            logger.warning("Invalid xpub checksum")
            return None

        # Replace version bytes (first 4 bytes) with target version
        new_payload = XPUB_VERSIONS[target_prefix] + payload[4:]

        # Calculate new checksum
        new_checksum = hashlib.sha256(hashlib.sha256(new_payload).digest()).digest()[:4]

        # Encode with new checksum
        return base58_encode(new_payload + new_checksum)

    except Exception as e:
        logger.error(f"Failed to convert xpub to {target_prefix}: {e}")
        return None


def get_xpub_variants(xpub: str) -> List[Tuple[str, str]]:
    """
    Get all format variants of an extended public key.

    Returns a list of (prefix, converted_key) tuples to try.
    Prioritizes the format most likely to have funds based on the input.
    """
    variants = []

    # Detect current prefix
    current_prefix = None
    for prefix in XPUB_VERSIONS:
        if xpub.startswith(prefix):
            current_prefix = prefix
            break

    if not current_prefix:
        return [(None, xpub)]

    # Add the original first
    variants.append((current_prefix, xpub))

    # For xpub input (likely from Ledger), prioritize zpub (native segwit) and ypub
    if current_prefix == "xpub":
        # Try zpub first (most common for modern wallets)
        zpub = convert_xpub(xpub, "zpub")
        if zpub:
            variants.append(("zpub", zpub))

        # Then try ypub (wrapped segwit)
        ypub = convert_xpub(xpub, "ypub")
        if ypub:
            variants.append(("ypub", ypub))

    # For ypub/zpub, also try the others
    elif current_prefix in ("ypub", "zpub"):
        for target in ["xpub", "ypub", "zpub"]:
            if target != current_prefix:
                converted = convert_xpub(xpub, target)
                if converted:
                    variants.append((target, converted))

    return variants


def derive_addresses_from_xpub(
    xpub: str, address_type: str = "p2wpkh_in_p2sh", count: int = 20
) -> List[str]:
    """
    Derive addresses from an extended public key.

    Args:
        xpub: Extended public key (xpub/ypub/zpub)
        address_type: 'p2pkh' (legacy), 'p2wpkh_in_p2sh' (nested SegWit), 'p2wpkh' (native SegWit)
        count: Number of addresses to derive (for both receive and change)

    Returns:
        List of derived addresses
    """
    if not HDWALLET_AVAILABLE:
        logger.warning("hdwallet not available for address derivation")
        return []

    try:
        # Normalize xpub - convert to standard xpub format for hdwallet
        normalized_xpub = xpub
        for prefix in ["ypub", "zpub"]:
            if xpub.startswith(prefix):
                converted = convert_xpub(xpub, "xpub")
                if converted:
                    normalized_xpub = converted
                break

        addresses = []

        # Derive receive addresses (external chain, index 0)
        for i in range(count):
            hdwallet = HDWallet(symbol=BTC)
            hdwallet.from_xpublic_key(xpublic_key=normalized_xpub)
            # Derive m/0/i (receive addresses)
            hdwallet.from_index(0)  # External chain
            hdwallet.from_index(i)  # Address index

            if address_type == "p2wpkh_in_p2sh":
                # P2SH-P2WPKH (Nested SegWit, starts with 3) - BIP-49
                addr = hdwallet.p2wpkh_in_p2sh_address()
            elif address_type == "p2wpkh":
                # Native SegWit (starts with bc1) - BIP-84
                addr = hdwallet.p2wpkh_address()
            else:
                # Legacy P2PKH (starts with 1) - BIP-44
                addr = hdwallet.p2pkh_address()

            if addr:
                addresses.append(addr)

        # Also derive change addresses (internal chain, index 1)
        for i in range(count // 2):  # Fewer change addresses
            hdwallet = HDWallet(symbol=BTC)
            hdwallet.from_xpublic_key(xpublic_key=normalized_xpub)
            # Derive m/1/i (change addresses)
            hdwallet.from_index(1)  # Internal chain (change)
            hdwallet.from_index(i)  # Address index

            if address_type == "p2wpkh_in_p2sh":
                addr = hdwallet.p2wpkh_in_p2sh_address()
            elif address_type == "p2wpkh":
                addr = hdwallet.p2wpkh_address()
            else:
                addr = hdwallet.p2pkh_address()

            if addr:
                addresses.append(addr)

        logger.info(f"Derived {len(addresses)} {address_type} addresses from xpub")
        return addresses

    except Exception as e:
        logger.error(f"Failed to derive addresses from xpub: {e}")
        return []


class BitcoinService:
    """Service for Bitcoin balance fetching."""

    BLOCKCHAIN_INFO_URL = "https://blockchain.info"
    BLOCKCHAIN_COM_API = "https://api.blockchain.info/haskoin-store/btc"

    # Address patterns
    BTC_LEGACY_PATTERN = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
    BTC_SEGWIT_PATTERN = re.compile(r"^bc1[a-z0-9]{39,59}$", re.IGNORECASE)
    XPUB_PREFIXES = ("xpub", "ypub", "zpub", "tpub", "upub", "vpub")

    @classmethod
    def is_valid_btc_address(cls, address: str) -> bool:
        """Validate Bitcoin address format."""
        if not address:
            return False
        return bool(cls.BTC_LEGACY_PATTERN.match(address) or cls.BTC_SEGWIT_PATTERN.match(address))

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

            return {"success": True, "address": address, "balance": balance_btc, "currency": "BTC"}
        except Exception as e:
            logger.error(f"Error fetching Bitcoin balance for {address}: {e}")
            return {"error": f"Failed to fetch balance: {str(e)}", "address": address}

    @classmethod
    async def _fetch_derived_addresses_balance(cls, xpub: str) -> Dict:
        """
        Derive addresses from xpub and fetch their balances individually.
        Tries P2WPKH-in-P2SH (Nested SegWit, "3" addresses) which is what Ledger uses for xpub.
        """
        if not HDWALLET_AVAILABLE:
            return {"error": "hdwallet not available", "balance": 0}

        try:
            # Try different address types - BIP-49 nested SegWit first (most common for Ledger)
            address_types = [
                ("p2wpkh_in_p2sh", "Nested SegWit (3...)"),
                ("p2wpkh", "Native SegWit (bc1...)"),
                ("p2pkh", "Legacy (1...)"),
            ]

            best_result = None
            best_balance = 0

            for addr_type, addr_desc in address_types:
                logger.info(f"Deriving {addr_desc} addresses from xpub...")
                addresses = derive_addresses_from_xpub(xpub, address_type=addr_type, count=20)

                if not addresses:
                    continue

                # Batch query addresses using multiaddr
                addresses_param = "|".join(addresses[:50])  # API limit
                url = f"{cls.BLOCKCHAIN_INFO_URL}/balance?active={addresses_param}"

                try:
                    data = await HTTPClient.get(url, timeout=30)

                    total_balance = 0
                    total_received = 0
                    total_tx = 0
                    addresses_with_balance = []

                    for addr, info in data.items():
                        balance = info.get("final_balance", 0)
                        total_balance += balance
                        total_received += info.get("total_received", 0)
                        total_tx += info.get("n_tx", 0)
                        if balance > 0:
                            addresses_with_balance.append(addr)

                    balance_btc = total_balance / 100_000_000

                    if balance_btc > best_balance:
                        best_balance = balance_btc
                        best_result = {
                            "success": True,
                            "key": xpub,
                            "balance": balance_btc,
                            "total_received": total_received / 100_000_000,
                            "total_sent": (total_received - total_balance) / 100_000_000,
                            "transaction_count": total_tx,
                            "source": f"derived_{addr_type}",
                            "addresses_with_balance": addresses_with_balance[:5],  # Show first 5
                        }

                    if balance_btc > 0:
                        logger.info(f"Found {balance_btc} BTC via {addr_desc}")
                        return best_result

                except Exception as e:
                    logger.warning(f"Failed to fetch {addr_desc} addresses: {e}")
                    continue

            if best_result:
                return best_result

            return {"error": "No balance found in derived addresses", "balance": 0}

        except Exception as e:
            logger.error(f"Error in derived address balance fetch: {e}")
            return {"error": str(e), "balance": 0}

    @classmethod
    async def _fetch_xpub_via_haskoin(cls, key: str) -> Dict:
        """
        Fetch balance using Blockchain.com's Haskoin API.
        This API properly handles all xpub derivation paths including BIP-49.
        """
        try:
            # Haskoin API endpoint for xpub balance
            url = f"{cls.BLOCKCHAIN_COM_API}/xpub/{key}/balances"
            data = await HTTPClient.get(url, timeout=30)

            # Response is a list of address balances
            if isinstance(data, list):
                total_confirmed = 0
                total_unconfirmed = 0
                total_received = 0
                tx_count = 0

                for addr_info in data:
                    total_confirmed += addr_info.get("confirmed", 0)
                    total_unconfirmed += addr_info.get("unconfirmed", 0)
                    total_received += addr_info.get("received", 0)
                    tx_count += addr_info.get("txs", 0)

                balance = total_confirmed + total_unconfirmed

                return {
                    "success": True,
                    "key": key,
                    "balance": balance / 100_000_000,
                    "total_received": total_received / 100_000_000,
                    "total_sent": (total_received - balance) / 100_000_000,
                    "transaction_count": tx_count,
                    "source": "haskoin",
                }
            else:
                logger.warning(f"Unexpected Haskoin response format: {type(data)}")
                return {"error": "Unexpected response format", "key": key, "balance": 0}

        except Exception as e:
            logger.warning(f"Haskoin API failed for {key[:20]}...: {e}")
            return {"error": str(e), "key": key, "balance": 0}

    @classmethod
    async def _fetch_xpub_via_multiaddr(cls, key: str) -> Dict:
        """
        Fetch balance using multiaddr endpoint (fallback).
        """
        try:
            # multiaddr endpoint returns all derived addresses and wallet info
            url = f"{cls.BLOCKCHAIN_INFO_URL}/multiaddr?active={key}"
            data = await HTTPClient.get(url, timeout=30)

            # Extract wallet info
            wallet = data.get("wallet", {})
            final_balance = wallet.get("final_balance", 0)

            # Also check addresses array for total
            addresses = data.get("addresses", [])
            total_received = 0
            total_sent = 0
            n_tx = 0

            for addr in addresses:
                total_received += addr.get("total_received", 0)
                total_sent += addr.get("total_sent", 0)
                n_tx += addr.get("n_tx", 0)

            return {
                "success": True,
                "key": key,
                "balance": final_balance / 100_000_000,
                "total_received": total_received / 100_000_000,
                "total_sent": total_sent / 100_000_000,
                "transaction_count": n_tx,
                "source": "multiaddr",
            }
        except Exception as e:
            logger.warning(f"multiaddr failed for {key[:20]}...: {e}")
            return {"error": str(e), "key": key, "balance": 0}

    @classmethod
    async def _fetch_single_xpub_balance(cls, key: str) -> Dict:
        """Fetch balance for a single extended public key (internal helper)."""
        try:
            url = f"{cls.BLOCKCHAIN_INFO_URL}/balance?active={key}"
            data = await HTTPClient.get(url, timeout=20)

            if key not in data:
                return {"error": "Key not found in response", "key": key, "balance": 0}

            key_data = data[key]

            return {
                "success": True,
                "key": key,
                "balance": key_data.get("final_balance", 0) / 100_000_000,
                "total_received": key_data.get("total_received", 0) / 100_000_000,
                "total_sent": key_data.get("total_sent", 0) / 100_000_000,
                "transaction_count": key_data.get("n_tx", 0),
            }
        except Exception as e:
            return {"error": str(e), "key": key, "balance": 0}

    @classmethod
    @cached(cache=balance_cache, ttl=120.0, key_prefix="xpub_balance")
    async def get_xpub_balance(cls, xpub: str) -> Dict:
        """
        Fetch Bitcoin HD wallet balance using xpub/ypub/zpub.

        Uses address derivation approach first (most reliable for Ledger xpubs),
        then falls back to API endpoints if derivation fails.
        """
        if not cls.is_valid_xpub(xpub):
            return {"error": "Invalid xpub format", "xpub": xpub}

        try:
            # First, try deriving addresses and checking their balances
            # This is the most reliable method for Ledger xpubs with SegWit addresses
            if HDWALLET_AVAILABLE:
                logger.info(f"Trying derived address approach for {xpub[:20]}...")
                result = await cls._fetch_derived_addresses_balance(xpub)

                if result.get("success") and result.get("balance", 0) > 0:
                    logger.info(f"Found balance via derived addresses: {result.get('balance')} BTC")
                    return {
                        "success": True,
                        "xpub": xpub,
                        "used_format": result.get("source", "derived"),
                        "converted_key": None,
                        "balance": result.get("balance", 0),
                        "total_received": result.get("total_received", 0),
                        "total_sent": result.get("total_sent", 0),
                        "transaction_count": result.get("transaction_count", 0),
                        "currency": "BTC",
                    }

            # Fallback: try multiaddr API (works for some xpubs)
            logger.info(f"Trying multiaddr API for {xpub[:20]}...")
            result = await cls._fetch_xpub_via_multiaddr(xpub)

            if result.get("success") and result.get("balance", 0) > 0:
                logger.info(f"Found balance via multiaddr: {result.get('balance')} BTC")
                return {
                    "success": True,
                    "xpub": xpub,
                    "used_format": "multiaddr",
                    "converted_key": None,
                    "balance": result.get("balance", 0),
                    "total_received": result.get("total_received", 0),
                    "total_sent": result.get("total_sent", 0),
                    "transaction_count": result.get("transaction_count", 0),
                    "currency": "BTC",
                }

            # Try format conversions as last resort
            logger.info("Trying format conversions...")
            variants = get_xpub_variants(xpub)

            best_result = None
            best_balance = result.get("balance", 0) if result.get("success") else -1
            tried_formats = ["derived", "multiaddr"]

            # Set initial best result if we have one
            if result.get("success"):
                best_result = {
                    "success": True,
                    "xpub": xpub,
                    "used_format": "multiaddr",
                    "converted_key": None,
                    "balance": result.get("balance", 0),
                    "total_received": result.get("total_received", 0),
                    "total_sent": result.get("total_sent", 0),
                    "transaction_count": result.get("transaction_count", 0),
                    "currency": "BTC",
                }

            for prefix, key in variants:
                # Skip the original xpub since we already tried it
                if key == xpub:
                    continue

                # Try multiaddr with converted format (more reliable than Haskoin)
                variant_result = await cls._fetch_xpub_via_multiaddr(key)
                tried_formats.append(prefix or "unknown")

                if variant_result.get("success"):
                    balance = variant_result.get("balance", 0)

                    # If we found a better balance, use this result
                    if balance > best_balance:
                        best_balance = balance
                        best_result = {
                            "success": True,
                            "xpub": xpub,  # Original input
                            "used_format": prefix,
                            "converted_key": key,
                            "balance": balance,
                            "total_received": variant_result.get("total_received", 0),
                            "total_sent": variant_result.get("total_sent", 0),
                            "transaction_count": variant_result.get("transaction_count", 0),
                            "currency": "BTC",
                        }

                    # If we found balance > 0, no need to try more formats
                    if balance > 0:
                        logger.info(f"Found balance using {prefix} format (tried: {tried_formats})")
                        break

            # If we found any successful result, return it
            if best_result:
                return best_result

            # No successful result from any format
            return {
                "success": True,
                "xpub": xpub,
                "balance": 0,
                "total_received": 0,
                "total_sent": 0,
                "transaction_count": 0,
                "currency": "BTC",
                "tried_formats": tried_formats,
            }

        except Exception as e:
            logger.error(f"Error fetching xpub balance: {e}")
            return {"error": f"Failed to fetch xpub balance: {str(e)}", "xpub": xpub}

    @classmethod
    async def get_total_btc_balance(cls, addresses: list, xpubs: list) -> Dict:
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
                if result.get("success"):
                    total_single += result.get("balance", 0)
                elif result.get("error"):
                    errors.append(result["error"])

        # Fetch xpub balances
        if xpubs:
            tasks = [cls.get_xpub_balance(xpub) for xpub in xpubs]
            results = await asyncio.gather(*tasks)

            for result in results:
                if result.get("success"):
                    total_xpub += result.get("balance", 0)
                elif result.get("error"):
                    errors.append(result["error"])

        return {
            "total_single": total_single,
            "total_xpub": total_xpub,
            "total_combined": total_single + total_xpub,
            "errors": errors if errors else None,
        }
