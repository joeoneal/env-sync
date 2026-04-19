import os
import click
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
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