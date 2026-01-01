+++
date = 2015-08-11
path = "2015/08/11/pbkdf2-performance-matters"
template = "page.html"
title = "PBKDF2: performance matters"
extra = { toc = true }
tags = ["security", "openssl", "passwords", "performance"]
+++

This is a summary of a talk I gave at Passwords15 on 2015-08-05 in Las Vegas.
There are [slides][slides] and a video:

<iframe width="620" height="420" src="https://www.youtube.com/embed/k_szwKBuNBw" frameborder="0" allowfullscreen></iframe>

---

# Overview

The PBKDF2 standards describe the algorithm in such an unhelpful way that almost every defender implementation is at least two times slower than it otherwise could be.

For slow password hashes, performance is important because any inefficiency is passed on to some combination of your user and attacker.

Of the implementations I reviewed, only the following are algorithmically optimal:

* SJCL (forever)
* OpenSSL (post 2013)
* Python core (3.4 and later)
* Django (post 2013)
* BouncyCastle (1.49 and later)
* Apple CoreCrypto (unknown history)

But, in practical terms, all are slower than a public domain implementation I released: 

# fastpbkdf2

[fastpbkdf2][fastpbkdf2] is a public domain PBKDF2-HMAC-{SHA1,SHA256,SHA512} which significantly outperforms
others available.  For example, it outperforms OpenSSL by about 4x and golang by about 6x.

It does this through a few tricks:

## Strategies

* **Aggressive inlining of everything in the inner loop**.  This makes everything statically available to the compiler so optimisation passes can have full effect.  This means the inner loop will get compiled to packed vector SSE2 operations, plus a call to the hash compression function.
  
* **Compute output in host endianess**.  This is a minor tweak, but should pay off much more when no endianness conversion is performed (see below).
  
* **No buffering or padding inside loop**.  The input to the hash function in the inner loop is always the same length, so MD length padding is done once, outside the loop.
  
* **Minimal copies and other operations inside loop**.  OpenSSL does memory allocations/frees and excessive copies.
  
* **Optional parallelisation of long outputs**.  PBKDF2's generation of long outputs is exceedingly broken, but in case you need it anyway, `fastpbkdf2` can use OpenMP to parallelise this computation.

  This graph compares making one to four blocks of output using OpenSSL versus fastpbkdf2.  Note that when multithreading is enabled, the second block is 'free' (with respect to wall time) and subsequent blocks are slightly faster (thanks to hyperthreading).
  
  ![calculating 1-4 blocks of output openssl/single thread fastpbkdf2/multi thread fastpbkdf2][multigraph]

## Future work

* **Avoid endianness conversions**.  The input to the compression function is in network order, but needs to be processed in host order.  This means order conversions before, during and after the compression function call.  However, if we keep everything in host order, we can get rid of these.
  
  I didn't do this yet, because it requires maintaining fast hash function implementations for interesting platforms.  At the moment `fastpbkdf2` is generally portable.

# Reviewed implementations
This review was performed in December 2014.  Things might have moved on since then.

