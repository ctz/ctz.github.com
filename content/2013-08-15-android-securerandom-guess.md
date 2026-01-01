+++
date = 2013-08-15
path = "2013/08/15/android-securerandom-guess"
template = "page.html"
title = "Android SecureRandom vulnerability guess"
subtitle = ""
tags = ["android", "security", "mobile", "google"]
+++
In which I try to guess where the recent [SecureRandom is not seeded][1] problem is on Android.
First, some background...

[1]: http://android-developers.blogspot.com/2013/08/some-securerandom-thoughts.html

# Zygote
Android tries to improve app startup time and memory usage by forking all normal apps from a 
`zygote` process which contains a copy of the dalvik VM preloaded with a selection of classes.

This means that a new app doesn't need to do this on startup, and most apps can actually end up
sharing most of the same physical pages (thanks to the miracle of [copy-on-write pages][2]).

[2]: http://en.wikipedia.org/wiki/Copy-on-write#Copy-on-write_in_virtual_memory_management

# OpenSSL's `RAND_bytes` behaviour
OpenSSL's [`RAND_bytes`][3] function is OpenSSL's interface to get random material from the single
[CSPRNG][4] within OpenSSL.

[3]: http://www.openssl.org/docs/crypto/RAND_bytes.html
[4]: http://en.wikipedia.org/wiki/Cryptographically_secure_pseudorandom_number_generator

On first call, the default CSPRNG seeds itself from a variety of sources
(as available) and sets an `initialized` flag.  OpenSSL also provides a `RAND_cleanup` function
to reset this flag (amongst other things) such that another call to `RAND_bytes` will reseed
the generator.

# My guess:
Nothing in the Android codebase calls `RAND_cleanup`.  Lots of things call `RAND_bytes`, some via
the tortuous route of JCA.

What would happen if something in zygote used `RAND_bytes`?  OpenSSL would consider its CSPRNG
seeded at that point.  All apps forked from the zygote would inherit the same CSPRNG state,
and produce the same sequence of random material.

This would produce the observed behaviour of reused DSA `k` values in Bitcoin transactions, when
the Bitcoin wallet was started twice from the same zygote (which roughly equates, I think, with
running a wallet, closing it for a while, and running it again within a single phone boot).

# Further assorted observations

## Error handling
Like most callers, Android is not handling errors from `RAND_bytes` properly or `RAND_load_file`
*at all*.

## Quiet, dangerous departure from the `SecureRandom` interface
Android's default implementation of the Java `SecureRandom` SPI (backed by `RAND_bytes`) doesn't
actually meet the documented or specified behaviour.

If I write `new SecureRandom().nextBytes(thing)` I should get the following actions happening behind
the scenes, irrespective of which provider got selected:

1. `new SecureRandom()`: selection and construction of a fresh unseeded generator.
2. `nextBytes(thing)`: automatic seeding of the generator from an entropy source.
3. `nextBytes(thing)`: filling `thing` with some random material.

Because Android backs its default `SecureRandom` implementation with OpenSSL (which has a single
CSPRNG instance, remember) it skips the second step.

So: an application which diligently creates a new `SecureRandom` every so often in the expectation
that it has fresh entropy gets surprised with the same generator every time, without any entropy
being added to it.

That really has to be fixed.