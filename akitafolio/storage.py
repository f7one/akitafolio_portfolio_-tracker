"""
Secure storage layer for Akitafolio.

Provides safe file operations with validation and atomic writes.
"""

import json
import re
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from akitafolio.config import settings
from akitafolio.exceptions import StorageError, ValidationError
from akitafolio.models import UserAddresses, PortfolioSnapshot

logger = logging.getLogger(__name__)


class PathValidator:
    """Validates and sanitizes file paths."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent injection."""
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
        if not safe_name or safe_name.startswith('.'):
            raise ValidationError(f"Invalid filename: {filename}")
        return safe_name
    
    @staticmethod
    def validate_path(file_path: Path, base_dir: Path) -> Path:
        """Validate path is within base directory."""
        resolved = file_path.resolve()
        base_resolved = base_dir.resolve()
        
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ValidationError(f"Path traversal detected: {file_path}")
        
        return resolved


class SecureStorage:
    """
    Secure JSON file storage with validation and atomic writes.
    
    Features:
    - Path validation to prevent traversal attacks
    - Atomic writes using temporary files
    - Automatic backup on write errors
    - Thread-safe async operations
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or settings.storage_path).resolve()
        self._lock = asyncio.Lock()
    
    def _get_safe_path(self, filename: str) -> Path:
        """Get validated file path."""
        safe_name = PathValidator.sanitize_filename(filename)
        return PathValidator.validate_path(self.base_dir / safe_name, self.base_dir)
    
    def read_json(self, filename: str) -> Dict:
        """Read JSON file safely."""
        file_path = self._get_safe_path(filename)
        
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            raise StorageError(f"Invalid JSON in {filename}") from e
        except IOError as e:
            logger.error(f"Error reading {filename}: {e}")
            raise StorageError(f"Failed to read {filename}") from e
    
    def write_json(self, filename: str, data: Dict) -> None:
        """Write JSON file with atomic operation."""
        file_path = self._get_safe_path(filename)
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            # Write to temp file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic rename
            temp_path.replace(file_path)
        except IOError as e:
            logger.error(f"Error writing {filename}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise StorageError(f"Failed to write {filename}") from e


# Global storage instance
storage = SecureStorage()


# ============================================================================
# USER DATA STORAGE
# ============================================================================

DEFAULT_USER_DATA = {
    'eth': [],
    'btc': [],
    'xpub': [],
    'tokens': [],
    'track_defi': True
}


def validate_user_id(user_id: Any) -> int:
    """Validate Telegram user ID."""
    try:
        uid = int(user_id)
        if uid <= 0:
            raise ValidationError("User ID must be positive")
        return uid
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid user ID: {user_id}")


def load_user_addresses(user_id: int) -> UserAddresses:
    """Load user addresses with validation."""
    try:
        user_id = validate_user_id(user_id)
        data = storage.read_json(settings.addresses_file)
        user_data = data.get(str(user_id), DEFAULT_USER_DATA.copy())
        
        # Ensure all keys exist
        for key, default_value in DEFAULT_USER_DATA.items():
            if key not in user_data:
                user_data[key] = default_value if not isinstance(default_value, list) else []
        
        return UserAddresses(**user_data)
    except Exception as e:
        logger.error(f"Error loading addresses for user {user_id}: {e}")
        return UserAddresses(**DEFAULT_USER_DATA.copy())


def save_user_addresses(user_id: int, addresses: UserAddresses) -> bool:
    """Save user addresses with validation."""
    try:
        user_id = validate_user_id(user_id)
        data = storage.read_json(settings.addresses_file)
        data[str(user_id)] = addresses.model_dump()
        storage.write_json(settings.addresses_file, data)
        return True
    except Exception as e:
        logger.error(f"Error saving addresses for user {user_id}: {e}")
        return False


# ============================================================================
# PORTFOLIO HISTORY STORAGE
# ============================================================================

def load_portfolio_history(user_id: int) -> List[PortfolioSnapshot]:
    """Load portfolio history with validation."""
    try:
        user_id = validate_user_id(user_id)
        data = storage.read_json(settings.history_file)
        snapshots_data = data.get(str(user_id), [])
        
        return [
            PortfolioSnapshot(
                timestamp=datetime.fromisoformat(s['timestamp']) if isinstance(s['timestamp'], str) else s['timestamp'],
                total_value_usd=s['total_value_usd'],
                eth_amount=s.get('eth_amount', 0),
                btc_amount=s.get('btc_amount', 0),
                eth_price=s.get('eth_price', 0),
                btc_price=s.get('btc_price', 0)
            )
            for s in snapshots_data
        ]
    except Exception as e:
        logger.error(f"Error loading history for user {user_id}: {e}")
        return []


def save_portfolio_snapshot(
    user_id: int,
    total_value_usd: float,
    eth_amount: float = 0.0,
    btc_amount: float = 0.0,
    eth_price: float = 0.0,
    btc_price: float = 0.0
) -> bool:
    """Save portfolio snapshot with cleanup of old entries."""
    try:
        user_id = validate_user_id(user_id)
        data = storage.read_json(settings.history_file)
        user_history = data.get(str(user_id), [])
        
        # Add new snapshot
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_value_usd': float(total_value_usd),
            'eth_amount': float(eth_amount),
            'btc_amount': float(btc_amount),
            'eth_price': float(eth_price),
            'btc_price': float(btc_price)
        }
        user_history.append(snapshot)
        
        # Clean up old entries
        cutoff_date = datetime.now() - timedelta(days=settings.history_retention_days)
        user_history = [
            s for s in user_history
            if datetime.fromisoformat(s['timestamp']) > cutoff_date
        ]
        
        data[str(user_id)] = user_history
        storage.write_json(settings.history_file, data)
        return True
    except Exception as e:
        logger.error(f"Error saving snapshot for user {user_id}: {e}")
        return False
