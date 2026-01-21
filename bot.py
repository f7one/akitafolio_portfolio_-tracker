import os
import logging
import asyncio
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, List, Any, Callable
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from web3 import Web3
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================================
# RETRY DECORATOR FOR NETWORK CALLS
# ============================================================================

def retry_async(max_retries: int = 3, backoff_factor: float = 1.5, exceptions: tuple = (Exception,)):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# HTTP CLIENT SESSION MANAGER
# ============================================================================

class HTTPClient:
    """Singleton HTTP client with connection pooling."""
    _session: Optional[aiohttp.ClientSession] = None
    _timeout = aiohttp.ClientTimeout(total=15)
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(timeout=cls._timeout)
        return cls._session
    
    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
    
    @classmethod
    @retry_async(max_retries=3, backoff_factor=1.5)
    async def get(cls, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Make async GET request with retry logic."""
        session = await cls.get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            response.raise_for_status()
            return await response.json()
    
    @classmethod
    @retry_async(max_retries=3, backoff_factor=1.5)
    async def get_text(cls, url: str, timeout: int = 10) -> str:
        """Make async GET request returning text with retry logic."""
        session = await cls.get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            response.raise_for_status()
            return await response.text()


# ============================================================================
# INPUT VALIDATION
# ============================================================================

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validator:
    """Centralized input validation."""
    
    # Bitcoin address patterns
    BTC_LEGACY_PATTERN = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$')
    BTC_SEGWIT_PATTERN = re.compile(r'^bc1[a-z0-9]{39,59}$', re.IGNORECASE)
    
    # xpub patterns
    XPUB_PREFIXES = ('xpub', 'ypub', 'zpub', 'tpub', 'upub', 'vpub')
    
    @staticmethod
    def validate_eth_address(address: str) -> str:
        """Validate Ethereum address and return checksummed version."""
        if not address:
            raise ValidationError("Address cannot be empty")
        
        try:
            if not Web3.is_address(address):
                raise ValidationError(f"Invalid Ethereum address format: {address}")
            return Web3.to_checksum_address(address)
        except Exception as e:
            raise ValidationError(f"Invalid Ethereum address: {address}") from e
    
    @staticmethod
    def validate_btc_address(address: str) -> str:
        """Validate Bitcoin address format."""
        if not address:
            raise ValidationError("Address cannot be empty")
        
        # Check Legacy (1...) or SegWit (3...)
        if Validator.BTC_LEGACY_PATTERN.match(address):
            return address
        
        # Check Native SegWit (bc1...)
        if Validator.BTC_SEGWIT_PATTERN.match(address):
            return address
        
        raise ValidationError(f"Invalid Bitcoin address format: {address}")
    
    @staticmethod
    def validate_xpub(xpub: str) -> str:
        """Validate xpub/ypub/zpub format."""
        if not xpub:
            raise ValidationError("xpub cannot be empty")
        
        if not any(xpub.startswith(prefix) for prefix in Validator.XPUB_PREFIXES):
            raise ValidationError(f"Invalid xpub prefix. Must start with: {', '.join(Validator.XPUB_PREFIXES)}")
        
        if not (100 <= len(xpub) <= 120):
            raise ValidationError(f"Invalid xpub length: {len(xpub)} (expected 100-120)")
        
        return xpub
    
    @staticmethod
    def validate_chain(chain: str, valid_chains: Dict) -> str:
        """Validate chain name."""
        chain = chain.lower().strip()
        if chain not in valid_chains:
            raise ValidationError(f"Unsupported chain: {chain}. Valid chains: {', '.join(valid_chains.keys())}")
        return chain

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID')

# Validate required configuration at startup
def validate_config():
    """Validate required environment variables."""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not INFURA_PROJECT_ID:
        errors.append("INFURA_PROJECT_ID is required")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ValueError(f"Missing required configuration: {', '.join(errors)}")

# Storage files
STORAGE_FILE = Path(__file__).parent / 'saved_addresses.json'
HISTORY_FILE = Path(__file__).parent / 'portfolio_history.json'

# EVM Chain Configuration - All chains that use ETH as native currency
ETH_CHAINS = {
    'ethereum': {
        'name': 'Ethereum',
        'rpc_url': f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '⟠',
        'counts_as_eth': True
    },
    'base': {
        'name': 'Base',
        'rpc_url': f'https://base-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '🔵',
        'counts_as_eth': True
    },
    'linea': {
        'name': 'Linea',
        'rpc_url': f'https://linea-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '🟢',
        'counts_as_eth': True
    },
    'optimism': {
        'name': 'Optimism',
        'rpc_url': f'https://optimism-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '🔴',
        'counts_as_eth': True
    },
    'arbitrum': {
        'name': 'Arbitrum',
        'rpc_url': f'https://arbitrum-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '🔷',
        'counts_as_eth': True
    },
    'unichain': {
        'name': 'Unichain',
        'rpc_url': f'https://unichain-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'ETH',
        'emoji': '🦄',
        'counts_as_eth': True
    }
}

# Other EVM chains (non-ETH native)
OTHER_CHAINS = {
    'polygon': {
        'name': 'Polygon',
        'rpc_url': f'https://polygon-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'MATIC',
        'emoji': '🟣',
        'counts_as_eth': False
    },
    'bsc': {
        'name': 'BSC',
        'rpc_url': f'https://bsc-mainnet.infura.io/v3/{INFURA_PROJECT_ID}',
        'symbol': 'BNB',
        'emoji': '🟡',
        'counts_as_eth': False
    }
}

# Combine all chains
ALL_CHAINS = {**ETH_CHAINS, **OTHER_CHAINS}

# Initialize Web3 instances for all chains
web3_instances = {
    chain: Web3(Web3.HTTPProvider(config['rpc_url']))
    for chain, config in ALL_CHAINS.items()
}

# ERC20 ABI (minimal - for balance checking)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]

# Popular tokens to track by default (can be customized per user)
DEFAULT_TOKENS = {
    'ethereum': [
        {'symbol': 'USDT', 'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'decimals': 6, 'coingecko_id': 'tether'},
        {'symbol': 'USDC', 'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'decimals': 6, 'coingecko_id': 'usd-coin'},
        {'symbol': 'DAI', 'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F', 'decimals': 18, 'coingecko_id': 'dai'},
        {'symbol': 'WETH', 'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'decimals': 18, 'coingecko_id': 'weth'},
        {'symbol': 'WBTC', 'address': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 'decimals': 8, 'coingecko_id': 'wrapped-bitcoin'},
        {'symbol': 'LINK', 'address': '0x514910771AF9Ca656af840dff83E8264EcF986CA', 'decimals': 18, 'coingecko_id': 'chainlink'},
        {'symbol': 'UNI', 'address': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'decimals': 18, 'coingecko_id': 'uniswap'},
        {'symbol': 'AAVE', 'address': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'decimals': 18, 'coingecko_id': 'aave'},
    ],
    'base': [
        {'symbol': 'USDC', 'address': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', 'decimals': 6, 'coingecko_id': 'usd-coin'},
    ],
    'arbitrum': [
        {'symbol': 'USDC', 'address': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', 'decimals': 6, 'coingecko_id': 'usd-coin'},
        {'symbol': 'USDT', 'address': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', 'decimals': 6, 'coingecko_id': 'tether'},
    ],
    'optimism': [
        {'symbol': 'USDC', 'address': '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85', 'decimals': 6, 'coingecko_id': 'usd-coin'},
        {'symbol': 'USDT', 'address': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58', 'decimals': 6, 'coingecko_id': 'tether'},
    ],
    'polygon': [
        {'symbol': 'USDC', 'address': '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', 'decimals': 6, 'coingecko_id': 'usd-coin'},
        {'symbol': 'USDT', 'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F', 'decimals': 6, 'coingecko_id': 'tether'},
    ],
}

# DeFi Protocol ABIs
AAVE_V3_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# DeFi Protocol Addresses
DEFI_PROTOCOLS = {
    'ethereum': {
        'aave_v3_pool': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
    },
    'arbitrum': {
        'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
    },
    'optimism': {
        'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
    },
    'base': {
        'aave_v3_pool': '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5',
    },
    'polygon': {
        'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
    },
}


# Storage Functions

def load_saved_addresses(user_id: int) -> dict:
    """Load saved addresses for a user."""
    try:
        if STORAGE_FILE.exists():
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                user_data = data.get(str(user_id), {
                    'eth': [], 
                    'btc': [], 
                    'xpub': [],
                    'tokens': [],  # Custom tokens to track
                    'track_defi': True  # Track DeFi positions by default
                })
                # Ensure all keys exist for backward compatibility
                if 'xpub' not in user_data:
                    user_data['xpub'] = []
                if 'tokens' not in user_data:
                    user_data['tokens'] = []
                if 'track_defi' not in user_data:
                    user_data['track_defi'] = True
                return user_data
        return {
            'eth': [], 
            'btc': [], 
            'xpub': [],
            'tokens': [],
            'track_defi': True
        }
    except Exception as e:
        logger.error(f"Error loading saved addresses: {e}")
        return {
            'eth': [], 
            'btc': [], 
            'xpub': [],
            'tokens': [],
            'track_defi': True
        }


def save_addresses(user_id: int, addresses: dict):
    """Save addresses for a user."""
    try:
        data = {}
        if STORAGE_FILE.exists():
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
        
        data[str(user_id)] = addresses
        
        with open(STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error saving addresses: {e}")
        return False


def load_portfolio_history(user_id: int) -> list:
    """Load portfolio value history for a user."""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return data.get(str(user_id), [])
        return []
    except Exception as e:
        logger.error(f"Error loading portfolio history: {e}")
        return []


def save_portfolio_snapshot(user_id: int, total_value_usd: float, eth_amount: float, btc_amount: float, eth_price: float, btc_price: float):
    """Save a portfolio snapshot for historical tracking."""
    try:
        data = {}
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
        
        user_history = data.get(str(user_id), [])
        
        # Add new snapshot
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_value_usd': total_value_usd,
            'eth_amount': eth_amount,
            'btc_amount': btc_amount,
            'eth_price': eth_price,
            'btc_price': btc_price
        }
        
        user_history.append(snapshot)
        
        # Keep only last 30 days of history (one snapshot per check)
        # If user checks multiple times per day, we keep all
        # But clean up older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        user_history = [
            s for s in user_history 
            if datetime.fromisoformat(s['timestamp']) > cutoff_date
        ]
        
        data[str(user_id)] = user_history
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error saving portfolio snapshot: {e}")
        return False


def calculate_24h_change(user_id: int, current_value_usd: float) -> dict:
    """Calculate 24h portfolio value change."""
    try:
        history = load_portfolio_history(user_id)
        
        if not history or len(history) < 2:
            return {
                'has_data': False,
                'change_usd': 0,
                'change_percent': 0
            }
        
        # Find snapshot closest to 24 hours ago
        now = datetime.now()
        target_time = now - timedelta(hours=24)
        
        # Find the closest snapshot to 24h ago
        closest_snapshot = None
        min_diff = float('inf')
        
        for snapshot in history:
            snapshot_time = datetime.fromisoformat(snapshot['timestamp'])
            time_diff = abs((target_time - snapshot_time).total_seconds())
            
            if time_diff < min_diff:
                min_diff = time_diff
                closest_snapshot = snapshot
        
        if not closest_snapshot:
            return {
                'has_data': False,
                'change_usd': 0,
                'change_percent': 0
            }
        
        # Calculate change
        old_value = closest_snapshot['total_value_usd']
        change_usd = current_value_usd - old_value
        change_percent = (change_usd / old_value * 100) if old_value > 0 else 0
        
        return {
            'has_data': True,
            'change_usd': change_usd,
            'change_percent': change_percent,
            'old_value': old_value,
            'hours_ago': min_diff / 3600  # Convert seconds to hours
        }
        
    except Exception as e:
        logger.error(f"Error calculating 24h change: {e}")
        return {
            'has_data': False,
            'change_usd': 0,
            'change_percent': 0
        }


def is_valid_ethereum_address(address: str) -> bool:
    """Validate Ethereum/EVM address format."""
    try:
        Validator.validate_eth_address(address)
        return True
    except ValidationError:
        return False


def is_valid_bitcoin_address(address: str) -> bool:
    """Basic Bitcoin address validation."""
    try:
        Validator.validate_btc_address(address)
        return True
    except ValidationError:
        return False


def is_valid_xpub(xpub: str) -> bool:
    """Validate xpub/ypub/zpub format."""
    try:
        Validator.validate_xpub(xpub)
        return True
    except ValidationError:
        return False


async def get_crypto_prices() -> dict:
    """Fetch current ETH and BTC prices in USD from CoinGecko API."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd"
        data = await HTTPClient.get(url, timeout=10)
        return {
            'eth': float(data.get('ethereum', {}).get('usd', 0)),
            'btc': float(data.get('bitcoin', {}).get('usd', 0))
        }
    except Exception as e:
        logger.error(f"Error fetching crypto prices: {e}")
        return {'eth': 0.0, 'btc': 0.0}


async def get_chain_balance(address: str, chain: str) -> dict:
    """Fetch balance for a given address on specified chain."""
    try:
        if chain not in ALL_CHAINS:
            return {"error": f"Unsupported chain: {chain}", "balance": 0}
        
        chain_config = ALL_CHAINS[chain]
        w3 = web3_instances[chain]
        
        # Get balance in Wei
        balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
        
        # Convert to Ether/native token
        balance = float(w3.from_wei(balance_wei, 'ether'))
        
        return {
            "success": True,
            "chain": chain,
            "address": address,
            "balance": balance,
            "currency": chain_config['symbol'],
            "network": chain_config['name'],
            "emoji": chain_config['emoji'],
            "counts_as_eth": chain_config['counts_as_eth']
        }
    except Exception as e:
        logger.error(f"Error fetching {chain} balance: {e}")
        return {
            "error": str(e),
            "chain": chain,
            "balance": 0,
            "counts_as_eth": ALL_CHAINS.get(chain, {}).get('counts_as_eth', False)
        }


async def get_all_eth_balances(address: str) -> dict:
    """Fetch ETH balances from all chains and aggregate them."""
    if not is_valid_ethereum_address(address):
        return {"error": "Invalid address format"}
    
    # Fetch balances from all chains in parallel
    tasks = [get_chain_balance(address, chain) for chain in ALL_CHAINS.keys()]
    results = await asyncio.gather(*tasks)
    
    # Aggregate ETH balances
    total_eth = 0
    chain_balances = []
    
    for result in results:
        chain_balances.append(result)
        if result.get('counts_as_eth', False) and 'error' not in result:
            total_eth += result['balance']
    
    return {
        "success": True,
        "address": address,
        "total_eth": total_eth,
        "chain_balances": chain_balances
    }


async def get_bitcoin_balance(address: str) -> dict:
    """Fetch Bitcoin balance for a given address using Blockchain.info API."""
    try:
        if not is_valid_bitcoin_address(address):
            return {"error": "Invalid Bitcoin address"}
        
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response_text = await HTTPClient.get_text(url, timeout=10)
        
        balance_satoshi = int(response_text)
        balance_btc = balance_satoshi / 100000000
        
        return {
            "success": True,
            "address": address,
            "balance": balance_btc,
            "currency": "BTC"
        }
    
    except Exception as e:
        logger.error(f"Error fetching Bitcoin balance: {e}")
        return {"error": f"Failed to fetch Bitcoin balance: {str(e)}"}


async def get_xpub_balance(xpub: str) -> dict:
    """Fetch Bitcoin HD wallet balance using xpub via Blockchain.info API."""
    try:
        if not is_valid_xpub(xpub):
            return {"error": "Invalid xpub format"}
        
        # Blockchain.info xpub balance endpoint
        url = f"https://blockchain.info/balance?active={xpub}"
        data = await HTTPClient.get(url, timeout=20)
        
        if xpub not in data:
            return {"error": "xpub not found in response"}
        
        xpub_data = data[xpub]
        
        return {
            "success": True,
            "xpub": xpub,
            "balance": xpub_data.get('final_balance', 0) / 100000000,
            "total_received": xpub_data.get('total_received', 0) / 100000000,
            "total_sent": xpub_data.get('total_sent', 0) / 100000000,
            "transaction_count": xpub_data.get('n_tx', 0),
            "currency": "BTC"
        }
    
    except Exception as e:
        logger.error(f"Error fetching xpub balance: {e}")
        return {"error": f"Failed to fetch xpub balance: {str(e)}"}


async def get_erc20_balance(address: str, token_address: str, chain: str) -> dict:
    """Fetch ERC20 token balance for an address on a specific chain."""
    try:
        if chain not in web3_instances:
            return {"error": f"Unsupported chain: {chain}", "balance": 0}
        
        w3 = web3_instances[chain]
        checksum_address = Web3.to_checksum_address(address)
        checksum_token = Web3.to_checksum_address(token_address)
        
        # Create contract instance
        contract = w3.eth.contract(address=checksum_token, abi=ERC20_ABI)
        
        # Get token info
        try:
            balance = contract.functions.balanceOf(checksum_address).call()
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()
        except Exception as e:
            logger.error(f"Error calling contract methods: {e}")
            return {"error": f"Failed to fetch token data: {str(e)}", "balance": 0}
        
        # Convert balance from wei-like units
        balance_formatted = balance / (10 ** decimals)
        
        return {
            "success": True,
            "address": address,
            "token_address": token_address,
            "chain": chain,
            "balance": balance_formatted,
            "decimals": decimals,
            "symbol": symbol
        }
    
    except Exception as e:
        logger.error(f"Error fetching ERC20 balance on {chain}: {e}")
        return {"error": str(e), "balance": 0}


async def get_token_price(coingecko_id: str) -> float:
    """Fetch token price from CoinGecko."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        data = await HTTPClient.get(url, timeout=10)
        return float(data.get(coingecko_id, {}).get('usd', 0))
    except Exception as e:
        logger.error(f"Error fetching price for {coingecko_id}: {e}")
        return 0.0


async def get_all_token_balances(addresses: list, custom_tokens: list = None) -> dict:
    """Fetch all token balances for user's addresses across all chains."""
    all_balances = []
    total_value_usd = 0
    
    # Combine default tokens with custom tokens
    tokens_to_check = {}
    for chain, tokens in DEFAULT_TOKENS.items():
        tokens_to_check[chain] = tokens.copy()
    
    # Add custom tokens if provided
    if custom_tokens:
        for token in custom_tokens:
            chain = token.get('chain', 'ethereum')
            if chain not in tokens_to_check:
                tokens_to_check[chain] = []
            tokens_to_check[chain].append(token)
    
    # Fetch balances for all addresses and tokens
    tasks = []
    token_info_map = {}  # Map to store token info for price fetching
    
    for address in addresses:
        for chain, tokens in tokens_to_check.items():
            for token in tokens:
                task = get_erc20_balance(address, token['address'], chain)
                tasks.append(task)
                # Store token info for later price lookup
                key = f"{chain}_{token['address']}"
                token_info_map[key] = token
    
    if not tasks:
        return {"balances": [], "total_value_usd": 0, "token_count": 0}
    
    results = await asyncio.gather(*tasks)
    
    # Filter non-zero balances and fetch prices
    price_tasks = {}
    non_zero_results = []
    
    for result in results:
        if result.get('success') and result.get('balance', 0) > 0.0001:  # Filter dust
            non_zero_results.append(result)
            key = f"{result['chain']}_{result['token_address']}"
            if key in token_info_map:
                coingecko_id = token_info_map[key].get('coingecko_id')
                if coingecko_id and coingecko_id not in price_tasks:
                    price_tasks[coingecko_id] = get_token_price(coingecko_id)
    
    # Fetch all prices in parallel
    if price_tasks:
        price_results = await asyncio.gather(*price_tasks.values())
        prices = dict(zip(price_tasks.keys(), price_results))
    else:
        prices = {}
    
    # Calculate USD values
    for result in non_zero_results:
        key = f"{result['chain']}_{result['token_address']}"
        if key in token_info_map:
            coingecko_id = token_info_map[key].get('coingecko_id')
            price = prices.get(coingecko_id, 0)
            usd_value = result['balance'] * price
            result['price_usd'] = price
            result['value_usd'] = usd_value
            result['chain_name'] = ALL_CHAINS.get(result['chain'], {}).get('name', result['chain'])
            total_value_usd += usd_value
            all_balances.append(result)
    
    # Sort by USD value
    all_balances.sort(key=lambda x: x.get('value_usd', 0), reverse=True)
    
    return {
        "balances": all_balances,
        "total_value_usd": total_value_usd,
        "token_count": len(all_balances)
    }


async def get_aave_position(address: str, chain: str) -> dict:
    """Fetch Aave V3 lending position for an address on a specific chain."""
    try:
        if chain not in DEFI_PROTOCOLS or 'aave_v3_pool' not in DEFI_PROTOCOLS[chain]:
            return {"error": f"Aave V3 not supported on {chain}"}
        
        w3 = web3_instances[chain]
        checksum_address = Web3.to_checksum_address(address)
        pool_address = DEFI_PROTOCOLS[chain]['aave_v3_pool']
        
        # Create contract instance
        contract = w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=AAVE_V3_POOL_ABI)
        
        # Get user account data
        account_data = contract.functions.getUserAccountData(checksum_address).call()
        
        # Values are in USD with 8 decimals
        total_collateral = account_data[0] / 1e8
        total_debt = account_data[1] / 1e8
        available_borrow = account_data[2] / 1e8
        health_factor = account_data[5] / 1e18
        
        net_value = total_collateral - total_debt
        
        if total_collateral == 0 and total_debt == 0:
            return {"success": True, "has_position": False}
        
        return {
            "success": True,
            "has_position": True,
            "chain": chain,
            "chain_name": ALL_CHAINS.get(chain, {}).get('name', chain),
            "protocol": "Aave V3",
            "total_collateral_usd": total_collateral,
            "total_debt_usd": total_debt,
            "available_borrow_usd": available_borrow,
            "net_value_usd": net_value,
            "health_factor": health_factor
        }
    
    except Exception as e:
        logger.error(f"Error fetching Aave position on {chain}: {e}")
        return {"error": str(e), "has_position": False}


