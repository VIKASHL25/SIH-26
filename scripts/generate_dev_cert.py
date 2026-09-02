import os
import sys
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevCertGenerator")

def generate_self_signed_cert():
    """Generates a self-signed dev certificate (certs/server.crt and certs/server.key)."""
    certs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../certs"))
    os.makedirs(certs_dir, exist_ok=True)
    
    cert_path = os.path.join(certs_dir, "server.crt")
    key_path = os.path.join(certs_dir, "server.key")
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        logger.info("Generating 2048-bit RSA private key using cryptography library...")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Karnataka"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Bengaluru"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DRDO-SIH-Novensis"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(sys.modules['ipaddress'].ip_address("127.0.0.1"))]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        logger.info(f"✅ Development TLS Certificate created successfully:")
        logger.info(f"   Certificate: {cert_path}")
        logger.info(f"   Private Key: {key_path}")
        return True
        
    except ImportError:
        logger.info("cryptography package not found, falling back to OpenSSL CLI generation...")
        import subprocess
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", key_path,
            "-out", cert_path, "-days", "365", "-nodes",
            "-subj", "/C=IN/ST=Karnataka/L=Bengaluru/O=DRDO-SIH-Novensis/CN=localhost"
        ]
        try:
            subprocess.run(cmd, check=True)
            logger.info("✅ Created certs via OpenSSL CLI.")
            return True
        except Exception as e:
            logger.error(f"Failed to generate dev certificates: {e}")
            logger.warning("Please install cryptography (`pip install cryptography`) or OpenSSL.")
            return False

if __name__ == "__main__":
    generate_self_signed_cert()
