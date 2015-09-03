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
algorithm's requirements.  AES-based algorithms will be tested with both 128-bit and 256-bit keys,
NORX32 only uses 128-bit keys, and ChaCha20-Poly1305 only uses 256-bit keys.

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

## AES-GCM

Galois Counter Mode is a block cipher mode by McGrew and Viega standardised in [SP800-38D][sp800-38d].

It encrypts the plaintext in counter mode, and authenticates it using a polynomial MAC called GHASH.

Cifra's implementation of GHASH has side-channel countermeasures, which makes it slower than other implementations.

## AES-EAX

EAX is a construction by Bellare, Rogaway and Wagner.  It encrypts the plaintext in counter mode, and authenticates it using CMAC.

## AES-CCM

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
AES-128-CCM | 200048 | 680B  | 2316B     | 70.27KB/s
AES-128-EAX | 210087 | 800B  | 2604B     | 70.07KB/s
AES-128-GCM | 327313 | 700B  | 2644B     | 41.30KB/s
AES-256-CCM | 271787 | 744B  | 2400B     | 51.45KB/s
AES-256-EAX | 285730 | 864B  | 2684B     | 51.35KB/s
AES-256-GCM | 362200 | 764B  | 2728B     | 37.49KB/s
ChaCha20-Poly1305 | 163980 | 756B  | 2728B | 94.23KB/s
NORX32-4-1  | 25115  | 336B  | 1808B     | 717.02KB/s

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
[testcode]: https://github.com/ctz/cifra/blob/2315db11fd5cb7e80e81590933e4502675b84fe5/src/arm/main.c#L261

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

      data.addRows([[0, 29182, 38962, 36723, 38714, 52422, 42327, 33197, 8180], [4, 42243, 50096, 57394, 55703, 67484, 65226, 37151, 10834], [8, 41519, 50176, 57194, 54979, 67564, 64894, 37231, 10858], [12, 40795, 50256, 56928, 54255, 67644, 64661, 37311, 10882], [16, 39969, 50007, 56626, 53429, 67395, 64689, 43089, 10906], [20, 53029, 60896, 77296, 70417, 82212, 86993, 43326, 10930], [24, 52305, 60976, 76667, 69693, 82292, 86034, 43406, 10954], [28, 51581, 61056, 76401, 68969, 82372, 84844, 43486, 10978], [32, 50755, 60807, 75439, 68143, 82123, 84212, 49264, 11002], [36, 63815, 71696, 95977, 85131, 96940, 106549, 49501, 11026], [40, 63091, 71776, 95546, 84407, 97020, 105722, 49581, 11050], [44, 62367, 71856, 94653, 83683, 97100, 105753, 49661, 11074], [48, 61541, 71607, 93328, 82857, 96851, 104626, 55439, 13223], [52, 74601, 82496, 113602, 99845, 111668, 126765, 55676, 13247], [56, 73877, 82576, 113633, 99121, 111748, 125839, 55756, 13271], [60, 73153, 82656, 112344, 98397, 111828, 125177, 55836, 13295], [64, 72327, 82407, 111778, 97571, 111579, 124776, 61614, 13319], [68, 85387, 93296, 132283, 114559, 126396, 147212, 65567, 13343], [72, 84663, 93376, 131192, 113835, 126476, 146319, 65647, 13367], [76, 83939, 93456, 130266, 113111, 126556, 145657, 65727, 13391], [80, 83113, 93207, 129766, 112285, 126307, 144629, 71505, 13415], [84, 96173, 104096, 149908, 129273, 141124, 167329, 71742, 13439], [88, 95449, 104176, 149147, 128549, 141204, 165974, 71822, 13463], [92, 94725, 104256, 148485, 127825, 141284, 165510, 71902, 13487], [96, 93899, 104007, 147721, 126999, 141035, 164812, 77680, 15636], [100, 106959, 114896, 167995, 143987, 155852, 187116, 77917, 15660], [104, 106235, 114976, 167069, 143263, 155932, 186487, 77997, 15684], [108, 105511, 115056, 167133, 142539, 156012, 185891, 78077, 15708], [112, 104685, 114807, 165907, 141713, 155763, 184863, 83855, 15732], [116, 117745, 125696, 186082, 158701, 170580, 206969, 84092, 15756], [120, 117021, 125776, 185849, 157977, 170660, 206406, 84172, 15780], [124, 116297, 125856, 184461, 157253, 170740, 206173, 84252, 15804], [128, 115471, 125607, 183862, 156427, 170491, 204716, 90030, 15828], [132, 128531, 136496, 204169, 173415, 185308, 226492, 93983, 15852], [136, 127807, 136576, 203474, 172691, 185388, 226061, 94063, 15876], [140, 127083, 136656, 202779, 171967, 185468, 225861, 94143, 15900], [144, 126257, 136407, 202213, 171141, 185219, 224866, 99921, 18049], [148, 139317, 147296, 222916, 188129, 200036, 247104, 100158, 18073], [152, 138593, 147376, 221957, 187405, 200116, 246541, 100238, 18097], [156, 137869, 147456, 221361, 186681, 200196, 245714, 100318, 18121], [160, 137043, 147207, 220300, 185855, 199947, 244752, 106096, 18145], [164, 150103, 158096, 240640, 202843, 214764, 267155, 106333, 18169], [168, 149379, 158176, 239780, 202119, 214844, 266163, 106413, 18193], [172, 148655, 158256, 239349, 201395, 214924, 265237, 106493, 18217], [176, 147829, 158007, 238255, 200569, 214675, 264572, 112271, 18241], [180, 160889, 168896, 258661, 217557, 229492, 286678, 112508, 18265], [184, 160165, 168976, 257735, 216833, 229572, 286016, 112588, 18289], [188, 159441, 169056, 257106, 216109, 229652, 285189, 112668, 18313], [192, 158615, 168807, 256507, 215283, 229403, 284623, 118446, 20462], [196, 171675, 179696, 276682, 232271, 244220, 307059, 122399, 20486], [200, 170951, 179776, 275822, 231547, 244300, 305704, 122479, 20510], [204, 170227, 179856, 275589, 230823, 244380, 305339, 122559, 20534], [208, 169401, 179607, 274528, 229997, 244131, 304212, 128337, 20558], [212, 182461, 190496, 294868, 246985, 258948, 326912, 128574, 20582], [216, 181737, 190576, 294602, 246261, 259028, 325920, 128654, 20606], [220, 181013, 190656, 293346, 245537, 259108, 324862, 128734, 20630], [224, 180187, 190407, 292978, 244711, 258859, 324527, 134512, 20654], [228, 193247, 201296, 313186, 261699, 273676, 346666, 134749, 20678], [232, 192523, 201376, 312458, 260975, 273756, 345608, 134829, 20702], [236, 191799, 201456, 311301, 260251, 273836, 345045, 134909, 20726], [240, 190973, 201207, 310966, 259425, 273587, 343687, 140687, 22875], [244, 204033, 212096, 331207, 276413, 288404, 366024, 140924, 22899], [248, 203309, 212176, 330446, 275689, 288484, 365791, 141004, 22923], [252, 202585, 212256, 329784, 274965, 288564, 364733, 141084, 22947], [256, 201759, 212007, 328558, 274139, 288315, 363870, 146862, 22971]]);

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