async def get_all_defi_positions(addresses: list) -> dict:
    """Fetch all DeFi positions for user's addresses."""
    all_positions = []
    total_collateral = 0
    total_debt = 0
    total_net_value = 0
    
    # Check Aave on all supported chains
    tasks = []
    for address in addresses:
        for chain in DEFI_PROTOCOLS.keys():
            tasks.append(get_aave_position(address, chain))
    
    if not tasks:
        return {
            "positions": [],
            "total_collateral_usd": 0,
            "total_debt_usd": 0,
            "total_net_value_usd": 0,
            "position_count": 0
        }
    
    results = await asyncio.gather(*tasks)
    
    # Filter positions with actual balances
    for result in results:
        if result.get('has_position'):
            all_positions.append(result)
            total_collateral += result.get('total_collateral_usd', 0)
            total_debt += result.get('total_debt_usd', 0)
            total_net_value += result.get('net_value_usd', 0)
    
    return {
        "positions": all_positions,
        "total_collateral_usd": total_collateral,
        "total_debt_usd": total_debt,
        "total_net_value_usd": total_net_value,
        "position_count": len(all_positions)
    }


async def get_portfolio_value(eth_addresses: list, btc_addresses: list, xpub_keys: list = None, custom_tokens: list = None, track_defi: bool = True) -> dict:
    """Calculate total portfolio value for multiple addresses and xpub keys, including tokens and DeFi."""
    # Fetch prices
    prices = await get_crypto_prices()
    
    # Fetch all ETH balances
    eth_tasks = [get_all_eth_balances(addr) for addr in eth_addresses]
    eth_results = await asyncio.gather(*eth_tasks) if eth_addresses else []
    
    # Fetch all BTC balances
    btc_tasks = [get_bitcoin_balance(addr) for addr in btc_addresses]
    btc_results = await asyncio.gather(*btc_tasks) if btc_addresses else []
    
    # Fetch all xpub balances
    xpub_keys = xpub_keys or []
    xpub_tasks = [get_xpub_balance(xpub) for xpub in xpub_keys]
    xpub_results = await asyncio.gather(*xpub_tasks) if xpub_keys else []
    
    # Fetch token balances
    token_data = await get_all_token_balances(eth_addresses, custom_tokens) if eth_addresses else {
        "balances": [], "total_value_usd": 0, "token_count": 0
    }
    
    # Fetch DeFi positions
    defi_data = await get_all_defi_positions(eth_addresses) if (eth_addresses and track_defi) else {
        "positions": [], "total_collateral_usd": 0, "total_debt_usd": 0, 
        "total_net_value_usd": 0, "position_count": 0
    }
    
    # Calculate totals
    total_eth = sum(r.get('total_eth', 0) for r in eth_results if 'error' not in r)
    total_btc = sum(r.get('balance', 0) for r in btc_results if 'error' not in r)
    total_btc_xpub = sum(r.get('balance', 0) for r in xpub_results if 'error' not in r)
    
    # Combine BTC from addresses and xpub
    total_btc_combined = total_btc + total_btc_xpub
    
    total_eth_usd = total_eth * prices['eth']
    total_btc_usd = total_btc_combined * prices['btc']
    
    # Calculate total portfolio including tokens and DeFi
    total_portfolio_usd = (
        total_eth_usd + 
        total_btc_usd + 
        token_data['total_value_usd'] + 
        defi_data['total_net_value_usd']
    )
    
    return {
        'total_eth': total_eth,
        'total_btc': total_btc,
        'total_btc_xpub': total_btc_xpub,
        'total_btc_combined': total_btc_combined,
        'eth_price': prices['eth'],
        'btc_price': prices['btc'],
        'total_eth_usd': total_eth_usd,
        'total_btc_usd': total_btc_usd,
        'total_portfolio_usd': total_portfolio_usd,
        'eth_results': eth_results,
        'btc_results': btc_results,
        'xpub_results': xpub_results,
        'token_data': token_data,
        'defi_data': defi_data
    }


