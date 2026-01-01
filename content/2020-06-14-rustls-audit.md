+++
date = 2020-06-14
path = "2020/06/14/rustls-audit"
template = "page.html"
title = "Third-party audit of rustls"
subtitle = ""
tags = ["rust", "rustls", "audit"]
+++

In May and June 2020, Cure53 completed an audit of *[ring][]*, [webpki][], and [rustls][].
[Their report][report] ([PDF][reportpdf]) fully describes the audit, and makes for interesting reading.

First off, though, Dirkjan Ochtman (of the [Quinn][quinn] project) deserves a great deal of thanks
for ultimately making this happen.  We first discussed the possibility of an audit like this at
RustFest Paris 2018. He worked with great determination for almost two years to secure a sponsor.
Thanks Dirkjan!

The [Cloud Native Computing Foundation][cncf] (a part of the Linux Foundation) funded
this audit, at the request of [Buoyant][buoyant] who use rustls in the data plane of [linkerd][].
So further thanks are due to Chris Aniszczyk of the Linux Foundation, and Oliver Gould of Buoyant
for their support of these projects.

Finally, thanks to the staff at Cure53 for being a pleasure to work with.

## Highlights

Some choice quotes:

> "[..] the team of auditors considered the **general code quality really good** and can attest
> to a solid impression left consistently by all scope items"

> "Both from a design point of view as from an implementation
> perspective the entire scope can be **considered of exceptionally high standard**."

> "The developer’s intent to provide a high-quality TLS implementation is
> very clear and **this goal can be considered as achieved successfully**."

> "Minor recommendations here and there are always possible for any project, but this does
> not change the fact that there is really not much to improve at rustls. Cure53 had the
> rare pleasure of being **incredibly impressed with the presented software**."

## Findings
There were two informational and two minor-severity findings.  See [the report][report] for the full details.
The discussion below reflects my opinion on these issues.

### TLS-01-001 - Formally Verified Cryptography Recommendations (info)
This finding suggests *ring* uses formally verified cryptography implementations from the EverCrypt project.
It's hard to argue against formal verification of foundational cryptography code.
It's worth noting here that *ring* does already use a formally verified curve25519 implementation
(from the [fiat-crypto][] project).

### TLS-01-002 - Unchecked usage of unwrap (info)
This finding relates to instances of `unwrap()` that were free of panics, but where it was too hard
to reason that this was the case.  The reasoning spanned several different modules, which itself is
a readability and maintenance hazard.  The code in question has been improved as a result.

### TLS-01-003 - Support for Non-Contiguous Subnet Masks (low)
This finding relates to certificate name constraints expressed as a space of IP addresses as
specified in [RFC5280][].  The RFC doesn't specify any constraints on network masks, but it
does seem sensible to disallow sparse masks.

### TLS-01-004 - Data Truncation in DER Encoding Implementation (low)
This finding rightly points out a function in rustls that produces incorrect output when applied
to an X.501 Name that is larger than 64KB.  While that's an exceedingly unlikely case, and the
bug does not cause unsafe operation (but perhaps connection failure), the function has been
corrected to produce valid output for all inputs.

## Conclusion
As with other forms of software testing, ultimately a third-party audit can only show the
presence of defects but not their absence.  With that said, the positive feedback in the
report and the low severity of these findings are certainly encouraging.

[rustls]: https://github.com/ctz/rustls
[ring]: https://github.com/briansmith/ring
[webpki]: https://github.com/briansmith/webpki
[quinn]: https://github.com/djc/quinn
[reportpdf]: https://github.com/ctz/rustls/raw/master/audit/TLS-01-report.pdf
[report]: https://github.com/ctz/rustls/blob/master/audit/TLS-01-report.pdf
[cncf]: https://www.cncf.io/
[buoyant]: https://buoyant.io/
[linkerd]: https://linkerd.io/
[fiat-crypto]: https://github.com/mit-plv/fiat-crypto
[rfc5280]: https://tools.ietf.org/html/rfc5280
