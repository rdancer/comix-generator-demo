from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import cryptography.hazmat.primitives.serialization as serialization
from base64 import urlsafe_b64encode
import uuid
import urllib.parse
import sys
import os

# Set the BASE_URL for token generation
BASE_URL = "https://comix-generator.rdancer.org/"

# Generate RSA key pair
def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key

# Save RSA private key to a file
def save_private_key_to_file(private_key, filename, password=None):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()) if password else serialization.NoEncryption()
    )
    with open(filename, 'wb') as pem_out:
        pem_out.write(pem)

# Save RSA public key to a file
def save_public_key_to_file(public_key, filename):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(filename, 'wb') as pem_out:
        pem_out.write(pem)

# Check if the RSA key files exist, generate and save them if not
def check_or_create_keys(private_key_filename, public_key_filename):
    if not os.path.exists(private_key_filename) or not os.path.exists(public_key_filename):
        print("RSA key pair not found. Generating new keys...", file=sys.stderr)
        private_key = generate_rsa_key_pair()
        public_key = private_key.public_key()

        save_private_key_to_file(private_key, private_key_filename)
        save_public_key_to_file(public_key, public_key_filename)
        print("New RSA key pair generated.", file=sys.stderr)
    else:
        print("RSA key pair found. Using existing keys.", file=sys.stderr)

# Function to generate a token
def generate_token(quota, private_key):
    uuid_str = str(uuid.uuid4())
    token_str = f"{quota}|{uuid_str}"

    # Sign the token string
    signature = private_key.sign(
        token_str.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    
    # URL-safe base64 encode the signature
    encoded_signature = urlsafe_b64encode(signature).decode()

    # Construct the complete token
    token = f"{token_str}|{encoded_signature}"
    
    # URL-encode the token when appending to a URL
    url_encoded_token = urllib.parse.quote(token)
    complete_url = f"{BASE_URL}?token={url_encoded_token}"
    
    return complete_url

# Main function for command line usage
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: script.py <number_of_tokens>")
        sys.exit(1)

    num_tokens = sys.argv[1]
    private_key_filename = "private_key.pem"
    public_key_filename = "public_key.pem"

    # Check for existing RSA keys or create them
    check_or_create_keys(private_key_filename, public_key_filename)

    # Load the private key from file
    with open(private_key_filename, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)

    # Generate and output the token URL
    generated_url = generate_token(num_tokens, private_key)

    print(generated_url)

