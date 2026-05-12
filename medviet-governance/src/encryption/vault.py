# src/encryption/vault.py
import base64
import json
import os

import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SimpleVault:
    """
    Local envelope encryption helper.

    Architecture:
        Master Key (KEK) -> encrypts -> Data Key (DEK) -> encrypts -> Data
    """

    def __init__(self, master_key_path: str = ".vault_key"):
        self.master_key_path = master_key_path
        self.kek = self._load_or_create_kek()

    def _load_or_create_kek(self) -> bytes:
        """
        Load an existing 32-byte KEK or create and persist one locally.
        """
        if os.path.exists(self.master_key_path):
            with open(self.master_key_path, "rb") as key_file:
                return base64.b64decode(key_file.read())

        kek = os.urandom(32)
        with open(self.master_key_path, "wb") as key_file:
            key_file.write(base64.b64encode(kek))
        return kek

    def generate_dek(self) -> tuple[bytes, bytes]:
        """
        Generate a new Data Encryption Key and encrypt it with the KEK.
        """
        plaintext_dek = os.urandom(32)
        aesgcm = AESGCM(self.kek)
        nonce = os.urandom(12)
        encrypted_dek = nonce + aesgcm.encrypt(nonce, plaintext_dek, None)
        return plaintext_dek, encrypted_dek

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        """
        Decrypt an encrypted DEK using the KEK.
        """
        nonce = encrypted_dek[:12]
        ciphertext = encrypted_dek[12:]
        aesgcm = AESGCM(self.kek)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_data(self, plaintext: str) -> dict:
        """
        Encrypt plaintext using a fresh DEK protected by the KEK.
        """
        plaintext_dek, encrypted_dek = self.generate_dek()
        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, str(plaintext).encode("utf-8"), None)

        del plaintext_dek

        return {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("utf-8"),
            "ciphertext": base64.b64encode(nonce + ciphertext).decode("utf-8"),
            "algorithm": "AES-256-GCM",
        }

    def decrypt_data(self, encrypted_payload: dict) -> str:
        """
        Decrypt data from an envelope-encrypted payload.
        """
        encrypted_dek = base64.b64decode(encrypted_payload["encrypted_dek"])
        ciphertext_with_nonce = base64.b64decode(encrypted_payload["ciphertext"])

        plaintext_dek = self.decrypt_dek(encrypted_dek)
        nonce = ciphertext_with_nonce[:12]
        ciphertext = ciphertext_with_nonce[12:]

        aesgcm = AESGCM(plaintext_dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        del plaintext_dek

        return plaintext.decode("utf-8")

    def encrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Encrypt a DataFrame column and store each payload as a JSON string.
        """
        df_encrypted = df.copy()
        df_encrypted[column] = df_encrypted[column].apply(
            lambda value: json.dumps(self.encrypt_data(str(value)))
        )
        return df_encrypted
