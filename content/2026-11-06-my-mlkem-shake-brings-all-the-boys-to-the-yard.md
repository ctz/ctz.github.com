+++
date = 2026-11-06
path = "2026/11/06/my-mlkem-shake-brings-all-the-boys-to-the-yard"
template = "page.html"
title = "My ML-KEM SHAKE Brings All the Boys to the Yard"
tags = ["cryptography", "performance"]
+++

## Warm it up
The performance of ML-KEM-768 [has become increasingly important](https://radar.cloudflare.com/post-quantum)
for overall TLS handshake performance.
This post is about recent performance improvements in [Graviola](https://github.com/ctz/graviola).

## The way I wind
All the measurements below are "combined" benchmarks, comprising all the ML-KEM computations
needed for one TLS handshake:  in [FIPS 203](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.203.pdf)
parlance, this is one `KeyGen` and one `Decaps` performed by the TLS client, and one `Encaps` performed by the server.

This makes a convenient all-in number which covers the entirety of the interface
standardised by FIPS 203.  But note that most benchmarks of ECDH algorithms are for one peer's work, not both
together as here, so caution is needed comparing ML-KEM performance with ECDH.

All the benchmarking here was done on [two of my computers](https://jbp.io/graviola/#reports).

## What the guys go crazy for
As you probably guessed from the title of this post, the techniques here all
revolve around SHAKE and SHA-3 generally, which make up a large proportion of the cost
of ML-KEM.  The general principles are not really novel and are well-known by ML-KEM implementors:
make individual components fast, and use SIMD to process a bunch of Keccak permutations in
parallel, and share Keccak permutation slots between otherwise-unrelated operations.

I can teach you, [but I have to charge](https://github.com/sponsors/ctz):

- **AVX-512 to do eight Keccak permutations in parallel.**  This takes about 1830 cycles, or 229 cycles
  per permutation.  That compares to 840 cycles for a single permutation using scalar instructions.

- **AVX-512 `SampleNTT()` rejection sampling.**  This attempts to keep data entirely in registers, meaning
  rejected samples are never written to memory.

- **AVX-512VL with 128-bit registers to improve the speed of a single Keccak permutation.**
  The latency of a single Keccak permutation remains a bottleneck because of data dependencies, sadly.
  This technique was [documented here by Intel](https://builders.intel.com/docs/networkbuilders/post-quantum-cryptography-accelerating-open-quantum-safe-library-with-intel-avx-512-keccak-1600-implementation-1762253806.pdf).
  This does one permutation in about 750 cycles.  This leaves half the register unused, so:

- **AVX-512VL with 128-bit registers to do two Keccak permutations in parallel.**
  This is used to make other progress alongside longer computations: `H(ek)` in parallel with parts of `SampleNTT`,
  and `G(m'||h)` in parallel with `J(z||c)`.

- **Continuing `J(z||c)` in parallel with the 7 SHAKE256 calls in `SamplePolyCBD()`.**
  With an eight-wide Keccak there's a spare lane, which shortens the critical path by the cost of one Keccak permutation.

The current Keccak permutation scheduling used by Graviola on x86_64 with AVX-512 is shown in this diagram:

[![keccak-f schedule](/assets/keccak-schedule.svg)](/assets/keccak-schedule.svg)

## Damn right it's better than yours
Combined ML-KEM-768 operations per second (higher is better), with Graviola's speedup in brackets:

| | x86_64 | aarch64 |
|---|--:|--:|
| **Graviola** | **59,081** | **49,328** |
| aws-lc-rs | 31,845 (1.86×) | 35,843 (1.38×) |
| libcrux-ml-kem | 21,711 (2.72×) | 21,886 (2.25×) |
| RustCrypto | 12,676 (4.66×) | 15,609 (3.16×) |
| Go | 7,614 (7.76×) | 9,501 (5.19×) |

The x86_64 machine has an AMD Ryzen 9 7940HS, and the aarch64 machine is an Apple M2.
Full details are in the [benchmark reports](https://jbp.io/graviola/#reports).

## Techniques that freaks these boys
I think this is getting close to an optimal schedule for Keccak permutations in ML-KEM-768.

Most likely, an optimal ML-KEM-768 implementation's internal structure needs to be completely
specialised on how many Keccak permutations can be performed at once, as has been done here
to account for an 8-wide Keccak. So the overall structure of the code would ideally be
specific to the architecture and CPU capabilities. Different ML-KEM parameter
sets would also dramatically change the layout.

Sounds like a job for a bunch of metaprogramming or code generation.  This, obviously, is what
the guys go crazy for.
