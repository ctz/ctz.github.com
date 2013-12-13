---
layout: post
title: "A novel countermeasure against CRIME and BREACH"
subtitle: ""
category: 
published: false
tags: [network, security, tls]
---
[CRIME][crime] and [BREACH][breach] are cool practical attacks, described in essence by Kelsey back in 2002.  CRIME targets TLS-level `zlib` compression, while BREACH attacks HTTP `Content-Encoding` `gzip` or `deflate` (which are  equivalent in terms of compression algorithm).

Here I suggest two countermeasures.  I don't suggest anybody implements these without significant further analysis, but I think they're a fun thought exercise.

# DEFLATE and zlib compression
First, a quick sketch of how DEFLATE/zlib works.  See [RFC1950][rfc1950] and [RFC1951][rfc1951] for the full details.

A zlib encoding is a short header, a DEFLATE encoding, and then a 32-bit CRC over the input data.  zlib's purpose here is to specify the parameters the decompression algorithm needs to get the right answer, rather than to perform any compression itself.

       DEFLATE window size is 2^(8 + wwww)
       |   compression method is DEFLATE
       |   |      compression level (not used by decompressor)  
       |   |      | preset dictionary (rarely used)
       |   |      | | checksum such that header is 0 mod 0x1f
       |   |      | | |
      /--\/--\   /-\|/--\
    +----------+----------+----------+----------+
    | wwww1000 | LLL0cccc |  DEFLATE stream...  |
    +----------+----------+----------+----------+
    | ...                                       |
    +----------+----------+----------+----------+
    |    Adler-32 CRC over uncompressed data    |
    +----------+----------+----------+----------+

A DEFLATE stream is formatted as a sequence of *blocks*, of varying *types*.  There are three defined types:

* Uncompressed data (type 0).
* Data compressed with well-known Huffman codes (type 1).
* Data compressed with included Huffman codes (type 2).

The latter two blocks types encode sequences of literal byte values and instructions to copy a previous subsequence of bits, as far back as the window extends.

So the plaintext `street by street` might get compressed like this:

    'street by ', COPY(back 10, length 6)
    ^             |
    '-------------'

These back references in a DEFLATE stream are important, because they mean a plaintext containing two instances of the same string (within the window size) will compress better.  As a trivial example:

    GET /?twid=sec HTTP/1.1
    Host: twitter.com
    Cookie: twid=secret

will compress to a noticably smaller encoding, than:

    GET /?twid=butts HTTP/1.1
    Host: twitter.com
    Cookie: twid=secret

That's because the occurance of 'twid=sec' in the Cookie value will refer back to the HTTP preamble line
in the first example, but will probably get encoded literally in the second.
    
# Aside 1: a crappy zlib compressor
I hereby present the world's stupidest zlib 'compressor':

    from zlib import adler32

    def compress(inp):
        ll = len(inp)
        assert ll <= 0xffff
        
        # a single, final, uncompressed block
        block = bytes([0b00000001]) + \
                ll.to_bytes(2, 'little') + \
                (ll ^ 0xffff).to_bytes(2, 'little')
        
        # zlib (fake window size, compression level)
        zlib_header = bytes([0b01111000, 0b10011100])
        
        csum = adler32(inp).to_bytes(4, 'big')
        
        return zlib_header + block + inp + csum

    if __name__ == '__main__':
        import zlib
        m = b'hello world'
        c = compress(m)
        assert len(c) > len(m) # whoops
        assert zlib.decompress(c) == m

# Countermeasure 1: dynamic compression window adjustment
Imagine our input to the compressor was the plaintext and a number of positions in the plaintext over which the window must not extend.  For example (position marked with a pipe):

    GET /?twid=sec HTTP/1.1|
    Host: twitter.com
    Cookie: twid=secret

Choosing where to put these marks is an important detail.  Surrounding either user-controlled input (like the HTTP preamble above), or sensitive data (like cookies, CSRF tokens, etc.) should work (but the latter seems like a safer idea).

Now the window when compressing 'twid=secret' in the Cookie like only extends back to the end of the preamble line.

[crime]: https://docs.google.com/presentation/d/11eBmGiHbYcHR9gL5nDyZChu_-lCa2GizeuOfaLU2HOU
[breach]: http://breachattack.com/
[rfc1951]: http://tools.ietf.org/html/rfc1951
[rfc1950]: http://tools.ietf.org/html/rfc1950