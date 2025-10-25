"""
GLPI Agent HTTPS Protocol Handler - Python Implementation

"""

import hashlib
import os
import ssl
import warnings
from typing import Optional, Union, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import urllib3


class GLPIHTTPSAdapter(HTTPAdapter):
    """
    Custom HTTPS adapter equivalent to GLPI::Agent::HTTP::Protocol::https.
    Handles SSL/TLS with custom certificate verification.
    """
    
    def __init__(self, 
                 ssl_verify: bool = True,
                 ca_cert_file: Optional[str] = None,
                 ca_cert_dir: Optional[str] = None,
                 ssl_cert_file: Optional[str] = None,
                 ssl_key_file: Optional[str] = None,
                 ssl_ca: Optional[str] = None,
                 ssl_fingerprint: Optional[Union[str, List[str]]] = None,
                 verify_hostname: bool = True,
                 **kwargs):
        
        self.ssl_verify = ssl_verify
        self.ca_cert_file = ca_cert_file or ssl_ca
        self.ca_cert_dir = ca_cert_dir
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.ssl_fingerprint = ssl_fingerprint
        self.verify_hostname = verify_hostname
        
        if isinstance(ssl_fingerprint, str):
            self.ssl_fingerprint = [ssl_fingerprint]
        
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        """Equivalent to _extra_sock_opts in Perl code."""
        context = self._create_ssl_context()
        kwargs['ssl_context'] = context
        self.poolmanager = PoolManager(*args, **kwargs)
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Creates SSL context with verification settings.
        Equivalent to SSL_verify_mode, SSL_verifycn_scheme, SSL_verifycn_name.
        """
        if self.ssl_verify:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = self.verify_hostname  # SSL_verifycn_scheme => 'http'
            context.verify_mode = ssl.CERT_REQUIRED  # SSL_VERIFY_PEER
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # SSL_VERIFY_NONE
        
        # Load CA certificates (set_ctx_defaults equivalents)
        if self.ca_cert_file and os.path.isfile(self.ca_cert_file):
            context.load_verify_locations(cafile=self.ca_cert_file)
        
        if self.ca_cert_dir and os.path.isdir(self.ca_cert_dir):
            context.load_verify_locations(capath=self.ca_cert_dir)
        
        # Load client certificate
        if self.ssl_cert_file:
            context.load_cert_chain(
                certfile=self.ssl_cert_file,
                keyfile=self.ssl_key_file
            )
        
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA')
        
        return context
    
    def cert_verify(self, conn, url, verify, cert):
        """Override for fingerprint verification."""
        super().cert_verify(conn, url, verify, cert)
        
        if self.ssl_fingerprint and verify:
            self._verify_fingerprint(conn, url)
    
    def _verify_fingerprint(self, conn, url):
        """Verify certificate fingerprint (ssl_fingerprint parameter)."""
        cert_der = conn.sock.getpeercert(binary_form=True)
        
        if not cert_der:
            raise ssl.SSLError("Unable to retrieve peer certificate")
        
        sha256_fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
        sha1_fingerprint = hashlib.sha1(cert_der).hexdigest().upper()
        
        sha256_formatted = ':'.join(
            sha256_fingerprint[i:i+2] for i in range(0, len(sha256_fingerprint), 2)
        )
        sha1_formatted = ':'.join(
            sha1_fingerprint[i:i+2] for i in range(0, len(sha1_fingerprint), 2)
        )
        
        for expected_fp in self.ssl_fingerprint:
            normalized_expected = expected_fp.replace(':', '').replace(' ', '').upper()
            
            if (normalized_expected == sha256_fingerprint or 
                normalized_expected == sha1_fingerprint or
                expected_fp.upper() == sha256_formatted or
                expected_fp.upper() == sha1_formatted):
                return
        
        raise ssl.SSLError(
            f"Certificate fingerprint mismatch. Expected: {self.ssl_fingerprint}, "
            f"Got SHA256: {sha256_formatted}, SHA1: {sha1_formatted}"
        )


class GLPIHTTPSProtocol:
    """
    Equivalent to GLPI::Agent::HTTP::Protocol::https package.
    Provides import() functionality via configure_defaults().
    """
    
    # Class-level defaults (equivalent to set_ctx_defaults)
    _default_ca_cert_file = None
    _default_ca_cert_dir = None
    _default_ssl_cert_file = None
    _default_ssl_key_file = None
    _default_ssl_ca = None
    _default_ssl_fingerprint = None
    
    @classmethod
    def configure_defaults(cls,
                          ca_cert_file: Optional[str] = None,
                          ca_cert_dir: Optional[str] = None,
                          ssl_cert_file: Optional[str] = None,
                          ssl_key_file: Optional[str] = None,
                          ssl_ca: Optional[str] = None,
                          ssl_fingerprint: Optional[str] = None):
        """
        Equivalent to Perl's import() function with set_ctx_defaults.
        Sets default SSL context parameters.
        """
        if ca_cert_file:
            cls._default_ca_cert_file = ca_cert_file
        if ca_cert_dir:
            cls._default_ca_cert_dir = ca_cert_dir
        if ssl_cert_file:
            cls._default_ssl_cert_file = ssl_cert_file
        if ssl_key_file:
            cls._default_ssl_key_file = ssl_key_file
        if ssl_ca:
            cls._default_ssl_ca = ssl_ca
        if ssl_fingerprint:
            cls._default_ssl_fingerprint = ssl_fingerprint
    
    @classmethod
    def create_session(cls, ssl_check: bool = True, **kwargs) -> requests.Session:
        """
        Create session with HTTPS adapter.
        Equivalent to using the protocol handler in Perl.
        
        Args:
            ssl_check: Equivalent to {ua}->{ssl_check} in Perl
        """
        config = {
            'ssl_verify': ssl_check,
            'ca_cert_file': kwargs.get('ca_cert_file', cls._default_ca_cert_file),
            'ca_cert_dir': kwargs.get('ca_cert_dir', cls._default_ca_cert_dir),
            'ssl_cert_file': kwargs.get('ssl_cert_file', cls._default_ssl_cert_file),
            'ssl_key_file': kwargs.get('ssl_key_file', cls._default_ssl_key_file),
            'ssl_ca': kwargs.get('ssl_ca', cls._default_ssl_ca),
            'ssl_fingerprint': kwargs.get('ssl_fingerprint', cls._default_ssl_fingerprint),
            'verify_hostname': kwargs.get('verify_hostname', True)
        }
        
        session = requests.Session()
        adapter = GLPIHTTPSAdapter(**config)
        session.mount('https://', adapter)
        
        if config['ssl_verify']:
            if config['ca_cert_file']:
                session.verify = config['ca_cert_file']
            elif config['ca_cert_dir']:
                session.verify = config['ca_cert_dir']
            elif config['ssl_ca']:
                session.verify = config['ssl_ca']
            else:
                session.verify = True
        else:
            session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        if config['ssl_cert_file']:
            if config['ssl_key_file']:
                session.cert = (config['ssl_cert_file'], config['ssl_key_file'])
            else:
                session.cert = config['ssl_cert_file']
        
        return session


# Convenience function
def create_https_session(ssl_check: bool = True, **kwargs) -> requests.Session:
    """Convenience wrapper."""
    return GLPIHTTPSProtocol.create_session(ssl_check=ssl_check, **kwargs)


if __name__ == "__main__":
    # Example: Configure defaults (equivalent to Perl import with parameters)
    GLPIHTTPSProtocol.configure_defaults(
        ca_cert_file='/etc/ssl/certs/ca-bundle.crt'
    )
    
    # Create session with SSL verification
    session = GLPIHTTPSProtocol.create_session(ssl_check=True)
    print("HTTPS Protocol handler initialized")