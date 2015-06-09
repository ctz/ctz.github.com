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

How does modern authenticated encryption run on such devices?

# Methodology

We'll measure encryption of different length plaintexts.  Each encryption will include a 16-byte
additionally authenticated data (AAD).  Nonce lengths and key sizes are chosen to match each
algorithm's requirements.  NORX32 uses a 128-bit key, other algorithms use a 256-bit key. 

For each encryption, we'll count the number of cycles.  We'll also measure the stack usage and program size.

We count cycles by setting up the standard ARM systick peripheral to tick down once per cycle.  When
it reaches zero, we increment a counter and the systick is reloaded with its maximum value (`0xffffff`).

We measure stack usage by filling the stack with a pattern before a test starts (from the bottom
upwards to its current extent), and then checking how the pattern was overwritten after the test.

We measure program size statically by reading the size of the text section of each test program.
We subtract from this the size of a test program which does nothing.  All code is built with `-Os`
(optimise for size first, speed second) and linked with `-gc-sections` to remove unused functions.

## Code

[Cifra][cifra] is a collection of cryptography primitives in standard C, targetted towards small embedded devices.
The code is intended to be clear, simple, and small.  The aim is understanding and quality code, not speed records.

The functions beginning [`aeadperf_`][testcode] is the code we're benchmarking.

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

This is a construction recently standardised in [RFC7539][rfc7539], glueing together the [ChaCha20][chacha] stream cipher and [Poly1305 one-time MAC][poly1305] to give a general purpose AEAD scheme.

# Results

For encrypting a 256-byte message:

Algorithm   | Cycles | Stack | Code size | Likely throughput[^3]
---------   | ------ | ----- | --------- | -----------------
AES-256-CCM | 271787 | 744B  | 2400B     | 51.44KB/s
AES-256-EAX | 285730 | 864B  | 2684B     | 51.34KB/s
AES-256-GCM | 362200 | 764B  | 2728B     | 37.49KB/s
ChaCha20-Poly1305 | 163980 | 756B  | 2728B | 94.22KB/s
NORX32-4-1  | 25115  | 336B  | 1808B     | 717.0KB/s

Even adjusting for the different security bound, NORX leads in every metric.

<script type="text/javascript" src="https://www.google.com/jsapi"></script>
<div id="full_chart_div"></div>


In this chart you can clearly see the 16-byte block size of AES and Poly1305.  You can also
see the 40-byte input block size of NORX32, and the 64-byte block size of ChaCha20.

The slight *decrease* in cycles for larger message sizes between whole blocks in CCM and GCM
is due to relatively slow code which adds padding -- it needs to add more padding for these
sizes.  This is an area for improvement.

---

[^1]: From [Farnell, in single quantities][farnell].  Costs vastly decrease with quantity, or if you [buy from chinese suppliers][aliexpress].
[^2]: Source: [486DX2 50Mhz cost][486-cost] adjusted for today's money.
[^3]: This is for one, long message.  It therefore discounts set-up costs.
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
[chacha]: http://cr.yp.to/chacha.html
[poly1305]: http://cr.yp.to/mac.html
[testcode]: https://github.com/ctz/cifra/blob/832ade9903604c17a6a40becc48b79ed0feab133/src/arm/main.c#L261

<script>
google.load('visualization', '1', {packages: ['corechart', 'scatter']});
google.setOnLoadCallback(drawBasic);

