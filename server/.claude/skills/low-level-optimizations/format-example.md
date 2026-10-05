# Reference implementation: score file + RLE

The format from SKILL.md §2, with run-length encoding from §4 and the three tests from §6. Tested with `cargo test` (Rust 2024 edition, no dependencies): 5 passed.

Adapt it, don't copy blindly: rename `Score`, change the record fields, keep the shape (config at top → write → read with guards → tests).

## Contents
* `FORMAT` config: magic, version, header size
* `ScoreFile::write` / `ScoreFile::read`: bounds-checked `take` helper, record count capped by remaining bytes
* `RunLength::encode` / `RunLength::decode` (output capped at `maximum_length`)
* Tests: round trip, golden header bytes, rejection incl. forged count, RLE

```rust
const FORMAT: FormatConfig = FormatConfig {
    magic: *b"SCOR",   // 53 43 4F 52: identifies the file before anything else is read
    version: 1,
    header_size: 10,   // bytes: magic 4 + version 2 + record_count 4
    minimum_record_size: 10, // bytes: player_id 4 + name_length 2 + empty name 0 + points 4
};

struct FormatConfig {
    magic: [u8; 4],
    version: u16,
    header_size: usize,
    minimum_record_size: usize,
}

#[derive(Debug, PartialEq, Clone)]
pub struct Score {
    pub player_id: u32,
    pub name: String,
    pub points: i32,
}

pub struct ScoreFile;

impl ScoreFile {
    pub fn write(scores: impl Into<Vec<Score>>) -> Vec<u8> {
        let scores: Vec<Score> = scores.into();
        let mut bytes: Vec<u8> = Vec::with_capacity(FORMAT.header_size + scores.len() * 16);

        bytes.extend_from_slice(&FORMAT.magic);
        bytes.extend_from_slice(&FORMAT.version.to_le_bytes());
        bytes.extend_from_slice(&(scores.len() as u32).to_le_bytes());

        for score in &scores {
            let name_bytes = score.name.as_bytes(); // UTF-8: length in bytes, not characters
            bytes.extend_from_slice(&score.player_id.to_le_bytes());
            bytes.extend_from_slice(&(name_bytes.len() as u16).to_le_bytes());
            bytes.extend_from_slice(name_bytes);
            bytes.extend_from_slice(&score.points.to_le_bytes());
        }

        return bytes;
    }

    pub fn read(bytes: impl Into<Vec<u8>>) -> Option<Vec<Score>> {
        let bytes: Vec<u8> = bytes.into();
        if bytes.len() < FORMAT.header_size { return None; }
        if bytes[0..4] != FORMAT.magic { return None; }

        let version = u16::from_le_bytes([bytes[4], bytes[5]]);
        if version != FORMAT.version { return None; }

        let record_count = u32::from_le_bytes([bytes[6], bytes[7], bytes[8], bytes[9]]) as usize;
        // A forged count must not allocate more records than the remaining bytes can hold.
        let maximum_record_count = (bytes.len() - FORMAT.header_size) / FORMAT.minimum_record_size;
        if record_count > maximum_record_count { return None; }
        let mut scores: Vec<Score> = Vec::with_capacity(record_count);
        let mut offset = FORMAT.header_size;

        for _ in 0..record_count {
            let player_id = u32::from_le_bytes(take(&bytes, offset, 4)?.try_into().ok()?);
            offset += 4;
            let name_length = u16::from_le_bytes(take(&bytes, offset, 2)?.try_into().ok()?) as usize;
            offset += 2;
            let name = String::from_utf8(take(&bytes, offset, name_length)?.to_vec()).ok()?;
            offset += name_length;
            let points = i32::from_le_bytes(take(&bytes, offset, 4)?.try_into().ok()?);
            offset += 4;

            scores.push(Score { player_id, name, points });
        }

        if offset != bytes.len() { return None; } // trailing bytes = corrupt file
        return Some(scores);
    }
}

fn take(bytes: &[u8], offset: usize, length: usize) -> Option<&[u8]> {
    return bytes.get(offset..offset.checked_add(length)?);
}

pub struct RunLength;

impl RunLength {
    // Output pairs: (count, byte). Count is 1..=255, so a run longer than 255 splits.
    pub fn encode(bytes: impl Into<Vec<u8>>) -> Vec<u8> {
        let bytes: Vec<u8> = bytes.into();
        let mut encoded: Vec<u8> = Vec::new();
        let mut index = 0;

        while index < bytes.len() {
            let value = bytes[index];
            let mut count: u8 = 1;
            while index + (count as usize) < bytes.len() && bytes[index + count as usize] == value && count < u8::MAX {
                count += 1;
            }
            encoded.push(count);
            encoded.push(value);
            index += count as usize;
        }

        return encoded;
    }

    // maximum_length comes from the header: a forged run list must not expand without limit.
    pub fn decode(encoded: impl Into<Vec<u8>>, maximum_length: usize) -> Option<Vec<u8>> {
        let encoded: Vec<u8> = encoded.into();
        if encoded.len() % 2 != 0 { return None; }

        let mut bytes: Vec<u8> = Vec::new();
        for pair in encoded.chunks_exact(2) {
            if pair[0] == 0 { return None; }
            if bytes.len() + pair[0] as usize > maximum_length { return None; }
            for _ in 0..pair[0] {
                bytes.push(pair[1]);
            }
        }

        return Some(bytes);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Vec<Score> {
        return vec![
            Score { player_id: 1, name: String::from("Ada"), points: 900 },
            Score { player_id: 2, name: String::from("Søren"), points: -5 },
        ];
    }

    #[test]
    fn round_trip_returns_the_same_scores() {
        let bytes = ScoreFile::write(sample());
        assert_eq!(ScoreFile::read(bytes), Some(sample()));
    }

    #[test]
    fn header_bytes_are_the_documented_layout() {
        let bytes = ScoreFile::write(sample());
        assert_eq!(bytes[0..10], [0x53, 0x43, 0x4F, 0x52, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00]);
        // "Søren": ø is 2 bytes in UTF-8, so the name length is 6, not 5
        assert_eq!(bytes[10 + 4 + 2 + 3 + 4 + 4..][0..2], [0x06, 0x00]);
    }

    #[test]
    fn read_rejects_wrong_magic_truncation_trailing_bytes_and_forged_count() {
        let bytes = ScoreFile::write(sample());
        let mut wrong_magic = bytes.clone();
        wrong_magic[0] = b'X';
        assert_eq!(ScoreFile::read(wrong_magic), None);
        assert_eq!(ScoreFile::read(bytes[..bytes.len() - 1].to_vec()), None);
        let mut trailing = bytes.clone();
        trailing.push(0);
        assert_eq!(ScoreFile::read(trailing), None);
        let mut forged_count = bytes.clone();
        forged_count[6..10].copy_from_slice(&u32::MAX.to_le_bytes());
        assert_eq!(ScoreFile::read(forged_count), None);
    }

    #[test]
    fn run_length_round_trips_and_splits_long_runs() {
        let input: Vec<u8> = [vec![0u8; 300], b"AAB".to_vec()].concat();
        let encoded = RunLength::encode(input.clone());
        assert_eq!(encoded, vec![255, 0, 45, 0, 2, b'A', 1, b'B']);
        assert_eq!(RunLength::decode(encoded.clone(), input.len()), Some(input.clone()));
        assert_eq!(RunLength::decode(encoded, input.len() - 1), None);
    }

    #[test]
    fn run_length_doubles_data_without_runs() {
        assert_eq!(RunLength::encode(b"ABCD".to_vec()).len(), 8);
    }
}
```
