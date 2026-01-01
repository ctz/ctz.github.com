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
