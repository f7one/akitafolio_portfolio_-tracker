import os
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from web3 import Web3
import requests
from dotenv import load_dotenv
from solana.rpc.api import Client as SolanaClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey as SolanaPubkey
import base58
import struct

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID', 'df20b3f6760a45ea87562328e8b02e19')
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

# Marginfi Program ID (used by 0.xyz)
MARGINFI_PROGRAM_ID = "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA"

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


# Storage Functions

def load_saved_addresses(user_id: int) -> dict:
    """Load saved addresses for a user."""
    try:
        if STORAGE_FILE.exists():
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                user_data = data.get(str(user_id), {'eth': [], 'btc': [], 'xpub': [], 'sol': []})
                # Ensure all keys exist for backward compatibility
                if 'xpub' not in user_data:
                    user_data['xpub'] = []
                if 'sol' not in user_data:
                    user_data['sol'] = []
                return user_data
        return {'eth': [], 'btc': [], 'xpub': [], 'sol': []}
    except Exception as e:
        logger.error(f"Error loading saved addresses: {e}")
        return {'eth': [], 'btc': [], 'xpub': [], 'sol': []}


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


def save_portfolio_snapshot(user_id: int, total_value_usd: float, eth_amount: float, btc_amount: float, sol_amount: float, eth_price: float, btc_price: float, sol_price: float):
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
            'sol_amount': sol_amount,
            'eth_price': eth_price,
            'btc_price': btc_price,
            'sol_price': sol_price
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
        return Web3.is_address(address)
    except:
        return False


def is_valid_bitcoin_address(address: str) -> bool:
    """Basic Bitcoin address validation."""
    if not address:
        return False
    
    if address.startswith('1') or address.startswith('3'):
        return 26 <= len(address) <= 35
    elif address.lower().startswith('bc1'):
        return 42 <= len(address) <= 90
    
    return False


def is_valid_solana_address(address: str) -> bool:
    """Validate Solana address format."""
    try:
        if not address or len(address) < 32 or len(address) > 44:
            return False
        # Try to create a Pubkey - will raise if invalid
        SolanaPubkey.from_string(address)
        return True
    except:
        return False


def is_valid_xpub(xpub: str) -> bool:
    """Validate xpub/ypub/zpub format."""
    if not xpub:
        return False
    
    # Check valid prefixes
    valid_prefixes = ['xpub', 'ypub', 'zpub', 'tpub', 'upub', 'vpub']
    if not any(xpub.startswith(prefix) for prefix in valid_prefixes):
        return False
    
    # Check length (typically 111 characters)
    if len(xpub) < 100 or len(xpub) > 120:
        return False
    
    return True


