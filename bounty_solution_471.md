2. Code Patch / Fix
Create a new file `docs/tutorials/stdlib_protobuf.md` (or `examples/protobuf/sensor_reading.lus` if the repo prefers code examples) containing the tutorial. Below is the canonical Lateralus code for a two-field sensor reading that is byte-compatible with standard protobuf.

**File: `examples/protobuf/sensor_reading.lus`**
```lateralus
// Lateralus 3.2.0
// Standard Library: protobuf
// Tutorial: Encoding and Decoding a Two-Field Sensor Reading

import stdlib.protobuf

// Define the message structure
// Field 1: sensor_id (uint32)
// Field 2: temperature (float)
// This matches the standard protobuf wire format for:
// message SensorReading {
//   uint32 sensor_id = 1;
//   float temperature = 2;
// }

def encode_sensor_reading(sensor_id: uint32, temperature: float) -> bytes {
    let buf = protobuf::Buffer::new()
    
    // Encode field 1: sensor_id (tag = (1 << 3) | 0 = 0x08)
    buf.write_varint(0x08)
    buf.write_varint(sensor_id)
    
    // Encode field 2: temperature (tag = (2 << 3) | 5 = 0x15)
    // Wire type 5 = 32-bit fixed length (float)
    buf.write_varint(0x15)
    buf.write_float32(temperature)
    
    return buf.to_bytes()
}

def decode_sensor_reading(data: bytes) -> (uint32, float) {
    let reader = protobuf::Reader::new(data)
    
    // Read field 1
    let tag1 = reader.read_varint()
    if tag1 != 0x08 {
        panic("Invalid tag for sensor_id")
    }
    let sensor_id = reader.read_varint()
    
    // Read field 2
    let tag2 = reader.read_varint()
    if tag2 != 0x15 {
        panic("Invalid tag for temperature")
    }
    let temperature = reader.read_float32()
    
    return (sensor_id, temperature)
}

// Test cases
def main() {
    // Test 1
    let encoded1 = encode_sensor_reading(1, 20.5)
    let (id1, temp1) = decode_sensor_reading(encoded1)