---
layout: post
title: "Lucky 13 in Amazon S2N"
subtitle: ""
category: 
tags: [security, tls, aws, s2n]
published: true
---
With the publication of an [excellent technical report][luckymicro] by Martin Albrecht and
Kenny Paterson on the problems
with s2n I thought I'd publish my contemporaneous report to Amazon.

I didn't disclose/publish further at the time because I didn't also discover the second
finding of their paper: that the timing chaff was too coarse to have meaningful effect.

[luckymicro]: http://eprint.iacr.org/2015/1129

{% highlight sh %}
MIME-Version: 1.0
Received: by 10.107.38.146 with HTTP; Tue, 30 Jun 2015 19:32:37 -0700 (PDT)
Date: Wed, 1 Jul 2015 03:32:37 +0100
Delivered-To: jpixton@gmail.com
Message-ID: <CACaGAp=P-zae2uxMbtfe7mkAnmpkz4K3i2rB=GrSaohj762kgg@mail.gmail.com>
Subject: s2n and Lucky 13-like attacks
From: Joseph Birr-Pixton <jpixton@gmail.com>
To: aws-security@amazon.com
Content-Type: text/plain; charset=UTF-8

Hi,

I was looking at the source for s2n, specifically:

https://github.com/awslabs/s2n/blob/master/tls/s2n_cbc.c#L88

I think HMACing the padding is insufficient to ensure a constant
number of compression function applications, due to MD padding.

For instance, consider a 128 byte plaintext passed to this function
(assume HMAC-SHA256):

If the last byte is 74, there are 74 bytes of padding and the message
is 21 bytes. The inner HMAC computation will take 2 blocks (one block
for the key, one for the padded message). The outer HMAC computation
always takes two blocks. HMACing the padding takes one block (hashing
the concatenation of the message and first 43 bytes of the padding).
That's 5 blocks in total.

However, if the last byte is 35 there are 35 bytes of padding and the
message is 60 bytes. The inner HMAC computation will take three blocks
(one block for the key, two blocks for the padded message). The outer
HMAC takes two as before. HMACing the padding takes one block (hashing
the message and 4 bytes of the padding). That's 6 blocks in total.

Here's a chart. These measurements included more than just the HMAC
computation, but you can see the effect.

https://jsfiddle.net/zf4v87p8/3/embedded/result/

I doubt this is practically exploitable, but might be interesting nonetheless.

Thanks,
Joe
{% endhighlight %}