# Command Handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Welcome to Akitafolio!\n\n"
        "Your multi-chain crypto portfolio tracker across multiple chains.\n\n"
        "📊 **Balance Commands:**\n"
        "/eth <address> - Check ETH balance across all chains\n"
        "/btc <address> - Check Bitcoin balance\n"
        "/xpub <xpub_key> - Check HD wallet balance (xpub/ypub/zpub)\n\n"
        "💼 **Portfolio Management:**\n"
        "/add_eth <addr1> <addr2> ... - Save ETH address(es)\n"
        "/add_btc <addr1> <addr2> ... - Save BTC address(es)\n"
        "/add_xpub <key1> <key2> ... - Save HD wallet(s)\n"
        "/portfolio - View total portfolio value (ETH + BTC + Tokens + DeFi!)\n"
        "/addresses - List your saved addresses\n"
        "/remove_eth <address> - Remove ETH address\n"
        "/remove_btc <address> - Remove BTC address\n"
        "/remove_xpub <xpub_key> - Remove HD wallet\n\n"
        "🪙 **Token & DeFi Tracking:**\n"
        "/tokens - View all ERC20 token balances\n"
        "/defi - View DeFi positions (Aave, etc.)\n"
        "/add_token - Add custom ERC20 token\n"
        "/toggle_defi - Enable/disable DeFi tracking\n\n"
        "ℹ️ **Other Commands:**\n"
        "/chains - List all supported chains\n"
        "/help - Show detailed help\n\n"
        "💡 Tip: You can add multiple addresses at once!"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_message = (
        "🔍 **How to use this bot:**\n\n"
        "**1️⃣ Quick Balance Check**\n"
        "   /eth <address> - Check ETH across all chains\n"
        "   /btc <address> - Check Bitcoin balance\n"
        "   /xpub <xpub_key> - Check HD wallet balance\n\n"
        "**2️⃣ Portfolio Tracking**\n"
        "   a) Save your addresses (single or multiple):\n"
        "      /add_eth 0xAddr1 0xAddr2 0xAddr3\n"
        "      /add_btc btcAddr1 btcAddr2\n"
        "      /add_xpub xpub6... ypub6...\n\n"
        "   b) View total portfolio:\n"
        "      /portfolio\n"
        "      Shows total ETH + BTC + Tokens + DeFi in USD!\n"
        "      Includes 24h price change tracking! 📈📉\n\n"
        "   c) Manage addresses:\n"
        "      /addresses - List saved addresses\n"
        "      /remove_eth <address> - Remove address\n\n"
        "**3️⃣ ERC20 Tokens**\n"
        "   /tokens - View all token balances\n"
        "   /add_token <chain> <address> <coingecko_id>\n"
        "   Automatically tracks popular tokens (USDT, USDC, etc.)\n\n"
        "**4️⃣ DeFi Positions**\n"
        "   /defi - View lending/borrowing positions\n"
        "   /toggle_defi - Enable/disable DeFi tracking\n"
        "   Supports: Aave V3 on multiple chains\n\n"
        "**5️⃣ Supported Networks**\n"
        "   /chains - See all 8 EVM chains + Bitcoin\n\n"
        "💰 **Portfolio Features:**\n"
        "• Track multiple addresses\n"
        "• Aggregated ETH from all L1/L2 chains\n"
        "• ERC20 tokens (USDT, USDC, DAI, WETH, etc.)\n"
        "• DeFi lending positions (Aave V3)\n"
        "• 24-hour portfolio change tracking\n"
        "• Combined total value in USD\n"
        "• Real-time prices from CoinGecko\n"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def chains_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all supported chains."""
    chains_info = "🔗 **Supported Blockchain Networks**\n\n"
    
    chains_info += "**ETH Chains (counted in total):**\n"
    for chain, config in ETH_CHAINS.items():
        chains_info += f"{config['emoji']} {config['name']} ({config['symbol']})\n"
    
    chains_info += "\n**Other Chains:**\n"
    for chain, config in OTHER_CHAINS.items():
        chains_info += f"{config['emoji']} {config['name']} ({config['symbol']})\n"
    
    chains_info += "\n₿ **Bitcoin** (BTC)\n"
    chains_info += f"\n📊 Total: {len(ALL_CHAINS)} EVM chains + Bitcoin"
    
    await update.message.reply_text(chains_info, parse_mode='Markdown')


async def eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /eth command to check total ETH balance across all chains."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an Ethereum address.\n"
            "Usage: /eth <address>\n"
            "Example: /eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb\n\n"
            "💡 Tip: Use /add_eth to save addresses for portfolio tracking!"
        )
        return
    
    address = context.args[0]
    
    # Send "processing" message
    processing_msg = await update.message.reply_text(
        "🔄 Fetching balances across all chains...\n"
        "This may take a moment ⏳"
    )
    
    # Get all balances and prices
    result = await get_all_eth_balances(address)
    prices = await get_crypto_prices()
    
    if "error" in result:
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
        return
    
    # Build response message
    response = f"💰 **Multi-Chain Balance Summary**\n\n"
    response += f"Address: `{result['address'][:10]}...{result['address'][-8:]}`\n\n"
    
    # Total summary
    total_eth = result['total_eth']
    total_usd = total_eth * prices['eth'] if prices['eth'] > 0 else 0
    
    response += f"📊 **TOTAL ETH: {total_eth:.6f} ETH**\n"
    if prices['eth'] > 0:
        response += f"💵 **USD Value: ${total_usd:,.2f}**\n"
        response += f"📈 ETH Price: ${prices['eth']:,.2f}\n"
    response += "\n" + "─" * 30 + "\n\n"
    
    # Individual chain balances
    response += "**Balance by Chain:**\n\n"
    
    for chain_data in result['chain_balances']:
        if 'error' in chain_data and chain_data['balance'] == 0:
            continue
        
        balance = chain_data.get('balance', 0)
        if balance > 0:
            emoji = chain_data.get('emoji', '•')
            name = chain_data.get('network', chain_data.get('chain', 'Unknown'))
            symbol = chain_data.get('currency', 'TOKEN')
            response += f"{emoji} **{name}**: {balance:.6f} {symbol}\n"
    
    # Check if all balances are zero
    total_balance = sum(c.get('balance', 0) for c in result['chain_balances'])
    if total_balance == 0:
        response = f"💰 **Multi-Chain Balance Summary**\n\n"
        response += f"Address: `{result['address'][:10]}...{result['address'][-8:]}`\n\n"
        response += "📊 No balances found on any chain.\n"
        response += f"✅ Checked {len(ALL_CHAINS)} networks"
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /btc command to check Bitcoin balance."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Bitcoin address.\n"
            "Usage: /btc <bitcoin_address>\n"
            "Example: /btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n\n"
            "💡 Tip: Use /add_btc to save addresses for portfolio tracking!"
        )
        return
    
    address = context.args[0]
    
    # Send "processing" message
    processing_msg = await update.message.reply_text("🔄 Fetching Bitcoin balance...")
    
    # Get balance and price
    result = await get_bitcoin_balance(address)
    prices = await get_crypto_prices()
    
    if "error" in result:
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
    else:
        btc_balance = result['balance']
        usd_value = btc_balance * prices['btc'] if prices['btc'] > 0 else 0
        
        response_message = (
            f"₿ **Bitcoin Balance**\n\n"
            f"Address: `{result['address']}`\n"
            f"Balance: **{btc_balance:.8f} BTC**\n"
        )
        
        if prices['btc'] > 0:
            response_message += f"💵 USD Value: **${usd_value:,.2f}**\n"
            response_message += f"📈 BTC Price: ${prices['btc']:,.2f}"
        
        await processing_msg.edit_text(response_message, parse_mode='Markdown')


async def add_eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add one or multiple Ethereum addresses to user's portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide Ethereum address(es) to save.\n\n"
            "Usage:\n"
            "• Single: /add_eth <address>\n"
            "• Multiple: /add_eth <addr1> <addr2> <addr3>\n\n"
            "Example:\n"
            "/add_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb\n"
            "/add_eth 0xAddr1 0xAddr2 0xAddr3"
        )
        return
    
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    # Process all provided addresses
    added = []
    skipped = []
    invalid = []
    
    for addr in context.args:
        # Remove commas if user separated with commas
        addr = addr.strip(',').strip()
        
        if not is_valid_ethereum_address(addr):
            invalid.append(addr)
            continue
        
        # Check if already saved
        if addr.lower() in [a.lower() for a in addresses['eth']]:
            skipped.append(addr)
            continue
        
        addresses['eth'].append(addr)
        added.append(addr)
    
    # Build response
    if added:
        if save_addresses(user_id, addresses):
            response = f"✅ **Added {len(added)} ETH address(es)!**\n\n"
            
            # Show added addresses (limit to 5 in display)
            for i, addr in enumerate(added[:5], 1):
                response += f"{i}. `{addr[:10]}...{addr[-8:]}`\n"
            
            if len(added) > 5:
                response += f"... and {len(added) - 5} more\n"
            
            response += f"\n📊 Total tracked: {len(addresses['eth'])} address(es)\n"
            
            if skipped:
                response += f"\nℹ️ Skipped {len(skipped)} duplicate(s)"
            
            if invalid:
                response += f"\n⚠️ Ignored {len(invalid)} invalid address(es)"
            
            response += "\n\n💡 Use /portfolio to see your total value!"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to save addresses. Please try again.")
    else:
        response = "❌ No new addresses added.\n\n"
        if skipped:
            response += f"• {len(skipped)} already in portfolio\n"
        if invalid:
            response += f"• {len(invalid)} invalid address(es)\n"
        await update.message.reply_text(response)


async def add_btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add one or multiple Bitcoin addresses to user's portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide Bitcoin address(es) to save.\n\n"
            "Usage:\n"
            "• Single: /add_btc <address>\n"
            "• Multiple: /add_btc <addr1> <addr2> <addr3>\n\n"
            "Example:\n"
            "/add_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n"
            "/add_btc bc1qAddr1 1Addr2 3Addr3"
        )
        return
    
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    # Process all provided addresses
    added = []
    skipped = []
    invalid = []
    
    for addr in context.args:
        # Remove commas if user separated with commas
        addr = addr.strip(',').strip()
        
        if not is_valid_bitcoin_address(addr):
            invalid.append(addr)
            continue
        
        # Check if already saved
        if addr in addresses['btc']:
            skipped.append(addr)
            continue
        
        addresses['btc'].append(addr)
        added.append(addr)
    
    # Build response
    if added:
        if save_addresses(user_id, addresses):
            response = f"✅ **Added {len(added)} BTC address(es)!**\n\n"
            
            # Show added addresses (limit to 5 in display)
            for i, addr in enumerate(added[:5], 1):
                response += f"{i}. `{addr}`\n"
            
            if len(added) > 5:
                response += f"... and {len(added) - 5} more\n"
            
            response += f"\n📊 Total tracked: {len(addresses['btc'])} address(es)\n"
            
            if skipped:
                response += f"\nℹ️ Skipped {len(skipped)} duplicate(s)"
            
            if invalid:
                response += f"\n⚠️ Ignored {len(invalid)} invalid address(es)"
            
            response += "\n\n💡 Use /portfolio to see your total value!"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to save addresses. Please try again.")
    else:
        response = "❌ No new addresses added.\n\n"
        if skipped:
            response += f"• {len(skipped)} already in portfolio\n"
        if invalid:
            response += f"• {len(invalid)} invalid address(es)\n"
        await update.message.reply_text(response)


async def xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /xpub command to check HD wallet balance."""
    if not context.args:
        await update.message.reply_text(
            "🔑 **Check HD Wallet Balance**\n\n"
            "Usage: /xpub <xpub_key>\n\n"
            "Example:\n"
            "/xpub xpub6CUGRUonZSQ4TWtTMmz...\n\n"
            "Supported formats:\n"
            "• xpub - Legacy (P2PKH)\n"
            "• ypub - SegWit (P2SH-P2WPKH)\n"
            "• zpub - Native SegWit (P2WPKH)\n\n"
            "This checks total balance across all derived addresses.\n\n"
            "💡 Tip: Use /add_xpub to save for portfolio tracking!",
            parse_mode='Markdown'
        )
        return
    
    xpub = context.args[0]
    
    # Validate xpub
    if not is_valid_xpub(xpub):
        await update.message.reply_text(
            "❌ Invalid xpub format.\n\n"
            "Must start with: xpub, ypub, or zpub\n"
            "Length should be ~111 characters"
        )
        return
    
    processing_msg = await update.message.reply_text(
        "🔄 Scanning HD wallet...\n"
        "⏳ Checking all derived addresses...\n"
        "This may take 10-20 seconds"
    )
    
    # Get xpub balance
    result = await get_xpub_balance(xpub)
    
    if "error" in result:
        await processing_msg.edit_text(
            f"❌ Error: {result['error']}\n\n"
            "Possible reasons:\n"
            "• Invalid xpub key\n"
            "• API rate limit (wait 10 seconds)\n"
            "• Network error\n\n"
            "Try again in a few moments."
        )
        return
    
    # Get BTC price
    prices = await get_crypto_prices()
    btc_price = prices.get('btc', 0)
    usd_value = result['balance'] * btc_price if btc_price > 0 else 0
    
    # Build rich response
    response = f"🔑 **HD Wallet Summary**\n\n"
    response += f"xpub: `{xpub[:15]}...{xpub[-10:]}`\n\n"
    response += "═" * 30 + "\n\n"
    response += f"💰 **Total Balance**\n"
    response += f"**{result['balance']:.8f} BTC**\n"
    
    if btc_price > 0:
        response += f"**${usd_value:,.2f} USD**\n"
        response += f"_(@ ${btc_price:,.2f}/BTC)_\n"
    
    response += "\n" + "─" * 30 + "\n\n"
    response += f"📊 **Statistics**\n"
    response += f"📥 Received: {result['total_received']:.8f} BTC\n"
    response += f"📤 Sent: {result['total_sent']:.8f} BTC\n"
    response += f"🔄 Transactions: {result['transaction_count']}\n"
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def add_xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add one or multiple xpub keys to user's portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide xpub key(s) to save.\n\n"
            "Usage:\n"
            "• Single: /add_xpub <xpub_key>\n"
            "• Multiple: /add_xpub <xpub1> <xpub2> <xpub3>\n\n"
            "Example:\n"
            "/add_xpub xpub6CUGRUonZSQ4TWtTMmz...\n"
            "/add_xpub xpub6... ypub6... zpub6...\n\n"
            "Supported: xpub, ypub, zpub"
        )
        return
    
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    # Process all provided xpub keys
    added = []
    skipped = []
    invalid = []
    
    for xpub in context.args:
        # Remove commas if user separated with commas
        xpub = xpub.strip(',').strip()
        
        if not is_valid_xpub(xpub):
            invalid.append(xpub[:20] + '...')
            continue
        
        # Check if already saved
        if xpub in addresses['xpub']:
            skipped.append(xpub)
            continue
        
        addresses['xpub'].append(xpub)
        added.append(xpub)
    
    # Build response
    if added:
        if save_addresses(user_id, addresses):
            response = f"✅ **Added {len(added)} HD Wallet(s)!**\n\n"
            
            # Show added xpub keys (limit to 3 in display)
            for i, xpub in enumerate(added[:3], 1):
                response += f"{i}. `{xpub[:15]}...{xpub[-10:]}`\n"
            
            if len(added) > 3:
                response += f"... and {len(added) - 3} more\n"
            
            response += f"\n📊 Total tracked: {len(addresses['xpub'])} HD wallet(s)\n"
            
            if skipped:
                response += f"\nℹ️ Skipped {len(skipped)} duplicate(s)"
            
            if invalid:
                response += f"\n⚠️ Ignored {len(invalid)} invalid key(s)"
            
            response += "\n\n💡 Use /portfolio to see your total value!"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to save xpub keys. Please try again.")
    else:
        response = "❌ No new HD wallets added.\n\n"
        if skipped:
            response += f"• {len(skipped)} already in portfolio\n"
        if invalid:
            response += f"• {len(invalid)} invalid key(s)\n"
        await update.message.reply_text(response)


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's complete portfolio value."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if not addresses['eth'] and not addresses['btc'] and not addresses['xpub']:
        await update.message.reply_text(
            "📭 You don't have any saved addresses yet.\n\n"
            "Add addresses to start tracking your portfolio:\n"
            "/add_eth <address> - Add Ethereum address\n"
            "/add_btc <address> - Add Bitcoin address\n"
            "/add_xpub <xpub_key> - Add HD wallet"
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 Calculating your portfolio value...\n"
        "📊 Fetching tokens and DeFi positions...\n"
        "This may take a moment ⏳"
    )
    
    # Get portfolio value (including tokens and DeFi)
    portfolio = await get_portfolio_value(
        addresses['eth'], 
        addresses['btc'], 
        addresses['xpub'],
        addresses.get('tokens', []),
        addresses.get('track_defi', True)
    )
    
    # Save portfolio snapshot for historical tracking
    save_portfolio_snapshot(
        user_id,
        portfolio['total_portfolio_usd'],
        portfolio['total_eth'],
        portfolio['total_btc_combined'],
        portfolio['eth_price'],
        portfolio['btc_price']
    )
    
    # Calculate 24h change
    change_data = calculate_24h_change(user_id, portfolio['total_portfolio_usd'])
    
    # Build response
    response = "💼 **YOUR PORTFOLIO**\n\n"
    response += "═" * 30 + "\n\n"
    
    # Total Portfolio Value
    response += f"🎯 **TOTAL VALUE: ${portfolio['total_portfolio_usd']:,.2f}**\n\n"
    
    # Show 24h change if available
    if change_data['has_data']:
        change_usd = change_data['change_usd']
        change_pct = change_data['change_percent']
        
        # Determine arrow and emoji based on change
        if change_usd > 0:
            arrow = "📈"
            sign = "+"
            color_emoji = "🟢"
        elif change_usd < 0:
            arrow = "📉"
            sign = ""
            color_emoji = "🔴"
        else:
            arrow = "➡️"
            sign = ""
            color_emoji = "⚪️"
        
        response += f"{arrow} **24h Change: {sign}${abs(change_usd):,.2f} ({sign}{change_pct:+.2f}%)**\n"
        response += f"{color_emoji} Previous: ${change_data['old_value']:,.2f}\n\n"
    else:
        response += "ℹ️ _Check back in 24h to see price changes_\n\n"
    
    response += "─" * 30 + "\n\n"
    
    # ETH Summary
    if portfolio['total_eth'] > 0:
        response += f"⟠ **Ethereum**\n"
        response += f"Total: {portfolio['total_eth']:.6f} ETH\n"
        response += f"Value: ${portfolio['total_eth_usd']:,.2f}\n"
        response += f"Price: ${portfolio['eth_price']:,.2f}\n"
        response += f"Addresses: {len(addresses['eth'])}\n\n"
    
    # BTC Summary (combined from addresses and xpub)
    if portfolio['total_btc_combined'] > 0:
        response += f"₿ **Bitcoin**\n"
        response += f"Total: {portfolio['total_btc_combined']:.8f} BTC\n"
        response += f"Value: ${portfolio['total_btc_usd']:,.2f}\n"
        response += f"Price: ${portfolio['btc_price']:,.2f}\n"
        
        # Show breakdown if both addresses and xpub exist
        if portfolio['total_btc'] > 0 and portfolio['total_btc_xpub'] > 0:
            response += f"  • Addresses: {portfolio['total_btc']:.8f} BTC ({len(addresses['btc'])})\n"
            response += f"  • HD Wallets: {portfolio['total_btc_xpub']:.8f} BTC ({len(addresses['xpub'])})\n"
        elif portfolio['total_btc'] > 0:
            response += f"Addresses: {len(addresses['btc'])}\n"
        elif portfolio['total_btc_xpub'] > 0:
            response += f"HD Wallets: {len(addresses['xpub'])}\n"
        response += "\n"
    
    # ERC20 Tokens Summary
    token_data = portfolio.get('token_data', {})
    if token_data.get('total_value_usd', 0) > 0:
        response += f"🪙 **ERC20 Tokens**\n"
        response += f"Total Value: ${token_data['total_value_usd']:,.2f}\n"
        response += f"Tokens: {token_data['token_count']}\n"
        
        # Show top 5 tokens
        top_tokens = token_data.get('balances', [])[:5]
        if top_tokens:
            response += "\nTop Holdings:\n"
            for token in top_tokens:
                response += f"  • {token['balance']:.4f} {token['symbol']} (${token['value_usd']:,.2f})\n"
        
        if token_data['token_count'] > 5:
            response += f"  ... and {token_data['token_count'] - 5} more\n"
        
        response += f"\n💡 Use /tokens to see all tokens\n\n"
    
    # DeFi Positions Summary
    defi_data = portfolio.get('defi_data', {})
    if defi_data.get('position_count', 0) > 0:
        response += f"🏦 **DeFi Positions**\n"
        response += f"Net Value: ${defi_data['total_net_value_usd']:,.2f}\n"
        response += f"Collateral: ${defi_data['total_collateral_usd']:,.2f}\n"
        response += f"Debt: ${defi_data['total_debt_usd']:,.2f}\n"
        response += f"Positions: {defi_data['position_count']}\n"
        response += f"\n💡 Use /defi to see details\n\n"
    
    response += "─" * 30 + "\n\n"
    
    # Allocation
    if portfolio['total_portfolio_usd'] > 0:
        components = []
        if portfolio['total_eth'] > 0:
            eth_pct = (portfolio['total_eth_usd'] / portfolio['total_portfolio_usd']) * 100
            components.append(f"ETH: {eth_pct:.1f}%")
        if portfolio['total_btc_combined'] > 0:
            btc_pct = (portfolio['total_btc_usd'] / portfolio['total_portfolio_usd']) * 100
            components.append(f"BTC: {btc_pct:.1f}%")
        if token_data.get('total_value_usd', 0) > 0:
            token_pct = (token_data['total_value_usd'] / portfolio['total_portfolio_usd']) * 100
            components.append(f"Tokens: {token_pct:.1f}%")
        if defi_data.get('total_net_value_usd', 0) > 0:
            defi_pct = (defi_data['total_net_value_usd'] / portfolio['total_portfolio_usd']) * 100
            components.append(f"DeFi: {defi_pct:.1f}%")
        
        if components:
            response += f"📊 **Allocation**\n"
            response += "\n".join(components)
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def addresses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved addresses."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if not addresses['eth'] and not addresses['btc'] and not addresses['xpub']:
        await update.message.reply_text(
            "📭 You don't have any saved addresses.\n\n"
            "Add addresses using:\n"
            "/add_eth <address>\n"
            "/add_btc <address>\n"
            "/add_xpub <xpub_key>"
        )
        return
    
    response = "📋 **YOUR SAVED ADDRESSES**\n\n"
    
    if addresses['eth']:
        response += f"⟠ **Ethereum ({len(addresses['eth'])} address{'es' if len(addresses['eth']) > 1 else ''}):**\n"
        for i, addr in enumerate(addresses['eth'], 1):
            response += f"{i}. `{addr[:10]}...{addr[-8:]}`\n"
        response += "\n"
    
    if addresses['btc']:
        response += f"₿ **Bitcoin ({len(addresses['btc'])} address{'es' if len(addresses['btc']) > 1 else ''}):**\n"
        for i, addr in enumerate(addresses['btc'], 1):
            response += f"{i}. `{addr}`\n"
        response += "\n"
    
    if addresses['xpub']:
        response += f"🔑 **HD Wallets ({len(addresses['xpub'])} xpub key{'s' if len(addresses['xpub']) > 1 else ''}):**\n"
        for i, xpub in enumerate(addresses['xpub'], 1):
            response += f"{i}. `{xpub[:15]}...{xpub[-10:]}`\n"
        response += "\n"
    
    response += "\n💡 Use /portfolio to see your total value"
    
    await update.message.reply_text(response, parse_mode='Markdown')