function drawBasic() {

      var data = new google.visualization.DataTable();
      data.addColumn('number', 'X');
      data.addColumn('number', 'AES-128-CCM');
      data.addColumn('number', 'AES-128-EAX');
      data.addColumn('number', 'AES-128-GCM');
      data.addColumn('number', 'AES-256-CCM');
      data.addColumn('number', 'AES-256-EAX');
      data.addColumn('number', 'AES-256-GCM');
      data.addColumn('number', 'ChaCha20-Poly1305');
      data.addColumn('number', 'NORX32-4-1');

      data.addRows([[0, 29268, 38838, 36731, 38543, 52017, 42102, 36632, 8379], [4, 42346, 49899, 57345, 55525, 66982, 64932, 40437, 10949], [8, 41578, 49967, 57137, 54757, 67050, 64592, 40505, 10973], [12, 40810, 50035, 56863, 53989, 67118, 64351, 40573, 10997], [16, 39938, 49767, 56551, 53117, 66850, 64369, 47271, 11021], [20, 53020, 60587, 77169, 70103, 81574, 86609, 47502, 11045], [24, 52252, 60655, 76532, 69335, 81642, 85642, 47570, 11069], [28, 51484, 60723, 76258, 68567, 81710, 84444, 47638, 11093], [32, 50612, 60455, 75286, 67695, 81442, 83802, 54336, 11117], [36, 63694, 71275, 95772, 84681, 96166, 106075, 54567, 11141], [40, 62926, 71343, 95333, 83913, 96234, 105240, 54635, 13274], [44, 62158, 71411, 94432, 83145, 96302, 105263, 54703, 13298], [48, 61286, 71143, 93097, 82273, 96034, 104126, 61401, 13322], [52, 74368, 81963, 113319, 99259, 110758, 126201, 61632, 13346], [56, 73600, 82031, 113342, 98491, 110826, 125267, 61700, 13370], [60, 72832, 82099, 112045, 97723, 110894, 124597, 61768, 13394], [64, 71960, 81831, 111469, 96851, 110626, 124186, 68466, 13418], [68, 85042, 92651, 131922, 113837, 125350, 146558, 72275, 13442], [72, 84274, 92719, 130823, 113069, 125418, 145657, 72343, 13466], [76, 83506, 92787, 129889, 112301, 125486, 144987, 72411, 13490], [80, 82634, 92519, 129379, 111429, 125218, 143949, 79109, 15623], [84, 95716, 103339, 149469, 128415, 139942, 166585, 79340, 15647], [88, 94948, 103407, 148700, 127647, 140010, 165222, 79408, 15671], [92, 94180, 103475, 148030, 126879, 140078, 164750, 79476, 15695], [96, 93308, 103207, 147256, 126007, 139810, 164042, 86174, 15719], [100, 106390, 114027, 167478, 142993, 154534, 186282, 86405, 15743], [104, 105622, 114095, 166544, 142225, 154602, 185645, 86473, 15767], [108, 104854, 114163, 166600, 141457, 154670, 185041, 86541, 15791], [112, 103982, 113895, 165364, 140585, 154402, 184003, 93239, 15815], [116, 117064, 124715, 185487, 157571, 169126, 206045, 93470, 15839], [120, 116296, 124783, 185246, 156803, 169194, 205474, 93538, 17972], [124, 115528, 124851, 183850, 156035, 169262, 205233, 93606, 17996], [128, 114656, 124583, 183241, 155163, 168994, 203766, 100304, 18020], [132, 127738, 135403, 203496, 172149, 183718, 225478, 104113, 18044], [136, 126970, 135471, 202793, 171381, 183786, 225039, 104181, 18068], [140, 126202, 135539, 202090, 170613, 183854, 224831, 104249, 18092], [144, 125330, 135271, 201514, 169741, 183586, 223826, 110947, 18116], [148, 138412, 146091, 222165, 186727, 198310, 246000, 111178, 18140], [152, 137644, 146159, 221198, 185959, 198378, 245429, 111246, 18164], [156, 136876, 146227, 220594, 185191, 198446, 244594, 111314, 18188], [160, 136004, 145959, 219523, 184319, 198178, 243622, 118012, 20321], [164, 149086, 156779, 239811, 201305, 212902, 265961, 118243, 20345], [168, 148318, 156847, 238943, 200537, 212970, 264961, 118311, 20369], [172, 147550, 156915, 238504, 199769, 213038, 264027, 118379, 20393], [176, 146678, 156647, 237400, 198897, 212770, 263352, 125077, 20417], [180, 159760, 167467, 257754, 215883, 227494, 285394, 125308, 20441], [184, 158992, 167535, 256820, 215115, 227562, 284724, 125376, 20465], [188, 158224, 167603, 256183, 214347, 227630, 283889, 125444, 20489], [192, 157352, 167335, 255574, 213475, 227362, 283313, 132142, 20513], [196, 170434, 178155, 275697, 230461, 242086, 305685, 135951, 20537], [200, 169666, 178223, 274829, 229693, 242154, 304322, 136019, 22670], [204, 168898, 178291, 274588, 228925, 242222, 303949, 136087, 22694], [208, 168026, 178023, 273517, 228053, 241954, 302812, 142785, 22718], [212, 181108, 188843, 293805, 245039, 256678, 325448, 143016, 22742], [216, 180340, 188911, 293531, 244271, 256746, 324448, 143084, 22766], [220, 179572, 188979, 292267, 243503, 256814, 323382, 143152, 22790], [224, 178700, 188711, 291889, 242631, 256546, 323037, 149850, 22814], [228, 191782, 199531, 312045, 259617, 271270, 345112, 150081, 22838], [232, 191014, 199599, 311309, 258849, 271338, 344046, 150149, 22862], [236, 190246, 199667, 310144, 258081, 271406, 343475, 150217, 22886], [240, 189374, 199399, 309799, 257209, 271138, 342107, 156915, 25019], [244, 202456, 210219, 329988, 274195, 285862, 364380, 157146, 25043], [248, 201688, 210287, 329219, 273427, 285930, 364139, 157214, 25067], [252, 200920, 210355, 328549, 272659, 285998, 363073, 157282, 25091], [256, 200048, 210087, 327313, 271787, 285730, 362200, 163980, 25115]]);

      var options = {
        hAxis: {
          title: 'Message size (bytes)'
        },
        vAxis: {
          title: 'Cycles'
        },
        width: 600,
        height: 800,
        backgroundColor: '#dddddd',
        chartArea: {left: 150, width: '100%', height: '80%'},
        legend: {position: 'top', maxLines: 3},
      };

      var chart = new google.visualization.LineChart(document.getElementById('full_chart_div'));

      chart.draw(data, options);
    }
</script>
