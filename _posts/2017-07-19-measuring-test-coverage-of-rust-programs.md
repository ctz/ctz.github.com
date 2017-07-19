---
layout: post
title: "Measuring test coverage of Rust libraries"
subtitle: ""
category: 
tags: [rust, rustls, programming]
published: false
---

* TOC
{:toc #toc-side}

This is documentation for how I measure the coverage of [rustls][rustls] using the [LLVM "profile" compiler runtime library][compilerrt].

# Previous attempts

Prior to this work, I used [kcov][kcov].  This produced good output, but each test process took around three seconds to start.
One of the test suites runs around 1000 processes, so this meant a full test run took almost an hour (compared to 50 seconds without coverage).

# Origin of this method

See [this thread][kennytm] for my starting point.  This worked to get coverage data out of a simple crate's unit tests.

# Those options in full

  * `-Ccodegen-units=1`
  * `-Clink-dead-code`
  * `-Cpasses=insert-gcov-profiling`
  * `-Zno-landing-pads`
  * `-L/usr/lib/llvm-3.8/lib/clang/3.8.1/lib/linux/ -lclang_rt.profile-x86_64`

# Only profiling relevent code

If you pass in coverage options to a whole compilation, they will apply to everything that cargo builds and
runs during a build.  This quickly fails -- every crate with a `build.rs` will compile it into an executable
called `build_script_build` whose coverage output data will be mutually imcompatible and written to the same place.

This is achieved by passing into `cargo` a [`RUSTC_WRAPPER`][cargoenv] program.  This parses the arguments
to `rustc` and decides whether to include the contents of an environment variable `COVERAGE_OPTIONS` depending
on which `--crate-name` is currently being built.

This is a pretty blunt shell script:

```bash
#!/bin/bash -e

get_crate_name()
{
  while [[ $# -gt 1 ]] ; do
    v=$1
    case $v in
      --crate-name)
        echo $2
        return
        ;;
    esac
    shift
  done
}

case $(get_crate_name "$@") in
  rustls|tlsclient|tlsserver|features|...)
    EXTRA=$COVERAGE_OPTIONS
    ;;
  *)
    ;;
esac

exec "$@" $EXTRA
```



-----

[rustls]: https://github.com/ctz/rustls
[kcov]: https://github.com/SimonKagstrom/kcov
[compilerrt]: https://compiler-rt.llvm.org/
[kennytm]: https://users.rust-lang.org/t/howto-generating-a-branch-coverage-report/8524/2
[cargoenv]: https://github.com/rust-lang/cargo/blob/master/src/doc/environment-variables.md