async def remove_eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove an Ethereum address from portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an Ethereum address to remove.\n"
            "Usage: /remove_eth <address>\n\n"
            "💡 Use /addresses to see your saved addresses"
        )
        return
    
    address = context.args[0]
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    # Find and remove address (case-insensitive)
    original_len = len(addresses['eth'])
    addresses['eth'] = [a for a in addresses['eth'] if a.lower() != address.lower()]
    
    if len(addresses['eth']) < original_len:
        if save_addresses(user_id, addresses):
            await update.message.reply_text(
                f"✅ ETH address removed from your portfolio.\n\n"
                f"Remaining addresses: {len(addresses['eth'])}"
            )
        else:
            await update.message.reply_text("❌ Failed to remove address. Please try again.")
    else:
        await update.message.reply_text("❌ Address not found in your portfolio.")


async def remove_btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a Bitcoin address from portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Bitcoin address to remove.\n"
            "Usage: /remove_btc <address>\n\n"
            "💡 Use /addresses to see your saved addresses"
        )
        return
    
    address = context.args[0]
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if address in addresses['btc']:
        addresses['btc'].remove(address)
        if save_addresses(user_id, addresses):
            await update.message.reply_text(
                f"✅ BTC address removed from your portfolio.\n\n"
                f"Remaining addresses: {len(addresses['btc'])}"
            )
        else:
            await update.message.reply_text("❌ Failed to remove address. Please try again.")
    else:
        await update.message.reply_text("❌ Address not found in your portfolio.")


