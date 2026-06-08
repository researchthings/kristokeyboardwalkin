# Hash modes

`keywalk_audit.hashing.algorithms.HASHCAT_MODES` registers 33
hashcat-supported algorithms. Each entry is a `HashAlgo` record with
the algorithm name, hashcat ``-m`` mode, family, fast / slow flag, and
a short description.

## Registry

| name | hashcat mode | family | fast | description |
|------|--------------|--------|------|-------------|
| ntlm | 1000 | windows | yes | Windows NT hash |
| lm | 3000 | windows | yes | LAN Manager hash |
| netntlmv1 | 5500 | windows | yes | NetNTLMv1 challenge response |
| netntlmv2 | 5600 | windows | yes | NetNTLMv2 challenge response |
| mscache | 1100 | windows | yes | Domain Cached Credentials (DCC1) |
| mscache2 | 2100 | windows | no | Domain Cached Credentials 2 (DCC2) |
| krb5_asrep_rc4 | 18200 | windows | yes | Kerberos 5 AS-REP etype 23 |
| krb5_tgsrep_rc4 | 13100 | windows | yes | Kerberos 5 TGS-REP etype 23 |
| krb5_asrep_aes128 | 19800 | windows | no | Kerberos 5 AS-REP etype 17 |
| krb5_asrep_aes256 | 19900 | windows | no | Kerberos 5 AS-REP etype 18 |
| krb5_tgsrep_aes128 | 19600 | windows | no | Kerberos 5 TGS-REP etype 17 |
| krb5_tgsrep_aes256 | 19700 | windows | no | Kerberos 5 TGS-REP etype 18 |
| descrypt | 1500 | unix | yes | Traditional DES crypt |
| md5crypt | 500 | unix | no | FreeBSD MD5 crypt ($1$) |
| sha256crypt | 7400 | unix | no | SHA-256 crypt ($5$) |
| sha512crypt | 1800 | unix | no | SHA-512 crypt ($6$) |
| bcrypt | 3200 | unix | no | bcrypt ($2a$/$2b$/$2y$) |
| scrypt | 8900 | unix | no | scrypt |
| macos_pbkdf2 | 7100 | macos | no | macOS PBKDF2-HMAC-SHA512 |
| macos_sha1 | 122 | macos | yes | macOS 10.4 to 10.6 salted SHA-1 |
| cisco_type4 | 5700 | network | yes | Cisco-IOS type 4 (SHA-256) |
| cisco_type8 | 9200 | network | no | Cisco-IOS type 8 (PBKDF2-SHA256) |
| cisco_type9 | 9300 | network | no | Cisco-IOS type 9 (scrypt) |
| raw_md4 | 900 | generic | yes | Raw MD4 |
| raw_md5 | 0 | generic | yes | Raw MD5 |
| raw_sha1 | 100 | generic | yes | Raw SHA-1 |
| raw_sha224 | 1300 | generic | yes | Raw SHA-224 |
| raw_sha256 | 1400 | generic | yes | Raw SHA-256 |
| raw_sha384 | 10800 | generic | yes | Raw SHA-384 |
| raw_sha512 | 1700 | generic | yes | Raw SHA-512 |
| raw_sha3_256 | 17400 | generic | yes | Raw SHA3-256 |
| raw_sha3_512 | 17600 | generic | yes | Raw SHA3-512 |
| raw_blake2b | 600 | generic | yes | Raw BLAKE2b-512 |

The five generic raw modes below the original SHA-2 entries
(SHA-224/384, SHA3-256/512, BLAKE2b) were added in v0.2 and all build in
pure Python.

## Edge cases

### Cisco IOS type 5

Cisco type 5 hashes use the same kernel as `md5crypt` (mode 500). The
registry intentionally omits a separate `cisco_type5` entry; callers
that need to handle Cisco type 5 hashes pass `md5crypt` to hashcat.

### Cisco IOS type 7

Cisco type 7 is reversible obfuscation, not a one-way hash. There is no
hashcat mode for it because cracking is unnecessary: the password is
recovered by direct decoding. This registry deliberately excludes
`cisco_type7`; the decoder lives in
`keywalk_audit.hashing.cisco_type7`. It is a Vigenère-style XOR against
the fixed 53-byte Cisco key, with a leading two-digit seed index:

```
keywalk-audit decode-cisco7 02050D480809   # -> cisco
keywalk-audit encode-cisco7 secret --seed 7
```

`decode(encode(p, s)) == p` for any ASCII `p` and any seed `0 <= s <
len(KEY)`; malformed ciphertext raises `CiscoType7Error`.

## Build-time vs audit-time

`keywalk_audit.hashing.computer.compute_hash` provides pure-Python
implementations for the fast, hashcat-aligned algorithms (NTLM, LM, and
the generic raw modes: MD4, MD5, SHA-1, SHA-224/256/384/512,
SHA3-256/512, BLAKE2b). The rainbow builder uses these to populate the
`hashes` table at build time so that audit-time exact lookups are
immediate.

MD4 is implemented from scratch in `keywalk_audit.hashing.md4` because
OpenSSL 3 drops MD4 from `hashlib`. NTLM is MD4 over the UTF-16LE
encoding of the password; raw MD4 hashes the UTF-8 bytes. The empty NT
hash `31d6cfe0d16ae931b73c59d7e0c089c0` equals MD4 of the empty input,
which cross-validates the implementation.

Slow algorithms (bcrypt, scrypt, sha256crypt, sha512crypt, the Kerberos
AES variants, PBKDF2 and crypt-family algorithms) are not materialized
in the rainbow table. Audits against captured hashes in those
algorithms invoke hashcat at audit time with the candidate plaintexts
as the wordlist.

## hashcat version

The runner enforces hashcat 6.2.0 or newer because earlier releases do
not support all modes registered above. ``hashcat --version`` is
parsed for the `vMAJOR.MINOR.PATCH` triple; older binaries raise
`HashcatVersionError` before the actual run.
