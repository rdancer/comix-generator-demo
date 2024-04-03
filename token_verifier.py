import sqlite3
import urllib.parse
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from base64 import urlsafe_b64decode
import sys
from typing import Union, Optional
import argparse

class TokenVerifier:
    def __init__(self, url_fragment: str):
        self.db_path = 'quota.db'
        self.initialize_database()
        
        # Extract and verify token from URL
        token = self.extract_token(url_fragment)
        self.quota, self.uuid, self.signature = self.parse_token(token)
        self.verify_signature(self.quota, self.uuid, self.signature)
        
        # Check and update database record for the token
        self.prepare_record(self.uuid, int(self.quota))
    
    def extract_token(self, url_fragment: str):
        # hack
        if url_fragment[0] in '0123456789':
            # This is just the bare token, already parsed
            return url_fragment
        # Parse the URL and extract the token from the query string
        parsed_url = urllib.parse.urlparse(url_fragment)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        token = query_params.get('token', [None])[0]
        if not token:
            raise ValueError("URL is malformed or doesn't contain a token")
        return token
    
    def parse_token(self, token: str):
        components = token.split('|')
        if len(components) != 3:
            raise ValueError("Token format is invalid")
        quota, uuid, signature = components
        return quota, uuid, signature
    
    def verify_signature(self, quota: str, uuid: str, signature: str):
        signature_bytes = urlsafe_b64decode(signature)
        data = f"{quota}|{uuid}".encode()
        
        with open("public_key.pem", "rb") as key_file:
            public_key = load_pem_public_key(key_file.read())
        
        try:
            public_key.verify(
                signature_bytes,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except Exception as e:
            raise ValueError("Signature verification failed") from e
    
    def initialize_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS quotas
                          (uuid TEXT PRIMARY KEY, quota INTEGER)''')
        conn.commit()
        conn.close()
    
    def prepare_record(self, uuid: str, quota: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO quotas (uuid, quota) VALUES (?, ?)", (uuid, quota))
        conn.commit()
        conn.close()
    
    def quota_remaining(self, token_count: int = 1) -> Union[int, None]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT quota FROM quotas WHERE uuid = ?", (self.uuid,))
        row = cursor.fetchone()
        if row and row[0] >= token_count:
            return row[0] - token_count
        return None
    
    def update_quota(self, spent_tokens: int) -> bool:
        if not self.quota_remaining(spent_tokens):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE quotas SET quota = quota - ? WHERE uuid = ?", (spent_tokens, self.uuid))
        conn.commit()
        conn.close()
        return True

def main(tokens, urls):
    for url in urls:
        try:
            verifier = TokenVerifier(url)
            remainder = verifier.quota_remaining(token_count=tokens)
            if remainder is None:
                raise Exception("Could not retrieve quota.")
            else:
                result = f"✅ {remainder:>5}"
        except Exception as e:
            result = f"❌     N/A"
        print(f"{result} {url}")

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='Check quota remaining for given URLs with an optional token spend override.')
    
    # Add an argument for token spend, defaulting to 1 if not provided
    parser.add_argument('--tokens', type=int, default=1, help='Number of tokens to spend (default: 1)')
    
    # Add an argument for URLs, expecting at least one
    parser.add_argument('urls', nargs='+', help='One or more URLs to check')

    # Parse the command-line arguments
    args = parser.parse_args()

    print(f"args.tokens: {args.tokens}")
    # Pass the parsed tokens and URLs to the main function
    main(args.tokens, args.urls)
