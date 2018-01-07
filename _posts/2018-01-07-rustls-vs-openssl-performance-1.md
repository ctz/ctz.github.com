---
layout: post
title: "TLS bulk performance: rustls versus OpenSSL"
subtitle: ""
category: 
tags: [rust, rustls, programming, tls, openssl]
---

* TOC
{:toc #toc-side}

There are quite a few dimensions to how TLS performance can vary.

Handshake performance covers how quickly new TLS sessions can be
set up.  There are broadly two kinds of TLS handshake: *full* and
*resumed*.  Full handshake performance will be dominated by the
expense of public key crypto -- certificate validation, authentication
and key exchange.  Resumed handshakes require no or
few public key operations, so are much quicker.

Bulk performance covers how quickly application data can be
transferred over an already set-up session.  Performance here
will be dominated by symmetric crypto performance -- the name
of the game is for the TLS stack to *stay out of the way* and
minimise overhead in the main data path.  The data rates
concerned are typically many times a typical network link speed.

This post covers bulk performance.  Later posts will cover
resumption and full handshake performance.

# Reproducibility

We'll measure current master for rustls ([128fb80][rustls-master])
and OpenSSL ([d201dbc][openssl-master]).

OpenSSL was built from source with default options, using gcc 7.2.0.
rustls was built from source using rustc 1.22.1.

All measurements below were obtained on the same i5-6500 Skylake at
3.2GHz, on Debian linux.  CPU scaling was turned off.

The best speed from 5 runs is used.

## rustls

The code used is in kept [alongside rustls][rustlsbench].  Build and
run with:

```
$ cargo test --no-run --example bench --release
$ make -f admin/bench-measure.mk measure
```

## OpenSSL

All the code used is in [ctz/openssl-bench][oslbench].  It expects
to find a built OpenSSL tree in `../openssl/`.  Then just run `make measure`.

# Bulk performance

Bulk performance is obviously sensitive to underlying network
performance, TCP stack efficiency, overheads in the kernel/userland
interface, etc.  We'll design our tests to avoid these interfaces,
and instead measure an *upper bound* on performance which you might
attain if they all imposed no extra overhead.

That means no network or kernel differences are relevant in the
tests, which makes them more reproducible.  However, the normal
caveats about micro-benchmarks apply: we're not testing the whole
system, and real-world results are likely to be different.

We'll measure only TLS1.2 for the time being.  TLS1.3 is supported
by both rustls and OpenSSL, but the specification is still in flux.

## Codebase lineage

It's worth mentioning here that rustls and OpenSSL share most
of the underlying cryptography code.  rustls depends on [ring][ring]
for all its cryptography, which itself has its roots in Google's
OpenSSL fork, [BoringSSL][boringssl].

So we don't expect to see significant performance differences.

These tests, then, are more concerned with whether the TLS library
can keep the underlying crypto well-fed to reach its maximal potential.

## Sending speed

This covers how quickly a TLS library can convert application
data into TLS frames.  We send 1GB of data in chunks of 1MB, and
time how long that takes.  The timing does not include sending
the TLS frames on the receive-side.

<div align="center"><img src="/assets/diagrams/tls-session-send.png"
  alt="diagram showing the sending direction of a TLS session, with plaintext entering on the left and ciphertext leaving on the right" /></div>

Cipher suite | OpenSSL (MB/s) | Rustls (MB/s) | vs. (2sf)
------------ | --------------------- | -------------------- |
`ECDHE-RSA-AES128-GCM-SHA256` | 3365.56 | 3591.31 | +6.7%
`ECDHE-RSA-AES256-GCM-SHA384` | 2679.29 | 2825.56 | +5.5%
`ECDHE-RSA-CHACHA20-POLY1305` | 1620.79 | 1672.15 | +3.2%

The difference between OpenSSL and rustls appears to be thanks to an
extra copy in the main data-path in OpenSSL.

## Receiving speed

This covers how quickly a TLS library can process TLS frames into
the corresponding application data.  The TLS frames result from
encrypting 1GB of total application data in chunks of 1MB.

The timing includes covers the transport of TLS frames from memory
into the TLS library, because at this point the TLS library can
perform computation on the frames.

<div align="center"><img src="/assets/diagrams/tls-session-recv.png"
  alt="diagram showing the receive direction of a TLS session, with ciphertext entering on the right and plaintext leaving on the left" /></div>

Cipher suite | OpenSSL (MB/s) | Rustls (MB/s) | vs. (2sf)
------------ | --------------------- | -------------------- |
`ECDHE-RSA-AES128-GCM-SHA256` | 3738.02 | 3727.86 | -0.3%
`ECDHE-RSA-AES256-GCM-SHA384` | 2940.52 | 2932.72 | -0.3%
`ECDHE-RSA-CHACHA20-POLY1305` | 1705.77 | 1706.56 | +0.0%

There's nothing in it on this measurement.

# Conclusions

These are quite respectable speeds: both libraries can achieve 25Gbit/s
per core at full pelt, in either direction.

It's expected that the two AES-GCM suites are quicker than the chacha20-poly1305
suite -- they're hardware accelerated (using the AES-NI and [pclmulqdq][pclmulqdq]
instructions).  If we were to disable that acceleration, the speeds drop
to approx 230MB/s.  That gives a flavour of why chacha20-poly1305 is valuable
in modern TLS: performance where AES-GCM acceleration is not available.

The difference between AES128 and AES256 appears to be approximately 26%, rather
than the 40% one might expect (AES128 does 10 rounds, AES256 does 14 rounds).
There may be some limiting factor that prevents AES128 running at the expected
speed, or perhaps this CPU has extra area dedicated to making AES256 faster.

In the sending direction, OpenSSL has an extra copy of the plaintext application
data.  Rustls avoids a copy here, but the performance advantage is relatively
minor.

-----

[rustls]: https://github.com/ctz/rustls
[rustls-master]: https://github.com/ctz/rustls/tree/128fb80fb44c41ea40cf37082f761e499bcdf9c6
[openssl-master]: https://github.com/openssl/openssl/tree/d201dbc9a4d4ce7fd1f7ffc8f499cf261ba5e72a
[oslbench]: https://github.com/ctz/openssl-bench/tree/10344fb
[rustlsbench]: https://github.com/ctz/rustls/blob/128fb80fb44c41ea40cf37082f761e499bcdf9c6/examples/internal/bench.rs
[pclmulqdq]: https://www.intel.com/content/www/us/en/processors/carry-less-multiplication-instruction-in-gcm-mode-paper.html
[ring]: https://github.com/briansmith/ring
[boringssl]: https://github.com/google/boringssl
