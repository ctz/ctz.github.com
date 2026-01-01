+++
date = 2015-11-23
path = "2015/11/23/abusing-u2f-to-store-keys"
template = "page.html"
title = "Abusing U2F to 'store' keys"
extra = { toc = true }
tags = ["security", "authentication", "passwords"]
+++

[U2F][u2f] is another authentication technology which requires a trusted verifier,
like a remote server: fundamentally the output of an authentication is 'Yes' or 'No'
rather than some key material or new capability.

OTPs fall into this category too. Biometrics usually also do; biometric key generation
is a thing, but the entropy of the resulting key is tricky to quantify without large-scale
population studies.

This makes most authentication devices: **unusable offline**, and that means
they **don't work for mobile**, and certainly **won't work in early boot**
when you want to decrypt your disk.

# U2F
U2F comes from the [FIDO alliance][fido], an industry consortium of a bunch of authentication
hardware people (Vasco, NXP, RSA, Synaptics, Yubico, Oberthur), software people (Google, Microsoft),
and payment card issuers.

U2F has an enrollment phase, where a token generates a per-site ECDSA key (on the NIST P-256 curve)
and returns the associated public key, and an opaque 'key handle' which names the key.
The verifier stores the key handle and public key.

Then, for an authentication later, the verifier presents the key handle back to the token along
with a challenge, and the token signs the challenge.  The user is authenticated if the the 
signature is valid.

This is pretty simple.

# But I wanted key material!
I have a [Yubico Security key][yubico] which costs £12.99.  That's pretty good,
but even cheaper U2F tokens are available.

But I want to use this thing to decrypt my disk, or decrypt my password database!

So: we want some bytes with high entropy that are hard to guess without talking to a
specific U2F device.  We'll hash them before use, so it doesn't matter too much if the
bytes are not uniformly distributed or have some bias.

## Warning!
The following abuses the design of U2F.  It deliberately misuses cryptography.
It is presented for your amusement rather than serious use.

## Per-site keys
U2F's separation of keys between sites was done for privacy reasons, so database leaks
don't allow correlation of accounts to the same U2F device.

Storing all the per-site keys on a device is not a workable idea.  The device will never
be told if a key is abandoned by its verifier, so eventually it will run out of
persistent storage.

There are two ways of achieving this:

1. have some per-device secret, and generate private keys deterministically by
   hashing this secret together with a nonce.  The key handle is then merely
   this nonce.  This is, in fact, almost exactly what [yubico does][yubicou2f].
2. have some per-device key, use this to encrypt the private key material.  Key handles
   are then just ciphertexts.

**Note that if a U2F device produces key handles which contain the public key in plaintext, this whole scheme
fails catastrophically.** This isn't under our control, but it seems extremely unlikely.

## ECDSA public key recovery
A not well-known property of ECDSA: given a message and a valid signature over it,
you can derive the corresponding public keys.  There are two such public keys for each
signature, and one is the 'correct' one (ie. pairs up with the original signing key).

If the signature is invalid, you'll get junk or the maths won't work at all.

-----

# Protocol outline

Let's sketch a password + U2F key derivation method.  We'll use PBKDF2, any
slow hash is suitable as long as it processes arbitrary-length inputs.

## Enrollment

1. Obtain user password.
2. Perform U2F enrollment, obtaining public key and key handle.  Store key handle in plaintext.
3. Hash the public key and store the hash in plaintext.
3. Generate a random salt.  Store it in plaintext.
4. Compute `PBKDF2(salt, encode(public key) + password)`, use the result as a key.

Note: `encode()` is a fixed length encoding of an elliptic curve point, like P1363's `EC2OSP-XY`.

## Authentication

1. Obtain user password.
2. Choose a random nonce, and perform U2F authentication with the stored key handle.  A signature results.
3. Extract two candidate ECDSA public keys from the signature.
4. Hash both candidate public keys, and check against the stored hash.  If neither match,
   the U2F device is an imposter.
5. Produce the key again with `PBKDF2(salt, encode(public key) + password)`.

This has the following nice properties:

* **Freshness: it resists replay of token traffic**.  If the token doesn't sign our nonce, we don't recover the public key.
  Straightforward fingerprinting of the token does not achieve this.
* **Good entropy**. There are almost 2<sup>256</sup> possible public keys on NIST-P256, assuming the private key is chosen well.
* **Efficient**. Over and above the normal U2F user interaction time, the additional computations are minor.

-----

# Proof of concept

There's a proof of concept of this in my [u2f-key-storage][u2f-secret-storage] repo.
You'll need [Yubico's python-u2flib-host][python-u2flib-host] and its prerequisites.

```shell
$ sudo pip install python-u2flib-host
(...)
$ python u2fkey.py enroll
Touch the U2F device you wish to register...
written data to data.json
secret is b859c0416c979f6904e85ab60f93026a1af95f1afc29e07df0beca205ca8f68b
$ python u2fkey.py auth
Touch the flashing U2F device to authenticate...
secret is b859c0416c979f6904e85ab60f93026a1af95f1afc29e07df0beca205ca8f68b
```

-----

[u2f]: https://fidoalliance.org/specifications/overview/
[fido]: https://fidoalliance.org
[yubico]: https://www.yubico.com/applications/fido/
[yubicou2f]: https://developers.yubico.com/U2F/Protocol_details/Key_generation.html
[lastpass]: https://lastpass.com/yubico/
[u2f-secret-storage]: https://github.com/ctz/u2f-secret-storage
[python-u2flib-host]: https://github.com/Yubico/python-u2flib-host