async def remove_xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove an xpub key from portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an xpub key to remove.\n"
            "Usage: /remove_xpub <xpub_key>\n\n"
            "💡 Use /addresses to see your saved xpub keys"
        )
        return
    
    xpub = context.args[0]
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if xpub in addresses['xpub']:
        addresses['xpub'].remove(xpub)
        if save_addresses(user_id, addresses):
            await update.message.reply_text(
                f"✅ HD Wallet (xpub) removed from your portfolio.\n\n"
                f"Remaining xpub keys: {len(addresses['xpub'])}"
            )
        else:
            await update.message.reply_text("❌ Failed to remove xpub. Please try again.")
    else:
        await update.message.reply_text("❌ xpub not found in your portfolio.")


async def tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all ERC20 token balances."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if not addresses['eth']:
        await update.message.reply_text(
            "📭 You don't have any saved ETH addresses yet.\n\n"
            "Add addresses to track tokens:\n"
            "/add_eth <address> - Add Ethereum address"
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 Fetching token balances...\n"
        "This may take a moment ⏳"
    )
    
    # Get token balances
    token_data = await get_all_token_balances(addresses['eth'], addresses.get('tokens', []))
    
    if token_data['token_count'] == 0:
        await processing_msg.edit_text(
            "💭 No token balances found.\n\n"
            "Make sure you have tokens in your tracked addresses!"
        )
        return
    
    # Build response
    response = "🪙 **YOUR TOKEN HOLDINGS**\n\n"
    response += "═" * 30 + "\n\n"
    response += f"💰 **Total Value: ${token_data['total_value_usd']:,.2f}**\n"
    response += f"📊 Tokens: {token_data['token_count']}\n\n"
    response += "─" * 30 + "\n\n"
    
    # Group tokens by chain
    tokens_by_chain = {}
    for token in token_data['balances']:
        chain_name = token.get('chain_name', token['chain'])
        if chain_name not in tokens_by_chain:
            tokens_by_chain[chain_name] = []
        tokens_by_chain[chain_name].append(token)
    
    # Display tokens by chain
    for chain_name, tokens in tokens_by_chain.items():
        chain_emoji = ALL_CHAINS.get(tokens[0]['chain'], {}).get('emoji', '🔗')
        response += f"{chain_emoji} **{chain_name}**\n"
        
        for token in tokens:
            response += f"  • {token['balance']:.4f} {token['symbol']}\n"
            response += f"    ${token['value_usd']:,.2f} (@ ${token['price_usd']:,.4f})\n"
        
        response += "\n"
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all DeFi positions."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if not addresses['eth']:
        await update.message.reply_text(
            "📭 You don't have any saved ETH addresses yet.\n\n"
            "Add addresses to track DeFi positions:\n"
            "/add_eth <address> - Add Ethereum address"
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 Fetching DeFi positions...\n"
        "This may take a moment ⏳"
    )
    
    # Get DeFi positions
    defi_data = await get_all_defi_positions(addresses['eth'])
    
    if defi_data['position_count'] == 0:
        await processing_msg.edit_text(
            "💭 No DeFi positions found.\n\n"
            "Supported protocols:\n"
            "• Aave V3 (Ethereum, Arbitrum, Optimism, Base, Polygon)"
        )
        return
    
    # Build response
    response = "🏦 **YOUR DeFi POSITIONS**\n\n"
    response += "═" * 30 + "\n\n"
    response += f"💰 **Net Value: ${defi_data['total_net_value_usd']:,.2f}**\n"
    response += f"📊 Positions: {defi_data['position_count']}\n\n"
    response += f"🔒 Total Collateral: ${defi_data['total_collateral_usd']:,.2f}\n"
    response += f"💳 Total Debt: ${defi_data['total_debt_usd']:,.2f}\n\n"
    response += "─" * 30 + "\n\n"
    
    # Display individual positions
    for position in defi_data['positions']:
        chain_emoji = ALL_CHAINS.get(position['chain'], {}).get('emoji', '🔗')
        response += f"{chain_emoji} **{position['protocol']} - {position['chain_name']}**\n"
        response += f"  Collateral: ${position['total_collateral_usd']:,.2f}\n"
        response += f"  Debt: ${position['total_debt_usd']:,.2f}\n"
        response += f"  Net: ${position['net_value_usd']:,.2f}\n"
        
        # Health factor warning
        hf = position.get('health_factor', 0)
        debt = position.get('total_debt_usd', 0)
        
        if debt == 0 or hf > 100000:
            # No debt means infinite health factor
            response += f"  ✅ Health Factor: ∞ (No Debt)\n"
        elif hf > 0:
            if hf < 1.5:
                response += f"  ⚠️ Health Factor: {hf:.2f} (RISKY!)\n"
            elif hf < 2.0:
                response += f"  ⚡ Health Factor: {hf:.2f} (Low)\n"
            else:
                response += f"  ✅ Health Factor: {hf:.2f}\n"
        
        response += "\n"
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def add_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a custom ERC20 token to track."""
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Please provide token details.\n\n"
            "Usage: /add_token <chain> <contract_address> <coingecko_id>\n\n"
            "Example:\n"
            "/add_token ethereum 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 uniswap\n\n"
            "Supported chains:\n"
            "ethereum, base, arbitrum, optimism, polygon"
        )
        return
    
    chain = context.args[0].lower()
    contract_address = context.args[1]
    coingecko_id = context.args[2]
    
    # Validate chain
    if chain not in web3_instances:
        await update.message.reply_text(
            f"❌ Unsupported chain: {chain}\n\n"
            "Supported chains:\n" + 
            ", ".join(web3_instances.keys())
        )
        return
    
    # Validate address format
    if not is_valid_ethereum_address(contract_address):
        await update.message.reply_text("❌ Invalid contract address format.")
        return
    
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    # Try to get token info
    processing_msg = await update.message.reply_text("🔄 Validating token...")
    
    # Test fetching token info
    try:
        w3 = web3_instances[chain]
        contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ERC20_ABI)
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        
        # Create token entry
        token_entry = {
            'chain': chain,
            'address': contract_address,
            'symbol': symbol,
            'decimals': decimals,
            'coingecko_id': coingecko_id
        }
        
        # Check if already added
        if 'tokens' not in addresses:
            addresses['tokens'] = []
        
        for existing in addresses['tokens']:
            if existing['address'].lower() == contract_address.lower() and existing['chain'] == chain:
                await processing_msg.edit_text("ℹ️ This token is already being tracked.")
                return
        
        addresses['tokens'].append(token_entry)
        
        if save_addresses(user_id, addresses):
            await processing_msg.edit_text(
                f"✅ **Token added successfully!**\n\n"
                f"Token: {symbol}\n"
                f"Chain: {chain.capitalize()}\n"
                f"Address: `{contract_address[:10]}...{contract_address[-8:]}`\n\n"
                f"💡 Use /portfolio to see it in your holdings!",
                parse_mode='Markdown'
            )
        else:
            await processing_msg.edit_text("❌ Failed to save token. Please try again.")
    
    except Exception as e:
        logger.error(f"Error adding token: {e}")
        await processing_msg.edit_text(
            f"❌ Failed to validate token.\n\n"
            f"Error: {str(e)}\n\n"
            "Please verify:\n"
            "• Contract address is correct\n"
            "• Token is ERC20 standard\n"
            "• Chain is correct"
        )


async def toggle_defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle DeFi position tracking on/off."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    current_status = addresses.get('track_defi', True)
    addresses['track_defi'] = not current_status
    
    if save_addresses(user_id, addresses):
        status_text = "enabled ✅" if addresses['track_defi'] else "disabled ❌"
        await update.message.reply_text(
            f"DeFi position tracking is now **{status_text}**\n\n"
            f"Use /portfolio to see updated results.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to update settings. Please try again.")



async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot."""
    # Check if token is provided
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("❌ Error: Please set TELEGRAM_BOT_TOKEN in your .env file")
        return
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chains", chains_command))
    application.add_handler(CommandHandler("eth", eth_command))
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("xpub", xpub_command))
    
    # Portfolio management commands
    application.add_handler(CommandHandler("add_eth", add_eth_command))
    application.add_handler(CommandHandler("add_btc", add_btc_command))
    application.add_handler(CommandHandler("add_xpub", add_xpub_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("addresses", addresses_command))
    application.add_handler(CommandHandler("remove_eth", remove_eth_command))
    application.add_handler(CommandHandler("remove_btc", remove_btc_command))
    application.add_handler(CommandHandler("remove_xpub", remove_xpub_command))
    
    # Token and DeFi commands
    application.add_handler(CommandHandler("tokens", tokens_command))
    application.add_handler(CommandHandler("defi", defi_command))
    application.add_handler(CommandHandler("add_token", add_token_command))
    application.add_handler(CommandHandler("toggle_defi", toggle_defi_command))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    logger.info("Starting Akitafolio...")
    print("🐕 Akitafolio is running...")
    print(f"📡 Monitoring {len(ALL_CHAINS)} EVM chains + Bitcoin")
    print(f"💼 Portfolio tracking enabled (ETH, BTC, xpub)")
    print(f"🔑 HD Wallet support via Blockchain.info API")
    print(f"📊 24h portfolio change tracking enabled")
    print(f"🪙 ERC20 token tracking enabled")
    print(f"🏦 DeFi position tracking enabled (Aave V3)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
