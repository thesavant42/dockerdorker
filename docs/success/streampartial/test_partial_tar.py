"""
Partial tar.gz streaming experiment.

Goal: Parse tar headers from the FIRST N KB of a layer blob,
then close the connection - getting a partial file listing
without downloading the full layer.
"""

import io
import gzip
import struct
import requests
from dataclasses import dataclass

# Test layer URL
TEST_URL = "http://msnasty.local/sha256_ea4ac7c2aed5e8bd05e7fcc8c0cd77ade510c4daf1690cfe93167a634eb81e4f.tar.gz"


@dataclass
class TarEntry:
    name: str
    size: int
    typeflag: str
    is_dir: bool


def parse_tar_header(data: bytes, offset: int = 0) -> tuple[TarEntry | None, int]:
    """
    Parse a 512-byte tar header at the given offset.
    
    Returns (entry, next_offset) or (None, -1) if invalid.
    
    Tar header structure (POSIX ustar):
    - 0-99: filename (100 bytes, null-terminated)
    - 100-107: mode (8 bytes octal)
    - 108-115: uid (8 bytes)
    - 116-123: gid (8 bytes)
    - 124-135: size (12 bytes octal)
    - 136-147: mtime (12 bytes)
    - 148-155: checksum (8 bytes)
    - 156: typeflag (1 byte)
    - 157-256: linkname (100 bytes)
    - 257-262: magic "ustar\0" or "ustar " (6 bytes)
    - ... more fields
    """
    if offset + 512 > len(data):
        return None, -1
    
    header = data[offset:offset + 512]
    
    # Check for null block (end of archive)
    if header == b'\x00' * 512:
        return None, -1
    
    # Check magic at offset 257 ("ustar")
    magic = header[257:262]
    if magic != b'ustar' and magic[:5] != b'ustar':
        # Might be GNU tar or old format, try anyway
        pass
    
    # Parse filename (first 100 bytes, null-terminated)
    name_bytes = header[0:100]
    name = name_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
    
    # Parse size (12 bytes octal at offset 124)
    size_bytes = header[124:136].rstrip(b'\x00').strip()
    try:
        size = int(size_bytes, 8) if size_bytes else 0
    except ValueError:
        size = 0
    
    # Parse typeflag (1 byte at offset 156)
    typeflag = chr(header[156]) if header[156] else '0'
    
    # Calculate next header offset (header + content + padding to 512 boundary)
    content_blocks = (size + 511) // 512  # Round up to 512-byte blocks
    next_offset = offset + 512 + (content_blocks * 512)
    
    entry = TarEntry(
        name=name,
        size=size,
        typeflag=typeflag,
        is_dir=(typeflag == '5' or name.endswith('/'))
    )
    
    return entry, next_offset


def peek_layer(url: str, initial_bytes: int = 65536) -> list[TarEntry]:
    """
    Fetch only the first N bytes of a layer, decompress, and parse tar headers.
    
    This gives us a partial file listing without downloading the full layer.
    """
    print(f"Fetching first {initial_bytes:,} bytes from {url[:50]}...")
    
    # Use HTTP Range header to fetch only first N bytes
    headers = {"Range": f"bytes=0-{initial_bytes - 1}"}
    resp = requests.get(url, headers=headers, stream=True)
    
    # Check if server supports Range requests
    if resp.status_code == 206:
        print(f"Server supports Range requests (206 Partial Content)")
    elif resp.status_code == 200:
        print(f"Server returned full content (no Range support), reading first {initial_bytes} bytes")
    
    # Read only what we need
    compressed_data = resp.raw.read(initial_bytes)
    resp.close()
    
    print(f"Downloaded: {len(compressed_data):,} bytes")
    
    # Check gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2:
        print("Not enough data")
        return []
    
    if compressed_data[0:2] != b'\x1f\x8b':
        print(f"Not gzip: magic bytes are {compressed_data[0:2].hex()}")
        return []
    
    print("Found gzip magic bytes")
    
    # Decompress what we have
    try:
        # gzip.decompress expects complete stream, so use zlib directly
        import zlib
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = gzip format
        decompressed = decompressor.decompress(compressed_data)
        print(f"Decompressed: {len(decompressed):,} bytes")
    except Exception as e:
        print(f"Decompression error (expected for partial data): {e}")
        # Try with what we got before error
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decompressed = b""
        try:
            decompressed = decompressor.decompress(compressed_data)
        except:
            pass
        print(f"Partial decompression got: {len(decompressed):,} bytes")
    
    if len(decompressed) < 512:
        print("Not enough decompressed data for tar header")
        return []
    
    # Parse tar headers
    entries = []
    offset = 0
    
    while offset + 512 <= len(decompressed):
        entry, next_offset = parse_tar_header(decompressed, offset)
        if entry is None:
            break
        entries.append(entry)
        
        if next_offset <= offset or next_offset > len(decompressed):
            # Next header would be outside our buffer
            break
        offset = next_offset
    
    return entries


def test_varying_sizes():
    """Test with different initial byte sizes to find minimum needed."""
    sizes = [8192, 16384, 32768, 65536, 131072, 262144]
    
    for size in sizes:
        print(f"\n{'='*60}")
        print(f"Testing with {size:,} bytes")
        print(f"{'='*60}")
        
        entries = peek_layer(TEST_URL, initial_bytes=size)
        
        print(f"\nFound {len(entries)} entries:")
        for i, e in enumerate(entries):
            type_str = "[DIR] " if e.is_dir else "[FILE]"
            print(f"  {type_str} {e.name} ({e.size:,} bytes)")


if __name__ == "__main__":
    test_varying_sizes()
