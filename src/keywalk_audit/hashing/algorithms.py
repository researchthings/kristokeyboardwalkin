"""Hash-algorithm registry mapping names to hashcat -m modes.

Notes on edge cases (also documented in docs/HASH_MODES.md):
- Cisco IOS Type 5 uses the same kernel as ``md5crypt`` (mode 500). It is
  not registered separately to avoid duplicate (algorithm, mode) entries.
- Cisco IOS Type 7 is reversible obfuscation, not a one-way hash. It is
  not a hashcat mode and is handled by a dedicated decoder rather than
  this registry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HashAlgo:
    """Metadata for a hashcat-supported hash algorithm."""

    name: str
    hashcat_mode: int
    family: str
    is_fast: bool
    description: str


HASHCAT_MODES: dict[str, HashAlgo] = {
    "ntlm": HashAlgo("ntlm", 1000, "windows", True, "Windows NT hash"),
    "lm": HashAlgo("lm", 3000, "windows", True, "LAN Manager hash"),
    "netntlmv1": HashAlgo("netntlmv1", 5500, "windows", True, "NetNTLMv1 challenge response"),
    "netntlmv2": HashAlgo("netntlmv2", 5600, "windows", True, "NetNTLMv2 challenge response"),
    "mscache": HashAlgo("mscache", 1100, "windows", True, "Domain Cached Credentials (DCC1)"),
    "mscache2": HashAlgo("mscache2", 2100, "windows", False, "Domain Cached Credentials 2 (DCC2)"),
    "krb5_asrep_rc4": HashAlgo(
        "krb5_asrep_rc4", 18200, "windows", True, "Kerberos 5 AS-REP etype 23"
    ),
    "krb5_tgsrep_rc4": HashAlgo(
        "krb5_tgsrep_rc4", 13100, "windows", True, "Kerberos 5 TGS-REP etype 23"
    ),
    "krb5_asrep_aes128": HashAlgo(
        "krb5_asrep_aes128", 19800, "windows", False, "Kerberos 5 AS-REP etype 17"
    ),
    "krb5_asrep_aes256": HashAlgo(
        "krb5_asrep_aes256", 19900, "windows", False, "Kerberos 5 AS-REP etype 18"
    ),
    "krb5_tgsrep_aes128": HashAlgo(
        "krb5_tgsrep_aes128", 19600, "windows", False, "Kerberos 5 TGS-REP etype 17"
    ),
    "krb5_tgsrep_aes256": HashAlgo(
        "krb5_tgsrep_aes256", 19700, "windows", False, "Kerberos 5 TGS-REP etype 18"
    ),
    "descrypt": HashAlgo("descrypt", 1500, "unix", True, "Traditional DES crypt"),
    "md5crypt": HashAlgo("md5crypt", 500, "unix", False, "FreeBSD MD5 crypt ($1$)"),
    "sha256crypt": HashAlgo("sha256crypt", 7400, "unix", False, "SHA-256 crypt ($5$)"),
    "sha512crypt": HashAlgo("sha512crypt", 1800, "unix", False, "SHA-512 crypt ($6$)"),
    "bcrypt": HashAlgo("bcrypt", 3200, "unix", False, "bcrypt ($2a$/$2b$/$2y$)"),
    "scrypt": HashAlgo("scrypt", 8900, "unix", False, "scrypt"),
    "macos_pbkdf2": HashAlgo("macos_pbkdf2", 7100, "macos", False, "macOS PBKDF2-HMAC-SHA512"),
    "macos_sha1": HashAlgo("macos_sha1", 122, "macos", True, "macOS 10.4 to 10.6 salted SHA-1"),
    "cisco_type4": HashAlgo("cisco_type4", 5700, "network", True, "Cisco-IOS type 4 (SHA-256)"),
    "cisco_type8": HashAlgo(
        "cisco_type8", 9200, "network", False, "Cisco-IOS type 8 (PBKDF2-SHA256)"
    ),
    "cisco_type9": HashAlgo("cisco_type9", 9300, "network", False, "Cisco-IOS type 9 (scrypt)"),
    "raw_md4": HashAlgo("raw_md4", 900, "generic", True, "Raw MD4"),
    "raw_md5": HashAlgo("raw_md5", 0, "generic", True, "Raw MD5"),
    "raw_sha1": HashAlgo("raw_sha1", 100, "generic", True, "Raw SHA-1"),
    "raw_sha224": HashAlgo("raw_sha224", 1300, "generic", True, "Raw SHA-224"),
    "raw_sha256": HashAlgo("raw_sha256", 1400, "generic", True, "Raw SHA-256"),
    "raw_sha384": HashAlgo("raw_sha384", 10800, "generic", True, "Raw SHA-384"),
    "raw_sha512": HashAlgo("raw_sha512", 1700, "generic", True, "Raw SHA-512"),
    "raw_sha3_256": HashAlgo("raw_sha3_256", 17400, "generic", True, "Raw SHA3-256"),
    "raw_sha3_512": HashAlgo("raw_sha3_512", 17600, "generic", True, "Raw SHA3-512"),
    "raw_blake2b": HashAlgo("raw_blake2b", 600, "generic", True, "Raw BLAKE2b-512"),
}


def get_algo(name: str) -> HashAlgo:
    """Return the registered HashAlgo for `name` or raise KeyError."""
    try:
        return HASHCAT_MODES[name]
    except KeyError as exc:
        known = ", ".join(sorted(HASHCAT_MODES))
        raise KeyError(f"unknown hash algorithm {name!r}. Known: {known}") from exc
