---
layout: post
title: "Benchmarking Modern Authenticated Encryption on €1 devices"
subtitle: ""
category: 
tags: [security, crypto, embedded, authentication, iot]
---

* TOC
{:toc #toc-side}

You can get a lot of embedded processing power for a euro these days.

An ARM Cortex-M0-based STM32F030 costs €1.11[^1] and has approximately the computing power of a 1994-era 486 costing about €416[^2].

[Cifra][cifra] is my collection of cryptography primitives in standard C, targetted towards small embedded devices.
How does modern authenticated encryption run on such devices?

# Methodology

We'll measure encryption of different length plaintexts.  Each encryption will include a 16-byte
additionally authenticated data (AAD).  Nonce lengths are chosen to match each algorithm's requirements.
All algorithms use a 256-bit key.

For each encryption, we'll count the number of cycles.  We'll also measure the stack usage and program size.

We count cycles by setting up the standard ARM systick peripheral to tick down once per cycle.  When
it reaches zero, we increment a counter and the systick is reloaded with its maximum value (`0xffffff`).

We measure stack usage by filling the stack with a pattern before a test starts (from the bottom
upwards to its current extent), and then checking how the pattern was overwritten after the test.

We measure program size statically by reading the size of the text section of each test program.
We subtract from this the size of a test program which does nothing.  All code is built with `-Os`
(optimise for size first, speed second) and linked with `-gc-sections` to remove unused functions.

## Hardware

Our hardware is a STM32F030F4P6 soldered to a breakout board, which is connected directly to a STLinkV2
debugger.  The total cost is:

Item                        |  Supplier    |  Cost
----                        |  --------    |  ----
[STM32F030F4P6][farnell]    |  Farnell     |  £0.80 / €1.11
[STLinkV2 clone][stlinkv2]  |  Aliexpress  |  £2.06 / €2.87
[TSSOP20 breakout][tssop20] |  Aliexpress  |  £2.68 for 20 / €3.73
*Total*                     |              |  £5.54 / €7.71

# The contenders

## AES256-GCM

Galois Counter Mode is a block cipher mode by McGrew and Viega standardised in [SP800-38D][sp800-38d].

It encrypts the plaintext in counter mode, and authenticates it using a polynomial MAC called GHASH.

Cifra's implementation of GHASH has side-channel countermeasures, which makes it slower than other implementations.

## AES256-EAX

EAX is a construction by Bellare, Rogaway and Wagner.  It encrypts the plaintext in counter mode, and authenticates it using CMAC.

## AES256-CCM

CCM is a construction by Housley, Whiting and Ferguson.  It encrypts the plaintext in counter mode, and authenticates it using CBC-MAC.

Because CBC-MAC doesn't actually work very well, CCM has a convoluted internal structure and cannot encrypt
messages without knowing the length beforehand.

CCM is widely used in other communications protocols like Bluetooth, IPSec, and WPA2.

## NORX32-4-1

[Norx][norx] a candidate in the [CAESAR competition][caesar] and is by Aumasson, Jovanovic and Neves.
It's a very new AEAD algorithm with flavours of Salsa/ChaCha (the core permutation) and Keccak (the sponge structure).

The notation `NORX32-4-1` means an instance of NORX using 32-bit words, 4 rounds and no parallelisation.
One NORX round is worth two Salsa/ChaCha rounds, so this is about the same as ChaCha8.
You can expect this to have a lower security bound than ChaCha20, but also be about 2.5 times quicker.

## ChaCha20-Poly1305

This is a construction recently standardised in [RFC7539][rfc7539], glueing together the ChaCha20 stream cipher and Poly1305 one-time MAC to give a general purpose AEAD scheme.

[^1]: From [Farnell, in single quantities][farnell].  Costs vastly decrease with quantity, or if you [buy from chinese suppliers][aliexpress].
[^2]: Source: [486DX2 50Mhz cost][486-cost] adjusted for today's money.
[farnell]: http://uk.farnell.com/stmicroelectronics/stm32f030f4p6tr/mcu-32bit-cortex-m0-48mhz-tssop/dp/2432084
[aliexpress]: http://www.aliexpress.com/item/Free-shipping-10pcs-Lot-STM32F030F4P6-STM32F030F/32346098332.html
[stlinkv2]: http://www.aliexpress.com/item/FREE-SHIPPING-ST-Link-V2-stlink-mini-STM8STM32-STLINK-simulator-download-programming-With-Cover/1766455290.html
[tssop20]: http://www.aliexpress.com/item/20pcs-LOT-TSSOP20-SSOP20-MSOP20-SOP20-TURN-DIP20-20pin-IC-adapter-Socket-Adapter-plate-PCB-PCB/1719764709.html
[486-cost]: https://books.google.co.uk/books?id=FzsEAAAAMBAJ&pg=PA5&lpg=PA5&dq=486+50mhz+1994+price&source=bl&ots=hIyb58Hjw9&sig=0AS3jTLuZNsLMrNa-lvKc8TchKk&hl=en&sa=X&ei=pEdrVbWcAYO1sASEh4CYAg&ved=0CC0Q6AEwAg#v=onepage&q=486%2050mhz%201994%20price&f=false
[cifra]: https://github.com/ctz/cifra
[rfc7539]: https://tools.ietf.org/html/rfc7539
[norx]: https://norx.io
[caesar]: http://competitions.cr.yp.to/caesar.html
[sp800-38d]: http://csrc.nist.gov/publications/nistpubs/800-38D/SP-800-38D.pdf