async def get_crypto_prices() -> dict:
    """Fetch current ETH, BTC, and SOL prices in USD from CoinGecko API."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin,solana&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'eth': float(data.get('ethereum', {}).get('usd', 0)),
                'btc': float(data.get('bitcoin', {}).get('usd', 0)),
                'sol': float(data.get('solana', {}).get('usd', 0))
            }
        else:
            logger.warning(f"Failed to fetch crypto prices: {response.status_code}")
            return {'eth': 0.0, 'btc': 0.0, 'sol': 0.0}
    except Exception as e:
        logger.error(f"Error fetching crypto prices: {e}")
        return {'eth': 0.0, 'btc': 0.0, 'sol': 0.0}


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
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            balance_satoshi = int(response.text)
            balance_btc = balance_satoshi / 100000000
            
            return {
                "success": True,
                "address": address,
                "balance": balance_btc,
                "currency": "BTC"
            }
        else:
            return {"error": f"API returned status code: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Error fetching Bitcoin balance: {e}")
        return {"error": f"Failed to fetch Bitcoin balance: {str(e)}"}


async def get_solana_balance(address: str) -> dict:
    """Fetch Solana wallet balance."""
    try:
        if not is_valid_solana_address(address):
            return {"error": "Invalid Solana address"}
        
        # Initialize Solana client
        client = SolanaClient(SOLANA_RPC_URL)
        
        # Get balance
        pubkey = SolanaPubkey.from_string(address)
        response = client.get_balance(pubkey)
        
        if response.value is not None:
            # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
            balance_sol = response.value / 1_000_000_000
            
            return {
                "success": True,
                "address": address,
                "balance": balance_sol,
                "currency": "SOL"
            }
        else:
            return {"error": "Failed to fetch balance"}
    
    except Exception as e:
        logger.error(f"Error fetching Solana balance: {e}")
        return {"error": f"Failed to fetch Solana balance: {str(e)}"}


async def get_marginfi_positions(address: str) -> dict:
    """Fetch DeFi positions from marginfi (0.xyz) by parsing on-chain accounts."""
    try:
        if not is_valid_solana_address(address):
            return {"error": "Invalid Solana address"}
        
        # Initialize Solana client
        client = SolanaClient(SOLANA_RPC_URL)
        user_pubkey = SolanaPubkey.from_string(address)
        marginfi_program = SolanaPubkey.from_string(MARGINFI_PROGRAM_ID)
        
        # Find marginfi accounts for this user using getProgramAccounts
        # We look for accounts owned by the marginfi program that are related to this user
        try:
            # Get all accounts owned by marginfi program filtered by user
            from solders.rpc.requests import GetProgramAccounts
            from solders.rpc.config import RpcAccountInfoConfig
            from solana.rpc.commitment import Confirmed
            
            # Try to find marginfi accounts associated with this user
            # Marginfi accounts have a specific discriminator and user authority field
            
            # Get all token accounts owned by the user to check for marginfi positions
            response = client.get_token_accounts_by_owner(
                user_pubkey,
                {"programId": SolanaPubkey.from_string("TokenkgQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")},
                commitment=Confirmed
            )
            
            supplies = []
            borrows = []
            total_supply_usd = 0
            total_borrow_usd = 0
            
            # Get SOL price for calculations
            prices = await get_crypto_prices()
            sol_price = prices.get('sol', 0)
            
            # Try to fetch user's marginfi account data directly
            # Marginfi uses a PDA (Program Derived Address) pattern
            # We need to derive the user's marginfi account address
            
            # Common seeds for marginfi accounts: ["marginfi_account", user_pubkey, account_index]
            # Let's try to find accounts with index 0, 1, 2 (most users have 0-2 accounts)
            
            has_positions = False
            
            for account_index in range(5):  # Check first 5 possible accounts
                try:
                    # Derive marginfi account PDA
                    seeds = [
                        b"marginfi_account",
                        bytes(user_pubkey),
                        account_index.to_bytes(8, 'little')
                    ]
                    
                    # Find PDA
                    marginfi_account, bump = SolanaPubkey.find_program_address(seeds, marginfi_program)
                    
                    # Try to fetch account data
                    account_info = client.get_account_info(marginfi_account, commitment=Confirmed)
                    
                    if account_info.value is None:
                        continue  # Account doesn't exist
                    
                    # Parse account data
                    data = account_info.value.data
                    
                    # Marginfi account structure (simplified):
                    # - First 8 bytes: discriminator
                    # - Next 32 bytes: authority (user pubkey)
                    # - Following bytes: lending positions
                    
                    if len(data) < 40:
                        continue
                    
                    # Verify this account belongs to our user
                    authority_bytes = data[8:40]
                    account_authority = SolanaPubkey(authority_bytes)
                    
                    if account_authority != user_pubkey:
                        continue
                    
                    # This user has a marginfi account
                    has_positions = True
                    
                    # Parse lending positions (structure varies by marginfi version)
                    # For now, we'll indicate positions exist but parsing full details
                    # requires more complex deserialization of the account data
                    
                    logger.info(f"Found marginfi account {account_index} for user {address}")
                    
                except Exception as e:
                    # Account doesn't exist or error reading it
                    logger.debug(f"No marginfi account at index {account_index}: {e}")
                    continue
            
            if has_positions:
                # If we found accounts but couldn't parse details, show a note
                return {
                    "success": True,
                    "address": address,
                    "has_positions": True,
                    "supplies": supplies,
                    "borrows": borrows,
                    "total_supply_usd": total_supply_usd,
                    "total_borrow_usd": total_borrow_usd,
                    "net_value_usd": total_supply_usd - total_borrow_usd,
                    "note": "Active marginfi positions detected! For detailed balance information, visit https://app.0.xyz/"
                }
            else:
                return {
                    "success": True,
                    "address": address,
                    "has_positions": False,
                    "supplies": [],
                    "borrows": [],
                    "total_supply_usd": 0,
                    "total_borrow_usd": 0,
                    "net_value_usd": 0
                }
                
        except Exception as e:
            logger.error(f"Error querying marginfi accounts: {e}")
            return {
                "success": False,
                "address": address,
                "has_positions": False,
                "supplies": [],
                "borrows": [],
                "total_supply_usd": 0,
                "total_borrow_usd": 0,
                "net_value_usd": 0,
                "error": f"Unable to query DeFi positions. Visit https://app.0.xyz/ to view your positions."
            }
    
    except Exception as e:
        logger.error(f"Error fetching marginfi positions: {e}")
        return {"error": f"Failed to fetch DeFi positions: {str(e)}"}


async def get_xpub_balance(xpub: str) -> dict:
    """Fetch Bitcoin HD wallet balance using xpub via Blockchain.info API."""
    try:
        if not is_valid_xpub(xpub):
            return {"error": "Invalid xpub format"}
        
        # Blockchain.info xpub balance endpoint
        url = f"https://blockchain.info/balance?active={xpub}"
        response = requests.get(url, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            
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
        else:
            return {"error": f"API returned status code: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Error fetching xpub balance: {e}")
        return {"error": f"Failed to fetch xpub balance: {str(e)}"}


async def get_portfolio_value(eth_addresses: list, btc_addresses: list, xpub_keys: list = None, sol_addresses: list = None) -> dict:
    """Calculate total portfolio value for multiple addresses and xpub keys."""
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
    
    # Fetch all SOL balances
    sol_addresses = sol_addresses or []
    sol_tasks = [get_solana_balance(addr) for addr in sol_addresses]
    sol_results = await asyncio.gather(*sol_tasks) if sol_addresses else []
    
    # Calculate totals
    total_eth = sum(r.get('total_eth', 0) for r in eth_results if 'error' not in r)
    total_btc = sum(r.get('balance', 0) for r in btc_results if 'error' not in r)
    total_btc_xpub = sum(r.get('balance', 0) for r in xpub_results if 'error' not in r)
    total_sol = sum(r.get('balance', 0) for r in sol_results if 'error' not in r)
    
    # Combine BTC from addresses and xpub
    total_btc_combined = total_btc + total_btc_xpub
    
    total_eth_usd = total_eth * prices['eth']
    total_btc_usd = total_btc_combined * prices['btc']
    total_sol_usd = total_sol * prices['sol']
    total_portfolio_usd = total_eth_usd + total_btc_usd + total_sol_usd
    
    return {
        'total_eth': total_eth,
        'total_btc': total_btc,
        'total_btc_xpub': total_btc_xpub,
        'total_btc_combined': total_btc_combined,
        'total_sol': total_sol,
        'eth_price': prices['eth'],
        'btc_price': prices['btc'],
        'sol_price': prices['sol'],
        'total_eth_usd': total_eth_usd,
        'total_btc_usd': total_btc_usd,
        'total_sol_usd': total_sol_usd,
        'total_portfolio_usd': total_portfolio_usd,
        'eth_results': eth_results,
        'btc_results': btc_results,
        'xpub_results': xpub_results,
        'sol_results': sol_results
    }


# Command Handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Welcome to the Multi-Chain Crypto Portfolio Tracker!\n\n"
        "I can help you track your crypto portfolio across multiple chains.\n\n"
        "📊 **Balance Commands:**\n"
        "/eth <address> - Check ETH balance across all chains\n"
        "/btc <address> - Check Bitcoin balance\n"
        "/sol <address> - Check Solana balance\n"
        "/defi <address> - Check DeFi positions on 0.xyz\n"
        "/xpub <xpub_key> - Check HD wallet balance (xpub/ypub/zpub)\n\n"
        "💼 **Portfolio Management:**\n"
        "/add_eth <addr1> <addr2> ... - Save ETH address(es)\n"
        "/add_btc <addr1> <addr2> ... - Save BTC address(es)\n"
        "/add_sol <addr1> <addr2> ... - Save SOL address(es)\n"
        "/add_xpub <key1> <key2> ... - Save HD wallet(s)\n"
        "/portfolio - View total portfolio value (with 24h change!)\n"
        "/addresses - List your saved addresses\n"
        "/remove_eth <address> - Remove ETH address\n"
        "/remove_btc <address> - Remove BTC address\n"
        "/remove_sol <address> - Remove SOL address\n"
        "/remove_xpub <xpub_key> - Remove HD wallet\n\n"
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
        "   /sol <address> - Check Solana balance\n"
        "   /defi <address> - Check DeFi positions on 0.xyz\n"
        "   /xpub <xpub_key> - Check HD wallet balance\n\n"
        "**2️⃣ Portfolio Tracking**\n"
        "   a) Save your addresses (single or multiple):\n"
        "      /add_eth 0xAddr1 0xAddr2 0xAddr3\n"
        "      /add_btc btcAddr1 btcAddr2\n"
        "      /add_sol solAddr1 solAddr2\n"
        "      /add_xpub xpub6... ypub6...\n\n"
        "   b) View total portfolio:\n"
        "      /portfolio\n"
        "      Shows total ETH + BTC + SOL value in USD!\n"
        "      Includes 24h price change tracking! 📈📉\n\n"
        "   c) Manage addresses:\n"
        "      /addresses - List saved addresses\n"
        "      /remove_eth <address> - Remove address\n\n"
        "**3️⃣ Supported Networks**\n"
        "   /chains - See all 8 EVM chains + Bitcoin + Solana\n\n"
        "💰 **Portfolio Features:**\n"
        "• Track multiple addresses\n"
        "• Aggregated ETH from all L1/L2 chains\n"
        "• 24-hour portfolio change tracking\n"
        "• Combined ETH + BTC + SOL USD value\n"
        "• DeFi positions on 0.xyz (Solana)\n"
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


async def sol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sol command to check Solana balance."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Solana address.\n"
            "Usage: /sol <solana_address>\n"
            "Example: /sol 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU\n\n"
            "💡 Tip: Use /add_sol to save addresses for portfolio tracking!"
        )
        return
    
    address = context.args[0]
    
    # Send "processing" message
    processing_msg = await update.message.reply_text("🔄 Fetching Solana balance...")
    
    # Get balance and price
    result = await get_solana_balance(address)
    prices = await get_crypto_prices()
    
    if "error" in result:
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
    else:
        sol_balance = result['balance']
        usd_value = sol_balance * prices['sol'] if prices['sol'] > 0 else 0
        
        response_message = (
            f"◎ **Solana Balance**\n\n"
            f"Address: `{result['address']}`\n"
            f"Balance: **{sol_balance:.6f} SOL**\n"
        )
        
        if prices['sol'] > 0:
            response_message += f"💵 USD Value: **${usd_value:,.2f}**\n"
            response_message += f"📈 SOL Price: ${prices['sol']:,.2f}"
        
        await processing_msg.edit_text(response_message, parse_mode='Markdown')


async def defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /defi command to check DeFi positions on 0.xyz (marginfi)."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Solana address.\n"
            "Usage: /defi <solana_address>\n"
            "Example: /defi 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU\n\n"
            "💡 This shows your lending/borrowing positions on 0.xyz"
        )
        return
    
    address = context.args[0]
    
    # Send "processing" message
    processing_msg = await update.message.reply_text("🔄 Fetching DeFi positions from 0.xyz...")
    
    # Get DeFi positions
    result = await get_marginfi_positions(address)
    
    if "error" in result:
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
    else:
        if not result['has_positions']:
            response_message = (
                f"🏦 **DeFi Positions (0.xyz)**\n\n"
                f"Address: `{address[:10]}...{address[-8:]}`\n\n"
            )
            
            if result.get('note'):
                response_message += f"{result['note']}\n\n"
            else:
                response_message += f"📭 No active positions found.\n\n"
            
            response_message += f"💡 Visit [app.0.xyz](https://app.0.xyz/) to start lending or borrowing!"
        else:
            response_message = (
                f"🏦 **DeFi Positions (0.xyz)**\n\n"
                f"Address: `{address[:10]}...{address[-8:]}`\n\n"
            )
            
            # Display supplies
            if result['supplies']:
                response_message += "📈 **Supplied:**\n"
                for supply in result['supplies']:
                    response_message += f"  • {supply['amount']:.4f} {supply['token']}"
                    if supply['usd'] > 0:
                        response_message += f" (${supply['usd']:,.2f})"
                    response_message += "\n"
                response_message += f"\n💰 Total Supply: **${result['total_supply_usd']:,.2f}**\n\n"
            
            # Display borrows
            if result['borrows']:
                response_message += "📉 **Borrowed:**\n"
                for borrow in result['borrows']:
                    response_message += f"  • {borrow['amount']:.4f} {borrow['token']}"
                    if borrow['usd'] > 0:
                        response_message += f" (${borrow['usd']:,.2f})"
                    response_message += "\n"
                response_message += f"\n💸 Total Borrow: **${result['total_borrow_usd']:,.2f}**\n\n"
            
            # Net value
            if result['total_supply_usd'] > 0 or result['total_borrow_usd'] > 0:
                response_message += f"📊 **Net Value:** ${result['net_value_usd']:,.2f}\n\n"
            
            if result.get('note'):
                response_message += f"ℹ️ {result['note']}\n\n"
            
            response_message += f"🔗 View full details: [app.0.xyz](https://app.0.xyz/)"
        
        await processing_msg.edit_text(response_message, parse_mode='Markdown', disable_web_page_preview=True)


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
    
    if not addresses['eth'] and not addresses['btc'] and not addresses['xpub'] and not addresses['sol']:
        await update.message.reply_text(
            "📭 You don't have any saved addresses yet.\n\n"
            "Add addresses to start tracking your portfolio:\n"
            "/add_eth <address> - Add Ethereum address\n"
            "/add_btc <address> - Add Bitcoin address\n"
            "/add_xpub <xpub_key> - Add HD wallet\n"
            "/add_sol <address> - Add Solana address"
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 Calculating your portfolio value...\n"
        "This may take a moment ⏳"
    )
    
    # Get portfolio value
    portfolio = await get_portfolio_value(addresses['eth'], addresses['btc'], addresses['xpub'], addresses['sol'])
    
    # Save portfolio snapshot for historical tracking
    save_portfolio_snapshot(
        user_id,
        portfolio['total_portfolio_usd'],
        portfolio['total_eth'],
        portfolio['total_btc_combined'],
        portfolio['total_sol'],
        portfolio['eth_price'],
        portfolio['btc_price'],
        portfolio['sol_price']
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
    
    # SOL Summary
    if portfolio['total_sol'] > 0:
        response += f"◎ **Solana**\n"
        response += f"Total: {portfolio['total_sol']:.6f} SOL\n"
        response += f"Value: ${portfolio['total_sol_usd']:,.2f}\n"
        response += f"Price: ${portfolio['sol_price']:,.2f}\n"
        response += f"Addresses: {len(addresses['sol'])}\n\n"
    
    response += "─" * 30 + "\n\n"
    
    # Allocation
    if portfolio['total_portfolio_usd'] > 0:
        eth_pct = (portfolio['total_eth_usd'] / portfolio['total_portfolio_usd']) * 100
        btc_pct = (portfolio['total_btc_usd'] / portfolio['total_portfolio_usd']) * 100
        sol_pct = (portfolio['total_sol_usd'] / portfolio['total_portfolio_usd']) * 100
        response += f"📊 **Allocation**\n"
        if portfolio['total_eth'] > 0:
            response += f"ETH: {eth_pct:.1f}%\n"
        if portfolio['total_btc'] > 0:
            response += f"BTC: {btc_pct:.1f}%\n"
        if portfolio['total_sol'] > 0:
            response += f"SOL: {sol_pct:.1f}%\n"
    
    await processing_msg.edit_text(response, parse_mode='Markdown')


async def addresses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved addresses."""
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if not addresses['eth'] and not addresses['btc'] and not addresses['xpub'] and not addresses['sol']:
        await update.message.reply_text(
            "📭 You don't have any saved addresses.\n\n"
            "Add addresses using:\n"
            "/add_eth <address>\n"
            "/add_btc <address>\n"
            "/add_xpub <xpub_key>\n"
            "/add_sol <address>"
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
    
    if addresses['sol']:
        response += f"◎ **Solana ({len(addresses['sol'])} address{'es' if len(addresses['sol']) > 1 else ''}):**\n"
        for i, addr in enumerate(addresses['sol'], 1):
            response += f"{i}. `{addr[:10]}...{addr[-8:]}`\n"
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


async def add_sol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add one or multiple Solana addresses to user's portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide Solana address(es) to save.\n\n"
            "Usage:\n"
            "• Single: /add_sol <address>\n"
            "• Multiple: /add_sol <addr1> <addr2> <addr3>\n\n"
            "Example:\n"
            "/add_sol 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU\n"
            "/add_sol SolAddr1 SolAddr2 SolAddr3"
        )
        return
    
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    added_count = 0
    skipped_count = 0
    invalid_count = 0
    
    for address_arg in context.args:
        # Split by comma if present, then strip whitespace
        potential_addresses = [addr.strip() for addr in address_arg.split(',') if addr.strip()]
        
        for address in potential_addresses:
            if not is_valid_solana_address(address):
                invalid_count += 1
                continue
            
            if address in addresses['sol']:
                skipped_count += 1
                continue
            
            addresses['sol'].append(address)
            added_count += 1
    
    if added_count > 0:
        if save_addresses(user_id, addresses):
            response_message = f"✅ Added {added_count} SOL address(es)!\n\n"
            # Show first 5 added addresses
            for i, addr in enumerate(addresses['sol'][-added_count:]):
                if i < 5:
                    response_message += f"{i+1}. `{addr[:10]}...{addr[-8:]}`\n"
            if added_count > 5:
                response_message += f"... and {added_count - 5} more.\n"
            
            response_message += f"\n📊 Total tracked: {len(addresses['sol'])} address(es)\n"
            response_message += f"\n💡 Use /portfolio to see your total value!"
            
            if skipped_count > 0:
                response_message += f"\nℹ️ {skipped_count} address(es) were already in your portfolio."
            if invalid_count > 0:
                response_message += f"\n❌ {invalid_count} address(es) had an invalid format."
            
            await update.message.reply_text(response_message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to save addresses. Please try again.")
    elif skipped_count > 0 or invalid_count > 0:
        response_message = ""
        if skipped_count > 0:
            response_message += f"ℹ️ {skipped_count} address(es) were already in your portfolio.\n"
        if invalid_count > 0:
            response_message += f"❌ {invalid_count} address(es) had an invalid format."
        await update.message.reply_text(response_message)
    else:
        await update.message.reply_text("⚠️ No valid new addresses provided.")


async def remove_sol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a Solana address from portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Solana address to remove.\n"
            "Usage: /remove_sol <address>\n\n"
            "💡 Use /addresses to see your saved addresses"
        )
        return
    
    address = context.args[0]
    user_id = update.effective_user.id
    addresses = load_saved_addresses(user_id)
    
    if address in addresses['sol']:
        addresses['sol'].remove(address)
        if save_addresses(user_id, addresses):
            await update.message.reply_text(
                f"✅ SOL address removed from your portfolio.\n\n"
                f"Remaining addresses: {len(addresses['sol'])}"
            )
        else:
            await update.message.reply_text("❌ Failed to remove address. Please try again.")
    else:
        await update.message.reply_text("❌ Address not found in your portfolio.")


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
    application.add_handler(CommandHandler("sol", sol_command))
    application.add_handler(CommandHandler("defi", defi_command))
    application.add_handler(CommandHandler("xpub", xpub_command))
    
    # Portfolio management commands
    application.add_handler(CommandHandler("add_eth", add_eth_command))
    application.add_handler(CommandHandler("add_btc", add_btc_command))
    application.add_handler(CommandHandler("add_sol", add_sol_command))
    application.add_handler(CommandHandler("add_xpub", add_xpub_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("addresses", addresses_command))
    application.add_handler(CommandHandler("remove_eth", remove_eth_command))
    application.add_handler(CommandHandler("remove_btc", remove_btc_command))
    application.add_handler(CommandHandler("remove_sol", remove_sol_command))
    application.add_handler(CommandHandler("remove_xpub", remove_xpub_command))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    logger.info("Starting bot...")
    print("🤖 Bot is running...")
    print(f"📡 Monitoring {len(ALL_CHAINS)} EVM chains + Bitcoin + Solana")
    print(f"💼 Portfolio tracking enabled (ETH, BTC, SOL, xpub)")
    print(f"🔑 HD Wallet support via Blockchain.info API")
    print(f"📊 24h portfolio change tracking enabled")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
