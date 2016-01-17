---
layout: post
title: "Using SGX to harden password hashing"
subtitle: ""
category: 
tags: [security, authentication, passwords]
published: true
---

* TOC
{:toc #toc-side}

[SGX][sgx] is a way of running security-sensitive user-mode code in an 'enclave'.
Code running in an enclave has its memory encrypted and authenticated, and cannot be
observed by code running anywhere else.  It's able to use device-specific
keys to encrypt ('seal') data to future executions of itself or enclaves signed by the
same key.

We can use SGX to harden password hashing, by imposing the restriction that it is only
possible on our hardware.  That means offline attack is no longer possible, and a database
leak only contains undecryptable ciphertext.

# Warning

This is a demo, and the result of me playing with SGX for a day.  You shouldn't deploy
this without understanding everything yourself first.

# Design

It would be easy to hash a password in an enclave and then seal it to itself for
verification later.  Unfortunately, that means only that physical CPU will ever
be able to check a user password.  That's not a sensible approach; backups will be
worthless.

Instead, we use a logical grouping of enclaves all of whom can check passwords --
a 'region'.  A region is nothing more than an AES key available to all such enclaves.
'Enrolling' an enclave into a region involves telling it the region key and having it
seal the region key to itself.

![diagram showing simple region concept][regionpng]

At the enclave level, we need only two operations: setting a password and checking
a guess.  These look like:

![diagram showing password setup flow][setuppng]

Here, we generate a random salt (using laundered hardware entropy from the `RDRAND`
instruction) and pass the password into PBKDF2.  The result and salt are encrypted using
the region key, producing a ciphertext which can be stored alongside the user record
in a database or password file.

![diagram showing password guess flow][authpng]

Here we decrypt the ciphertext to obtain the salt and correct hash.  We hash the
purported password and compare with the correct hash.

[regionpng]: /assets/sgx-region.png
[setuppng]: /assets/sgx-pwsetup.png
[authpng]: /assets/sgx-pwauth.png

-----

[sgx]: https://software.intel.com/en-us/sgx-sdk
