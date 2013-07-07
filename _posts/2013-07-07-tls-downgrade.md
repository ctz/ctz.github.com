---
layout: post
title: "TLS downgrade behaviour"
subtitle: "or: why you shouldn't put all your eggs into the TLS forward secrecy basket"
category: 
tags: [tls, security, privacy]
---
Recently there has been a [sequence][1] of [recommendations][2] promoting the use of TLS ciphersuites which provide [forward secrecy][], particular in the context of [PRISM][] and [Tempora][].

[1]: https://community.qualys.com/blogs/securitylabs/2013/06/25/ssl-labs-deploying-forward-secrecy
[2]: http://www.theregister.co.uk/2013/06/26/ssl_forward_secrecy/
[forward secrecy]: http://en.wikipedia.org/wiki/Forward_secrecy
[PRISM]: http://en.wikipedia.org/wiki/PRISM_(surveillance_program)
[Tempora]: http://en.wikipedia.org/wiki/Tempora

Unfortunately most browsers have implemented unsafe downgrade behaviour when a TLS connection fails.  Since an attacker can usually invoke such a failure, he can often remove forward secrecy from a TLS connection which would have otherwise had it.  This happens transparently to the user.

This is bad, and surprising.

# Browers behaviour
A browser starts a new TLS connection with the highest (most recent) TLS protocol version it can speak.  If the connection fails early on, it moves down to an older version and retries from the beginning.

Importantly, this downgrade is *outside the protocol version negotiation facilities* that TLS provides: there is no possible binding between the first and subsequent connections, and so the way TLS detects version downgrade is made ineffective.

In concrete terms:

1. User opens a TCP connection to google.com and sends a `ClientHello` with version `TLS1.0` and its set of desired ciphersuites.
2. The adversary intercepts this message, and sends back a TLS fatal alert (the `AlertDescription` seems not to matter, but `handshake_failure` seems most obvious) or merely closes the connection at a TCP level with a `FIN`.  It doesn't matter which.
3. Upon receipt of the alert, the client closes the connection.
4. The client opens a new TCP connection, and sends a `ClientHello` with version `SSL3` and (in all most cases) a poorer set of SSL3 ciphersuites.
5. The adversary passes remaining traffic between the Server and Client without alteration or omission.

Here we made two TCP connections: one for the first TLS1.0 handshake, and one for the SSL3 handshake.

# Survey

(As of July 2013)

Pretending to be Chrome's TLS stack, I simulated the attack against the [top 300][] websites. 209 sites supported any kind of TLS.  Of those, 69 (33%) chose different security parameters under downgrade conditions:

* `TLS_ECDHE_RSA_WITH_RC4_128_SHA` to `TLS_RSA_WITH_RC4_128_SHA`: 50 sites
* `TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA` <br> to `TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA`: 8 sites
* `TLS_RSA_WITH_AES_128_CBC_SHA` to `TLS_RSA_WITH_RC4_128_SHA`: 6 sites
* `TLS_ECDHE_ECDSA_WITH_RC4_128_SHA` to `TLS_RSA_WITH_RC4_128_SHA`: 3 sites
* `TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA` to `TLS_DHE_RSA_WITH_AES_256_CBC_SHA`: 2 sites

So, if you're counting, 53 (25%) *lost forward secrecy under attacker control*.  Notably, this includes all Google properties.

Also, consider an attacker who has a preference for attacking RC4 statistical biases.  The 6 sites which switched to RC4 under downgrade (including all Microsoft properties) just became more appealing,

[top 300]: http://www.alexa.com/topsites

# History
This is not a new discovery.  Browser vendors implemented this downgrade *deliberately* to continue working in the presence of 'middle-boxes' (such as those made by [Bluecoat][], amongst others) which barf on use of modern TLS protocol versions.

Aside: read the 'Resolution' part of [that article][Bluecoat] and try and work out if Bluecoat is evil or merely incompetent.

[Bluecoat]: https://kb.bluecoat.com/index?page=content&id=KB5493  (incompetence in action)

# Affected browsers
(As of March 2013)

* Google Chrome 25.0.1364.172 m (Windows 7 x86_64).
* Google Chrome 25.0.1364.169 (Android 4.1.1).
* Chromium 22.0.1229.94 (Linux Mint x86_64).
* Safari 6.0.3 (Mac OS X v10.8.3).
* Mozilla Firefox 19.0.2 (Windows 7 x86_64).
* Mozilla Firefox 16.0.1 (Linux Mint x86_64).
* Internet Explorer 9.0.8112.16421 (Windows 7 x86_64) both in default configuration and with TLS1.2 enabled.

# Unaffacted browsers
The following products correctly treat fatal alerts as errors, and are not affected.

* Opera 12.14 (Linux Mint x86_64).
* CURL 7.27.0 (Linux Mint x86_64).

# The future
Encouragingly, there is already a formalisation of Opera's sensible behaviour in the form of [Managing and removing automatic version rollback in TLS Clients][rollback].  Less encouragingly, there hasn't been any clear push behind this proposal, or indications that Google, Microsoft or Mozilla will actually implement it.

Worse still, work on TLS1.2 support in NSS (Network Security Services -- used by Chrome and Firefox, amongst others) continues apace.  This is somewhat pointless in any normal attack scenario: the attacker will merely downgrade the client back from TLS1.2.

[rollback]: http://tools.ietf.org/html/draft-pettersen-tls-version-rollback-removal-01

# The code
During this investigation I wrote a [pure python toy TLS stack][tls-hacking].  Please observe the emphasis on **toy**.

[tls-hacking]: https://github.com/ctz/tls-hacking