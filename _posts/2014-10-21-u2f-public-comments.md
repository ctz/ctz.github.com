---
layout: post
title: "Public comments on FIDO U2F standard"
subtitle: ""
category: 
tags: [security, mobile, google, authentication]
---

This is a public comment made on the subject of the [FIDO][fido] U2F public standards.  Submitted 2014-10-21.

*****

U2F specifies use of ECDSA by referencing ANSI X9.62.  This version of ECDSA (also described in SEC1, FIPS186-3, P1363, etc.) catastrophically fails in a number of cases surrounding the guessing entropy and reuse of the per-signature nonce. This makes its use in a new protocol extremely inadvisable.

Fortunately we have a drop-in, fully compatible replacement standardised in [RFC6979][]: deterministic ECDSA.

My suggestions in full are:

1. In the 'Implementation Considerations' document, section 2.3 really must mention this. It is **significantly more important** over the lifetime of a key to use high entropy ECDSA k values, than in the key material itself!

2. Strongly suggest in the same document that deterministic ECDSA is used.

3. In the 'Security Reference' document, threat T-1.4.10 should mention deterministic ECDSA as a complete mitigation. (Aside: the current suggestion of 'use a good quality RNG' is not really a mitigation for the problem of 'the RNG is poor quality and my key fell out').

4. Strongly consider requiring authenticators use RFC6979 ECDSA.

[RFC6979]: http://tools.ietf.org/html/rfc6979
