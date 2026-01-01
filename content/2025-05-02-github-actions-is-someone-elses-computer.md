+++
date = 2025-05-02
path = "2025/05/02/github-actions-is-someone-elses-computer"
template = "page.html"
title = "GitHub Actions is Someone Else's Computer"
tags = ["security", "supply chain"]
+++

Your project should treat GitHub Actions like Someone Else's Computer.

What do I mean by that?  Well, I view GHA runners as public, unsecured
shell boxes that I can run scripts on.  They can check out and build
public code, but at no point should they be given any kind of privileges
or secrets.

Why is that? Well, I view the engineering discipline that went into
GHA as similar to PHP4-era web security in the early 2000s --
"unsafe at any speed".  They are functionally similar in a way -- uncontrolled
string interpolation, no type system, no tainting, no meaningful software
testing.  A stringly-typed carambolage.

**Treating GHA like this is freeing.**

There's no supply chain risk -- you're stealing a read only `GITHUB_TOKEN`
to a public open source repository?  We had a tool for this, it was called
"git clone https://github.com/shaddap/yaface".

Your creaky CI scripts need Python 2 linked against OpenSSL 0.9.8xxzz?
Wonderful! Beautiful work.

**Treating GHA like this is restrictive.**

An action can _never_ have commit privileges, or any other privilege more
than any GH user.  External services wanting to alter something (like, post
on a PR) need to be a GitHub App, they cannot use `GITHUB_TOKEN`.

Packages (Rust crates, PyPI packages, ..) cannot be published automatically
from a GitHub Action.  GHA in this model cannot keep secrets, and nor should
it ever be given OIDC `id-token: write` permissions.  So neither publishing
directly nor as a "trusted publisher" can work.

**But... but... my workflows!  My PR labeller!**

If you can't swing this, [zizmor](https://github.com/woodruffw/zizmor) is good.
GitHub should fund remedial tooling like this.
