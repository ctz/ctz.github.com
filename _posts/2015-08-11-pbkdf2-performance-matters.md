---
layout: post
title: "PBKDF2: performance matters"
subtitle: ""
category: 
tags: [security, openssl, passwords, performance]
---

* TOC
{:toc #toc-side}

This is a summary of a talk I gave at Passwords15 on 2015-08-05 in Las Vegas.
There are [slides][slides] and a video:

<iframe width="620" height="420" src="https://www.youtube.com/embed/k_szwKBuNBw" frameborder="0" allowfullscreen></iframe>

---

# Quick summary

The PBKDF2 standards describe the algorithm in such an unhelpful way that almost every defender implementation is at least two times slower than it otherwise could be.

For slow password hashes, performance is important because any inefficiency is either passed on to some combination of your  user and attacker.

# fastpbkdf2

[fastpbkdf2][fastpbkdf2] is a public domain PBKDF2-HMAC-{SHA1,SHA256,SHA512} which significantly outperforms
others available.  For example, it outperforms OpenSSL by about 4x and golang by about 6x.

It does this through a few tricks:

## Strategies

* **Aggressive inlining of everything in the inner loop**.  This makes everything statically available to the compiler so optimisation passes can have full effect.  This means the inner loop will get compiled to packed vector SSE2 operations, plus a call to the hash compression function.
  
* **Compute output in host endianess**.  This is a minor tweak, but should pay off much more when no endianness conversion is removed (see below).
  
* **No buffering or padding inside loop**.  The input to the hash function in the inner loop is always the same length, so MD length padding is done once, outside the loop.
  
* **Minimal copies and other operations inside loop**.  OpenSSL does memory allocations/frees and excessive copies.
  
* **Optional parallelisation of long outputs**.  PBKDF2's generation of long outputs is exceedingly broken, but in case you need it anyway, `fastpbkdf2` can use OpenMP to parallelise this computation.

  This graph compares making one to four blocks of output using OpenSSL versus fastpbkdf2.  Note that when multithreading is enabled, the second block is 'free' (with respect to wall time) and subsequent blocks are slightly faster (thanks to hyperthreading).
  
  ![calculating 1-4 blocks of output openssl/single thread fastpbkdf2/multi thread fastpbkdf2][multigraph]

## Future work

* **Avoid endianness conversions**.  The input to the compression function is in network order, but needs to be processed in host order.  This means order conversions before, during and after the compression function call.  However, if we keep everything in host order, we can get rid of these.
  
  I didn't do this yet, because it requires maintaining fast hash function implementations for interesting platforms.  At the moment `fastpbkdf2` is generally portable.

[slides]: https://github.com/ctz/talks/blob/master/pbkdf2/pbkdf2.pdf
[fastpbkdf2]: https://github.com/ctz/fastpbkdf2
[multigraph]: /assets/fastpbkdf2-graph.png