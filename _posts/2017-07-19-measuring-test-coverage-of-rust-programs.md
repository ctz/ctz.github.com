---
layout: post
title: "Measuring test coverage of Rust libraries"
subtitle: ""
category: 
tags: [rust, rustls, programming]
published: true
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

  * `-Ccodegen-units=1` -- build everything into one compilation unit.
  * `-Clink-dead-code` -- don't delete unused code at link-time.
  * `-Zno-landing-pads` -- disable panic unwinding, which would otherwise insert code only reachable on panic.
  * `-Cpasses=insert-gcov-profiling` -- include the compiler pass that calls functions in the following library to track coverage.
  * `-L/usr/lib/llvm-3.8/lib/clang/3.8.1/lib/linux/ -lclang_rt.profile-x86_64` -- runtime library that emits coverage output to file.

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

# Running unit tests

This looks like:

```bash
$ cargo clean
$ rm -rf *.gcda *.gcno
$ env COVERAGE_OPTIONS="-Ccodegen-units=1 -Clink-dead-code -Cpasses=insert-gcov-profiling \
  -Zno-landing-pads -L/usr/lib/llvm-3.8/lib/clang/3.8.1/lib/linux/ -lclang_rt.profile-x86_64" \
  RUSTC_WRAPPER="./admin/coverage-rustc" cargo rustc --all-features --profile test --lib
$ ./target/debug/rustls-cae6999c58b6598a
```

# Combining unit test and integration test coverage

Because the crate's library code gets recompiled between unit test and integration tests, the coverage output for the library
is incompatible between two runs.  It's therefore necessary to capture the coverage data after running the unit tests,
then delete the `.gcno` and `.gcda` files before running integration tests.

This extract is done with `lcov`:

```bash
$ lcov --gcov-tool ./admin/llvm-gcov --rc lcov_branch_coverage=1 --rc lcov_excl_line=assert \
  --capture --directory . --base-directory . -o rustls.info
```

Here, `admin/llvm-gcov` is a shell script to glue `llvm-cov` to `lcov`:

```bash
#!/bin/sh -e
llvm-cov gcov $*
```

# Running integration tests

This involves building and running all the example code and integration tests.

```bash
$ cargo clean
$ rm -rf *.gcda *.gcno
$ env COVERAGE_OPTIONS="-Ccodegen-units=1 -Clink-dead-code -Cpasses=insert-gcov-profiling \
  -Zno-landing-pads -L/usr/lib/llvm-3.8/lib/clang/3.8.1/lib/linux/ -lclang_rt.profile-x86_64" \
  RUSTC_WRAPPER="./admin/coverage-rustc" cargo rustc --all-features --profile dev --example tlsclient
$ ...
$ env COVERAGE_OPTIONS="-Ccodegen-units=1 -Clink-dead-code -Cpasses=insert-gcov-profiling \
  -Zno-landing-pads -L/usr/lib/llvm-3.8/lib/clang/3.8.1/lib/linux/ -lclang_rt.profile-x86_64" \
  RUSTC_WRAPPER="./admin/coverage-rustc" cargo rustc --all-features --profile dev --test api
$ ./target/debug/api-d608a762dc73a945
$ ...
```

Once all these tests have run, we need to capture the resulting coverage data.  Again, we use `lcov`:

```bash
$ lcov --gcov-tool ./admin/llvm-gcov --rc lcov_branch_coverage=1 --rc lcov_excl_line=assert \
  --capture --directory . --base-directory . -o tests.info
```

We now have `rustls.info` containing the unit test coverage, and `tests.info` containing the integration
test coverage.  These need to be merged together:

```bash
$ lcov --gcov-tool ./admin/llvm-gcov --rc lcov_branch_coverage=1 --rc lcov_excl_line=assert \
  --add rustls.info \
  --add tests.info \
  -o coverage.info
```

Now `coverage.info` contains all the coverage data for everything touched during our tests.  We now need
to reduce this to just code we're interested in (cutting out things in runtime libraries, the standard library, etc.).
This invocation also cuts out coverage of example/integration test code, which we're not particularly interested in.

```bash
$ lcov --gcov-tool ./admin/llvm-gcov --rc lcov_branch_coverage=1 --rc lcov_excl_line=assert \
  --extract coverage.info `pwd`/src/* -o final.info
```

Now `final.info` contains just coverage we're interested in.  Finally, we can generate a nice HTML report
with `lcov`'s `genhtml` tool:

```bash
$ genhtml --branch-coverage --demangle-cpp --legend final.info -o target/coverage/ --ignore-errors source
```

# Reporting to coveralls.io

One nice thing that kcov made easy was [uploading coverage data to coveralls.io][coveralls].  I found the `coveralls-lcov`
ruby gem did a fine job of this:

```bash
$ gem install coveralls-lcov
$ coveralls-lcov final.info
```

-----

[rustls]: https://github.com/ctz/rustls
[kcov]: https://github.com/SimonKagstrom/kcov
[compilerrt]: https://compiler-rt.llvm.org/
[kennytm]: https://users.rust-lang.org/t/howto-generating-a-branch-coverage-report/8524/2
[cargoenv]: https://github.com/rust-lang/cargo/blob/master/src/doc/environment-variables.md
[coveralls]: https://coveralls.io/github/ctz/rustls