1. [FreeBSD (10)][freebsd]:  Slow.  Measures speed.
2. [GRUB (2.0)][grub]: Slow.
3. [Truecrypt (7.1a)][truecrypt]: Slow.
4. Android (disk encryption): OK. Calls scrypt + openssl pbkdf2.
5. [Android (BouncyCastle)][androidbc]: Slow.
6. Django: OK. Fixed by sc00bz CVE-2013-1443.
7. OpenSSL: OK. Fixed by Christian Heimes 2013-11-03.
8. Python (core >=3.4): OK. Christian Heimes 2013-10-12.
9. [Python (pypi pbkdf2)][pypipbkdf2]:  Slow.
10. [Ruby (pbkdf2 gem)][rubygem]: Slow.
11. [Go (go.crypto)][gocrypto]: Slow (structurally fast, but hmac module lets it down).
12. [OpenBSD][openbsd]: Slow.
13. [PolarSSL/mbedTLS][polarssl]: Slow.
14. [CyaSSL/wolfSSL][cyassl]: Slow (structurally fast, but hmac module lets it down).
15. [SJCL][sjcl]: OK.
16. [Java][openjdk]: Slow (structurally fast, but hmac module lets it down).
17. [Common Lisp (ironclad)][lispironclad]: Slow.
18. [Perl (Crypt::PBKDF2)][perlcpan]: Slow.
19. [PHP (core)][phpcore]: Slow. [Pull request][phppatch] submitted upstream.
20. [C# (core)][mscorlib]: Slow.
21. [scrypt (scrypt and libscrypt)][scrypt] Slow but iterations==1, always. yescrypt also.
22. [BouncyCastle][bouncycastle] OK (>= 1.49).
23. Apple CoreCrypto. OK. Disassembly only (source is not available).

[slides]: https://github.com/ctz/talks/blob/master/pbkdf2/pbkdf2.pdf
[fastpbkdf2]: https://github.com/ctz/fastpbkdf2
[multigraph]: /assets/fastpbkdf2-graph.png

[freebsd]: http://sources.freebsd.org/RELENG_10/src/sys/geom/eli/pkcs5v2.c
[grub]: https://github.com/mokafive/grub/blob/upstream/grub-core/lib/pbkdf2.c#L89
[truecrypt]: https://github.com/FauxFaux/truecrypt/blob/targz/Common/Pkcs5.c#L131
[androidbc]: https://android.googlesource.com/platform/external/bouncycastle/+/2768c2948c0b1931bff087e43a8db8059c183b56/bcprov/src/main/java/org/bouncycastle/crypto/generators/PKCS5S2ParametersGenerator.java
[pypipbkdf2]: https://github.com/dlitz/python-pbkdf2/blob/master/pbkdf2.py#L173
[rubygem]: https://rubygems.org/gems/pbkdf2
[gocrypto]: https://code.google.com/p/go/source/browse/pbkdf2/pbkdf2.go?repo=crypto
[openbsd]: http://cvsweb.openbsd.org/cgi-bin/cvsweb/~checkout~/src/lib/libutil/pkcs5_pbkdf2.c?rev=1.6&content-type=text/plain
[polarssl]: https://github.com/polarssl/polarssl/blob/1b4eda3af96a7fb53a327fb3325670a14ff02213/library/pkcs5.c
[cyassl]: https://github.com/cyassl/cyassl/blob/fc24dca12dd724aea8448fc65ade35527ea3c26c/ctaocrypt/src/pwdbased.c
[sjcl]: https://github.com/bitwiseshiftleft/sjcl/blob/136512284d923390c115a735746b965c12f39fd0/core/pbkdf2.js
[openjdk]: http://hg.openjdk.java.net/jdk7/jdk7/jdk/file/9b8c96f96a0f/src/share/classes/com/sun/crypto/provider/HmacCore.java
[lispironclad]: https://github.com/froydnj/ironclad/blob/e0c1067fd5d00552fb4050f8654a610f619b4075/src/pkcs5.lisp#L51
[perlcpan]: https://metacpan.org/source/ARODLAND/Crypt-PBKDF2-0.142390/lib/Crypt/PBKDF2.pm
[phpcore]: https://github.com/php/php-src/blob/d0cb715373c3fbe9dc095378ec5ed8c71f799f67/ext/hash/hash.c#L214
[phppatch]: https://github.com/php/php-src/pull/1387
[mscorlib]: http://referencesource.microsoft.com/#mscorlib/system/security/cryptography/rfc2898derivebytes.cs,170
[scrypt]: https://github.com/technion/libscrypt/blob/master/sha256.c#L393
[bouncycastle]: https://github.com/bcgit/bc-java/blob/master/core/src/main/java/org/bouncycastle/crypto/generators/PKCS5S2ParametersGenerator.java
