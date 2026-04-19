import os
import click
import requests
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cli.utils.config import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, BASE_URL

def gen_keypair_if_none(token):
    """Generates RSA key pair if one doesn't already exists locally"""
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        return
    
    click.echo("Generating your unique end-to-end ecryption key pair...")

    priv = rsa.generate_private_key(
        public_exponent = 65537, 
        key_size = 2048
    )

    pub = priv.public_key()

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save Public Key (This goes to the server)
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    click.secho("Key pair generated successfully!", fg="green")

    click.secho('Uploading public key to server...', fg='blue')
    with open(PUBLIC_KEY_FILE, 'r') as f:
        pub_text = f.read()

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(f"{BASE_URL}/public_key", json={"public_key": pub_text}, headers=headers)
        if response.status_code == 200:
            click.secho("Public key securely registered with server!", fg="green")
        else:
            click.secho(f"Failed to upload public key: {response.text}", fg="red")
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server to upload key.", fg="red")


class CryptoEngine:
    @staticmethod
    def generate_vault_key() -> bytes:
        """Generates the master symmetric key for the team's vault."""
        return Fernet.generate_key()

    @staticmethod
    def wrap_key(vault_key: bytes, public_key_pem: str) -> str:
        """Encrypts the Vault Key using an RSA Public Key (Creates the Envelope)."""
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        encrypted_key = public_key.encrypt(
            vault_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        # Return as a base64 string so it can be safely sent via JSON
        return base64.b64encode(encrypted_key).decode('utf-8')

    @staticmethod
    def unwrap_key(encrypted_key_b64: str, private_key_pem: str) -> bytes:
        """Decrypts the Envelope using the user's local RSA Private Key."""
        private_key = serialization.load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
        encrypted_key = base64.b64decode(encrypted_key_b64)
        
        vault_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return vault_key

    @staticmethod
    def encrypt_env(env_text: str, vault_key: bytes) -> str:
        """Encrypts the massive .env payload using the symmetric Vault Key."""
        f = Fernet(vault_key)
        encrypted_data = f.encrypt(env_text.encode('utf-8'))
        return encrypted_data.decode('utf-8')

    @staticmethod
    def decrypt_env(env_blob: str, vault_key: bytes) -> str:
        """Decrypts the .env payload."""
        f = Fernet(vault_key)
        decrypted_data = f.decrypt(env_blob.encode('utf-8'))
        return decrypted_data.decode('utf-8')