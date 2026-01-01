+++
date = 2016-01-17
path = "2016/01/17/using-sgx-to-hash-passwords"
template = "page.html"
title = "Using SGX to harden password hashing"
extra = { toc = true }
tags = ["security", "authentication", "passwords"]
+++

[SGX][sgx] is a way of running security-sensitive user-mode code in an '**enclave**'.
Code running in an enclave has its memory encrypted and authenticated, and cannot be
observed by code running anywhere else.  It's able to use device-specific
keys to encrypt ('**seal**') data to future executions of itself or enclaves signed by the
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
be able to check a user password.  That's not a sensible approach; backups would be
worthless.

So we'll have a logical grouping of enclaves, all of which can check passwords --
a '**region**'.  A region is implemented as an AES key available to all such enclaves.
'Enrolling' an enclave into a region involves the enclave learning the region key,
and sealing the key material to itself for later use.

<div align="center"><img src="/assets/sgx-region.png" alt="diagram showing simple region concept"></div>

When we're not enrolling an enclave into our region, the region key can be kept offline,
in a hardware security module, or written down in a safe.

# Operations

We need only two operations: setting a password and checking a guess.  These look like:

<div align="center"><img src="/assets/sgx-pwsetup.png" alt="diagram showing password setup flow"></div>

Here, we generate a random salt (using laundered hardware entropy from the `RDRAND`
instruction) and pass the password into PBKDF2.  The result and salt are encrypted using
the region key, producing a ciphertext which can be stored alongside the user record
in a database or password file.

<div align="center"><img src="/assets/sgx-pwauth.png" alt="diagram showing password guess flow"></div>

Here we decrypt the ciphertext to obtain the salt and correct hash.  We hash the
purported password and compare with the correct hash.

# The code

The code is [here][code].  The main enclave code is 
in [pwenclave/pwenclave.c][pwenclavec].  The interface to it is
in [pwenclave/pwenclave.edl][pwenclaveedl], in Intel's "Enclave Description Language",
which tells the tooling which function calls you want remoted into (an 'ecall')
and out of (an 'ocall') the enclave.

There's a test program in [smoketest/smoketest.c][smoketestc] which should product
output like this:

<pre>
pw_region_enroll took 0ms
pw_setup took 78ms
setup worked, blob is 84 bytes
43fb1bbfda8e71b2fed8c714f7d5b16730c184
25595b34c4fc93280471967a7377ce251ff41f
a43068246eff231a3a86af6c50ef64e4b26d18
31d9e885c1ad577672c8c1f7beae8ee854e829
3f18d5b74e29f350
pw_check+ took 78ms
pw_check worked (positive case)
pw_check- took 78ms
pw_check worked (negative case)
</pre>

-----

[sgx]: https://software.intel.com/en-us/sgx-sdk
[code]: https://github.com/ctz/sgx-pwenclave
[pwenclavec]: https://github.com/ctz/sgx-pwenclave/blob/master/pwenclave/pwenclave.c
[pwenclaveedl]: https://github.com/ctz/sgx-pwenclave/blob/master/pwenclave/pwenclave.edl
[smoketestc]: https://github.com/ctz/sgx-pwenclave/blob/master/smoketest/smoketest.c
