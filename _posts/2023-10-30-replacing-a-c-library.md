---
layout: post
title: "Replacing a C library: a testing strategy"
subtitle: ""
category: 
tags: [rust, c, rewrite, riir]
---

Say we have an existing C library, and it's already well integrated with applications. But we no longer have confidence in it, so we want to replace it without existing applications having to care. We want some confidence that our replacement doesn't change the observable behaviour of the library, so that our rewrite can be a drop-in replacement with minimal risk.

This is a software testing problem.

If the existing library has a test suite -- great! We can certainly reuse that. But, generally, test suites built up alongside a library fall considerably short of precisely defining the behaviour of the library.

Let's attack a fictitious example. Here's a simple interface to an image codec:

```
size_t ImageEncodeRGB(const uint8_t* rgb, int width, int height, int stride,
                     float quality_factor, uint8_t** output);
uint8_t* ImageDecodeRGB(const uint8_t* data, size_t data_size,
                                   int* width, int* height);
void ImageFree(void* ptr)
```

Do you think the original library has a test case that describes the behaviour for `ImageEncodeRGB` with `quality_factor = 50`? `quality_factor = -1`? `quality_factor = NaN`? `quality_factor = 0`? `quality_factor = -Inf`?

This is the level of fidelity I think we need to achieve to have confidence our replacement doesn't cause regressions. And that is one parameter, in one function, with unknown interdependencies with other parameters.

The state space here is ginormous, and the idea that we'll start by writing an exhaustive test suite for the existing library feels hopeless.

Fortunately, we have some tools for exploring large state spaces in software: fuzzers.

## Glueing a fuzzer to a C API

It's not a new idea to view fuzzer input as an informal bytecode format, and dispatch to a bunch of different functions based on some of the input. Something like:

```
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t len) {
  if (len == 0) {
    return 0;
  }
  const uint8_t *rest = data + 1;
  len -= 1;
  switch (data[0]) {
  case 0:
    CallFunctionA(rest, len);
    break;
  case 1:
    CallFunctionB(rest, len);
    break;
  /* etc. */
  default:
    break;
  }
}
```

But let's take that idea to its logical conclusion:

- a fuzzer input maps to an **operation** and its **entire valid input space**,
- the **entire input space** needs to cover everything that can affect the output; that means any non-determinism needs to be eliminated (this is necessary anyway for effective fuzzing).
- **an operation** can map down to several API calls, e.g. a successful call to `ImageDecodeRGB` should be followed by `ImageFree`, to avoid memory leaks and ensure the intended relation between the two calls is maintained.
- the fuzzer harness should pretty-print the results of each API call; that would include return codes, image data -- everything. This is an odd thing to do in normal fuzzing, but becomes important for us later.
- for the sake of people's sanity, the fuzzer harness should also pretty-print the input to the API calls, so it is clear what API surface a given fuzzer input is exercising.
- if the fuzzer input is not valid (e.g. it is too short to cover all the parameters needed for an operation), the fuzzing harness should just return as soon as possible.

In the above example, one operation could be `ImageEncodeRGB`, with its input image data, width, height, stride and quality. In this case, it would be necessary to validate the size of the image data against the size expected by the library (implied by stride and height). Naturally, the glue between the fuzzer input and API functions needs to be memory safe in a basic sense.

That means one run of the fuzzing harness could be:

```
ImageDecodeRGB(0102030405060708, 8, …)
output:
deadbeef
width=3 height=4
```

These transcripts are a good ingredient for use in other tests – just storing input/expected output pairs in version control is a nice way of recording regression test cases.

## What now?
At this point we have a fuzzer that exercises the entirety of the API (inputs and outputs!) we care about, though nothing cares about the output. We can compile that against either the original or rewritten library.

What we're working towards is property-based testing, and the property we're interested in is that our new rewritten library has the same observable behaviour as the original.

Well, we can trivially get there by feeding each input to both libraries, and asserting that they produce precisely the same output.

Now we can run the fuzzer: each failing test identifies a place where the new library departs from the behaviour of the original.
