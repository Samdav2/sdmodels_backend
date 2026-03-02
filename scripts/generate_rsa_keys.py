"""
Generate RSA key pair for JWT token encryption
Run this once to generate keys, then add them to .env
"""
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def generate_rsa_keys():
    """Generate RSA private and public keys"""
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get private key in PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key in PEM format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Save to files
    with open('private_key.pem', 'wb') as f:
        f.write(private_pem)
    
    with open('public_key.pem', 'wb') as f:
        f.write(public_pem)
    
    print("✅ RSA keys generated successfully!")
    print("\n📁 Files created:")
    print("   - private_key.pem (Keep this SECRET!)")
    print("   - public_key.pem")
    print("\n⚠️  IMPORTANT:")
    print("   1. Add private_key.pem to .gitignore")
    print("   2. Never commit private_key.pem to version control")
    print("   3. Store private_key.pem securely in production")
    print("\n📝 Add to .env:")
    print("   JWT_PRIVATE_KEY_PATH=private_key.pem")
    print("   JWT_PUBLIC_KEY_PATH=public_key.pem")
    print("   JWT_ALGORITHM=RS256")
    
    # Print keys for .env (base64 encoded for easy storage)
    import base64
    print("\n" + "="*70)
    print("OR store keys directly in .env (base64 encoded):")
    print("="*70)
    print(f"\nJWT_PRIVATE_KEY={base64.b64encode(private_pem).decode()}")
    print(f"\nJWT_PUBLIC_KEY={base64.b64encode(public_pem).decode()}")

if __name__ == "__main__":
    generate_rsa_keys()
