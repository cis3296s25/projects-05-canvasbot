from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import os
import stat
from nextcord.ext import commands

class RSA(commands.Cog): 
    def __init__(self, client):
        self.client = client
        
        # Check if there is a .key file
        # If not, create one with a new RSA key pair
        self.filePath = os.path.join(os.getcwd(), ".key")
        try:
            with open(self.filePath, "rb") as keyFile:
                self.privateKey = serialization.load_pem_private_key(
                    keyFile.read(),
                    password=None,
                    backend=default_backend()
                )
        except (FileNotFoundError, ValueError):

            # Generate a new RSA key pair
            self.privateKey = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Save the private key to .key file
            with open(self.filePath, "wb") as keyFile:
                keyFile.write(self.privateKey.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Set the file permissions to read-only
            os.chmod(self.filePath, stat.S_IREAD)

        self.publicKey = self.privateKey.public_key()
    # Encrypt the API key using the public key
    async def encryptAPIKey(self, key: str):
        ciphertext = self.publicKey.encrypt(
            key.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    async def decryptAPIKey(self, ciphertext: bytes):
        # Decrypt the ciphertext using the private key
        plaintext = self.privateKey.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return plaintext.decode()
    
def setup(client):
    client.add_cog(RSA(client))