"""
Encryption utilities for sensitive data
"""

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption manager
        
        Args:
            key: 32-byte encryption key or None to generate new
        """
        if key:
            # Use provided key
            if len(key) != 32:
                raise ValueError("Encryption key must be exactly 32 bytes")
            # Convert string key to Fernet key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'stable_salt',  # In production, use random salt
                iterations=100000,
            )
            key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            self.cipher = Fernet(key_bytes)
        else:
            # Generate new key
            self.cipher = Fernet(Fernet.generate_key())
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        try:
            decoded = base64.b64decode(ciphertext.encode('utf-8'))
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted fields
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Decrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted fields
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except Exception as e:
                    # If decryption fails, keep the original value
                    # This handles cases where data was not encrypted
                    print(f"Warning: Decryption failed for field {field}, keeping original value")
                    pass
        return result

# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None

def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager"""
    global _encryption_manager
    if _encryption_manager is None:
        from src.config import settings
        key = settings.encryption_key or "default_32_byte_key_for_testing!"
        _encryption_manager = EncryptionManager(key)
    return _encryption_manager