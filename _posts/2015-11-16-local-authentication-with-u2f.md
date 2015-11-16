---
layout: post
title: "Disk encryption through U2F abuse"
subtitle: ""
category: 
tags: [security, authentication, passwords]
published: false
---

* TOC
{:toc #toc-side}

[U2F][u2f] is another authentication technology which requires a trusted verifier,
like a remote server: fundementally the output of an authentication is 'Yes' or 'No'
rather than some key material or new capability.

OTPs fall into this category too. Biometrics usually also do; biometric key generation
is a thing, but the entropy of the resulting key is tricky to quantify without large-scale
population studies.

This makes most authentication devices: **unusable offline**, and that means
they **don't work for mobile** either[^1], and certainly **won't work in early boot**
when you want to decrypt your disk.

[^1]: Sorry, I don't have any signal.

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

We'll rely on the following facts to do this:

## Per-site keys
U2F's separation of keys between sites was done for privacy reasons, so database leaks
don't allow correlation of accounts to the same U2F device.

Storing all the per-site keys on a device is not a workable idea.  The device will never
be told if a key is abandoned by its verifier, so eventually it will run out of
persistent storage.

The only sensible way of achieving this: to have some per-device secret, and generate private
keys deterministically by hashing this secret with a nonce.  The key handle is then merely
this nonce.  This is, in fact, almost exactly what [yubico does][yubicou2f].

## ECDSA
A not well-known property of ECDSA: given a message and a valid signature over it,
you can derive the corresponding public keys.  There are two such public keys for each
signature, and one is the 'correct' one (ie. pairs up with the original signing key).

If the signature is invalid, you'll get junk or the maths won't work at all.

-----

# Protocol outline

Let's sketch a password + U2F key derivation method.  We'll use PBKDF2, any
slow hash is suitable.

## Enrollment

1. Obtain user password.
2. Perform U2F enrollment, obtaining public key and key handle.  Store key handle in plaintext.
3. Hash the public key and store the hash in plaintext.
3. Generate a random salt.  Store it in plaintext.
4. Compute `PBKDF2(salt = salt, password = encode(public key) + password)`, use the result as a key.

## Authentication

1. Obtain user password.
2. Choose a random nonce, and perform U2F authentication with the stored key handle.  A signature results.
3. Extract two candidate ECDSA public keys from the signature.
4. Hash both candidate public keys, and check against the stored hash.  If neither match,
   the U2F device is an imposter.
4. Produce the key again with `PBKDF2(salt = salt, password = encode(public key) + password)`.
   
## Notes

* `encode()` is a fixed length encoding of an elliptic curve point, like SEC1's `EC2OSP`.
  
-----

[u2f]: https://fidoalliance.org/specifications/overview/
[fido]: https://fidoalliance.org
[yubico]: https://www.yubico.com/applications/fido/
[yubicou2f]: https://developers.yubico.com/U2F/Protocol_details/Key_generation.html
[lastpass]: https://lastpass.com/yubico/
