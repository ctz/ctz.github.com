+++
date = 2013-12-17
path = "2013/12/17/crime-vs-zlib"
template = "page.html"
title = "A novel countermeasure against CRIME and BREACH"
subtitle = ""
tags = ["network", "security", "tls", "zlib", "compression"]
+++

* TOC
{:toc}

[CRIME][crime] and [BREACH][breach] are cool practical attacks, described in essence by Kelsey back in 2002.  CRIME targets TLS-level `zlib` compression, while BREACH attacks HTTP `Content-Encoding` `gzip` or `deflate` (which are  equivalent in terms of compression algorithm).

Here I suggest a countermeasure.  I don't suggest anybody implement this without further analysis, but I think it's a fun thought exercise.

# Deflate and zlib compression
First, a quick sketch of how deflate/zlib works.  See [RFC1950][rfc1950] and [RFC1951][rfc1951] for the full details.

A zlib encoding is a short header, a deflate encoding, and then a 32-bit CRC over the input data.  zlib's purpose here is to specify the parameters the decompression algorithm needs to get the right answer, rather than to perform any compression itself.

       deflate window size is 2^(8 + wwww)
       |   compression method is deflate
       |   |      compression level (not used by decompressor)  
       |   |      | preset dictionary (rarely used)
       |   |      | | checksum such that header is 0 mod 0x1f
       |   |      | | |
      /--\/--\   /-\|/--\
    +----------+----------+----------+----------+
    | wwww1000 | LLL0cccc |  deflate stream...  |
    +----------+----------+----------+----------+
    | ...                                       |
    +----------+----------+----------+----------+
    |    Adler-32 CRC over uncompressed data    |
    +----------+----------+----------+----------+

A deflate stream is formatted as a sequence of *blocks*, of varying *types*.  There are three defined types:

* Uncompressed data (type 0).
* Data compressed with well-known Huffman codes (type 1).
* Data compressed with included Huffman codes (type 2).

The latter two blocks types encode sequences of literal byte values and instructions to copy a previous subsequence of bits, as far back as the window extends.

So the plaintext `street by street` might get compressed like this:

    'street by ', COPY(back 10, length 6)
    ^             |
    '-------------'

These back references in a deflate stream are important in the context of CRIME/BREACH, because they mean a plaintext containing two instances of the same string (within the window size) will compress better.  As a trivial example:

    GET /?twid=sec HTTP/1.1
    Host: twitter.com
    Cookie: twid=secret

will compress to a noticably smaller encoding, than:

    GET /?twid=butts HTTP/1.1
    Host: twitter.com
    Cookie: twid=secret

That's because the occurance of 'twid=sec' in the Cookie value will refer back to the HTTP preamble line
in the first example, but will probably get encoded literally in the second.

# Aside: a crappy zlib compressor
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
    

# Countermeasure: dynamic compression window adjustment
Imagine our input to the compressor was the plaintext and a number of positions in the plaintext over which the window must not extend.  For example (position marked with a pipe):

    GET /?twid=sec HTTP/1.1|
    Host: twitter.com
    Cookie: twid=secret

Choosing where to put these marks is a crucial detail.  Surrounding either user-controlled input (like the HTTP preamble above), or sensitive data (like cookies, CSRF tokens, etc.) should work (but the latter seems more convincing because the definition of 'user-controlled' here varies with time).

Now the window when compressing 'twid=secret' in the Cookie like only extends back to the end of the preamble line.

The same idea can be extended to deal with regions of previous plaintext which should not be considered in the window.  This could produce better compressions where a back-ref skips entirely over a region.

## But it's not that simple
Unfortunately this fails to take into account type 2 deflate blocks (those where the huffman codes for literal bytes and back-refs are encoded in the compression).  It is not enough to restrict the back-ref encoding to not cross our regions, because the choice of huffman codes will leak the contents of the region.  We have to either:

* Compress each region separately, then concatenate the deflate blocks into a single stream.  This is inefficient, and will produce non-optimal compressions.
* As well as only considering the window constrained in the current region for back-refs, also only do statistical analysis of the current region when working out the huffman codes for a type 2 block.

Fortunately, these problems are all still in the power of the compressor and don't involve alterations to the deflate format.

[crime]: https://docs.google.com/presentation/d/11eBmGiHbYcHR9gL5nDyZChu_-lCa2GizeuOfaLU2HOU
[breach]: http://breachattack.com/
[rfc1951]: http://tools.ietf.org/html/rfc1951
[rfc1950]: http://tools.ietf.org/html/rfc1950
