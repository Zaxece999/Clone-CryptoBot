import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class SecurityManager:
    def __init__(self):
        self.encryption_key = settings.wallet_encryption_key.encode()

    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        if salt is None:
            salt = b'cryptobot_salt_2024'

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_private_key(self, private_key: str, user_id: str) -> str:
        try:
            user_key = self._derive_key(f"{settings.wallet_encryption_key}_{user_id}")
            fernet = Fernet(user_key)

            encrypted_key = fernet.encrypt(private_key.encode())

            return base64.b64encode(encrypted_key).decode()

        except Exception as e:
            logger.error(
                "Failed to encrypt private key",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_private_key(self, encrypted_private_key: str, user_id: str) -> str:
        try:
            user_key = self._derive_key(f"{settings.wallet_encryption_key}_{user_id}")
            fernet = Fernet(user_key)

            encrypted_key = base64.b64decode(encrypted_private_key.encode())

            decrypted_key = fernet.decrypt(encrypted_key)

            return decrypted_key.decode()

        except Exception as e:
            logger.error(
                "Failed to decrypt private key",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Decryption failed: {str(e)}")

    def encrypt_data(self, data: str, key: str = None) -> str:
        try:
            if key is None:
                key = settings.wallet_encryption_key

            encryption_key = self._derive_key(key)
            fernet = Fernet(encryption_key)

            encrypted_data = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()

        except Exception as e:
            logger.error(
                "Failed to encrypt data",
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_data(self, encrypted_data: str, key: str = None) -> str:
        try:
            if key is None:
                key = settings.wallet_encryption_key

            encryption_key = self._derive_key(key)
            fernet = Fernet(encryption_key)

            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)

            return decrypted_data.decode()

        except Exception as e:
            logger.error(
                "Failed to decrypt data",
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Decryption failed: {str(e)}")

    def hash_data(self, data: str, salt: str = None) -> str:
        if salt:
            data = f"{data}{salt}"

        return hashlib.sha256(data.encode()).hexdigest()

    def verify_hash(self, data: str, hash_value: str, salt: str = None) -> bool:
        calculated_hash = self.hash_data(data, salt)
        return calculated_hash == hash_value


security_manager = SecurityManager()

def encrypt_data(data: str, key: str = None) -> str:
    return security_manager.encrypt_data(data, key)

def decrypt_data(encrypted_data: str, key: str = None) -> str:
    return security_manager.decrypt_data(encrypted_data, key)

def encrypt_private_key(private_key: str, user_id: str) -> str:
    return security_manager.encrypt_private_key(private_key, user_id)

def decrypt_private_key(encrypted_private_key: str, user_id: str) -> str:
    return security_manager.decrypt_private_key(encrypted_private_key, user_id)
