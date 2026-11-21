# Tutorial: Hashing and Checksums in Lateralus

This guide covers the `stdlib.hash` module, which provides robust hashing and checksum algorithms for data integrity and hash table implementations.

## Hash Functions
- **FNV-1a (32/64-bit):** Excellent distribution, ideal for hash tables.
- **DJB2:** A classic, simple, and fast string hash.
- **SDBM:** Used in the SDBM database engine.

## Checksums
- **checksum8:** Simple additive checksum.
- **Fletcher-16:** Better error detection than simple checksums.
- **Adler-32:** Used in zlib, faster than CRC32.

## Usage Example
See `examples/hash_tutorial.ltl` for a complete implementation demonstrating these functions with known test vectors.