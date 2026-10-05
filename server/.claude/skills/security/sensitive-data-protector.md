# Sensitive Data Protector

The single place where sensitive values are hashed, lookup-hashed, encrypted and decrypted. Build it once in `src/_architecture/encryption/`. Every controller and adapter uses it, and nothing else touches the keys.

## Contents
1. Normalize and mask
2. Code
3. Keys and rotation
4. Storage and use

## 1. Normalize and mask

Normalize before hashing. Otherwise `010190-1234` and `0101901234` produce two lookup hashes for the same person. The value type's `TryCreate` normalizes it and computes the mask (rule 1, parse don't validate).

| Value | Normalized | Masked |
|---|---|---|
| CPR | 10 digits: `0101901234` | `010190-****` |
| Norwegian national ID (fødselsnummer) | 11 digits: `01019012345` | `010190*****` |
| IBAN | uppercase, no spaces: `DK5000400440116243` | `DK** **** **** 6243` |
| Email | trimmed, lowercase: `jane@example.com` | `j***@example.com` |
| Phone | E.164: `+4512345678` | `+45 ****5678` |

* CVR numbers are public in the Danish business register, so they aren't sensitive.
   * A field that can hold a CPR *or* a CVR (a customer's `IdentificationNumber`) is treated as a CPR.

## 2. Code

```csharp
using cryptography = System.Security.Cryptography;
using text = System.Text;

namespace Architecture.Encryption;

internal static class SensitiveDataConfig
{
    public const int EncryptionKeySizeBytes = 32;   // AES-256
    public const int NonceSizeBytes = 12;           // AesGcm.NonceByteSizes.MaxSize
    public const int TagSizeBytes = 16;             // AesGcm.TagByteSizes.MaxSize
    public const int SaltSizeBytes = 16;            // random per chosen secret
    public const int SlowHashIterations = 210_000;  // OWASP minimum for PBKDF2-HMAC-SHA512
    public const int SlowHashSizeBytes = 32;
    public const string VersionSeparator = ":";
    public const char SlowHashSeparator = '.';
    public const string RedactedText = "[protected]";
}

public sealed class ProtectedValue
{
    public string Ciphertext { get; }  // "v1:" + base64(nonce | ciphertext | tag)
    public string LookupHash { get; }  // base64(HMAC-SHA256(lookup key, normalized value))
    public string Masked { get; }      // safe to show and to log

    public ProtectedValue(string ciphertext, string lookupHash, string masked)
    {
        Ciphertext = ciphertext;
        LookupHash = lookupHash;
        Masked = masked;
    }

    public override string ToString()
    {
        return SensitiveDataConfig.RedactedText; // string interpolation into a log can't leak
    }
}

public sealed class SensitiveDataProtector
{
    private readonly string _currentKeyVersion;
    private readonly System.Collections.Generic.Dictionary<string, byte[]> _encryptionKeysByVersion;
    private readonly byte[] _lookupKey;

    public SensitiveDataProtector(
        string currentKeyVersion,
        System.Collections.Generic.Dictionary<string, byte[]> encryptionKeysByVersion,
        byte[] lookupKey)
    {
        _currentKeyVersion = currentKeyVersion;
        _encryptionKeysByVersion = encryptionKeysByVersion;
        _lookupKey = lookupKey;
    }

    public ProtectedValue Protect(string normalizedValue, string masked)
    {
        return new ProtectedValue(Encrypt(normalizedValue), ComputeLookupHash(normalizedValue), masked);
    }

    public string Encrypt(string plaintext)
    {
        byte[] key = _encryptionKeysByVersion[_currentKeyVersion];
        byte[] plaintextBytes = text.Encoding.UTF8.GetBytes(plaintext);
        int ciphertextLength = plaintextBytes.Length;
        byte[] payload = new byte[SensitiveDataConfig.NonceSizeBytes + ciphertextLength + SensitiveDataConfig.TagSizeBytes];
        System.Span<byte> nonce = new System.Span<byte>(payload, 0, SensitiveDataConfig.NonceSizeBytes);
        System.Span<byte> ciphertext = new System.Span<byte>(payload, SensitiveDataConfig.NonceSizeBytes, ciphertextLength);
        System.Span<byte> tag = new System.Span<byte>(payload, SensitiveDataConfig.NonceSizeBytes + ciphertextLength, SensitiveDataConfig.TagSizeBytes);
        cryptography.RandomNumberGenerator.Fill(nonce); // fresh per value: a nonce reused with the same key breaks GCM

        using (cryptography.AesGcm aesGcm = new cryptography.AesGcm(key, SensitiveDataConfig.TagSizeBytes))
        {
            aesGcm.Encrypt(nonce, plaintextBytes, ciphertext, tag);
        }

        return _currentKeyVersion + SensitiveDataConfig.VersionSeparator + System.Convert.ToBase64String(payload);
    }

    // null = not our format, unknown key version, or tampered. Fail closed: never hand back the input as plaintext.
    public string? Decrypt(string protectedText)
    {
        int separatorIndex = protectedText.IndexOf(SensitiveDataConfig.VersionSeparator);
        if (separatorIndex <= 0)
        {
            return null;
        }

        string keyVersion = protectedText.Substring(0, separatorIndex);
        if (!_encryptionKeysByVersion.TryGetValue(keyVersion, out byte[]? key))
        {
            return null;
        }

        string base64Payload = protectedText.Substring(separatorIndex + 1);
        byte[] payloadBuffer = new byte[base64Payload.Length];
        if (!System.Convert.TryFromBase64String(base64Payload, payloadBuffer, out int payloadLength))
        {
            return null;
        }

        int ciphertextLength = payloadLength - SensitiveDataConfig.NonceSizeBytes - SensitiveDataConfig.TagSizeBytes;
        if (ciphertextLength < 0)
        {
            return null;
        }

        System.ReadOnlySpan<byte> nonce = new System.ReadOnlySpan<byte>(payloadBuffer, 0, SensitiveDataConfig.NonceSizeBytes);
        System.ReadOnlySpan<byte> ciphertext = new System.ReadOnlySpan<byte>(payloadBuffer, SensitiveDataConfig.NonceSizeBytes, ciphertextLength);
        System.ReadOnlySpan<byte> tag = new System.ReadOnlySpan<byte>(payloadBuffer, SensitiveDataConfig.NonceSizeBytes + ciphertextLength, SensitiveDataConfig.TagSizeBytes);
        byte[] plaintextBytes = new byte[ciphertextLength];

        using (cryptography.AesGcm aesGcm = new cryptography.AesGcm(key, SensitiveDataConfig.TagSizeBytes))
        {
            try
            {
                aesGcm.Decrypt(nonce, ciphertext, tag, plaintextBytes);
            }
            catch (cryptography.AuthenticationTagMismatchException)
            {
                return null;
            }
        }

        return text.Encoding.UTF8.GetString(plaintextBytes);
    }

    // Blind index: equality lookup and unique index without storing the value.
    public string ComputeLookupHash(string normalizedValue)
    {
        byte[] hash = cryptography.HMACSHA256.HashData(_lookupKey, text.Encoding.UTF8.GetBytes(normalizedValue));
        return System.Convert.ToBase64String(hash);
    }

    // For random tokens we issue (≥ 128 bits): store and look up only this hash.
    public static string HashToken(string token)
    {
        byte[] hash = cryptography.SHA256.HashData(text.Encoding.UTF8.GetBytes(token));
        return System.Convert.ToBase64String(hash);
    }

    // For secrets a person chooses (PINs): "iterations.salt.hash", so the iteration count can be raised later.
    public static string HashChosenSecret(string secret)
    {
        byte[] salt = cryptography.RandomNumberGenerator.GetBytes(SensitiveDataConfig.SaltSizeBytes);
        byte[] hash = cryptography.Rfc2898DeriveBytes.Pbkdf2(
            secret,
            salt,
            SensitiveDataConfig.SlowHashIterations,
            cryptography.HashAlgorithmName.SHA512,
            SensitiveDataConfig.SlowHashSizeBytes);

        return SensitiveDataConfig.SlowHashIterations.ToString()
            + SensitiveDataConfig.SlowHashSeparator + System.Convert.ToBase64String(salt)
            + SensitiveDataConfig.SlowHashSeparator + System.Convert.ToBase64String(hash);
    }

    public static bool VerifyChosenSecret(string secret, string storedHash)
    {
        string[] parts = storedHash.Split(SensitiveDataConfig.SlowHashSeparator);
        if (parts.Length != 3)
        {
            return false;
        }

        if (!int.TryParse(parts[0], out int iterations))
        {
            return false;
        }

        byte[] salt = System.Convert.FromBase64String(parts[1]);
        byte[] expectedHash = System.Convert.FromBase64String(parts[2]);
        byte[] actualHash = cryptography.Rfc2898DeriveBytes.Pbkdf2(
            secret,
            salt,
            iterations,
            cryptography.HashAlgorithmName.SHA512,
            expectedHash.Length);

        return cryptography.CryptographicOperations.FixedTimeEquals(actualHash, expectedHash);
    }
}
```

* Tokens we issue: generate them with `cryptography.RandomNumberGenerator.GetBytes(32)` and give the raw token to the client once. Store only `HashToken(token)`.
* No interface and no mock. Tests construct the real protector with random test keys (`tests-as-documentation`).

## 3. Keys and rotation

* Two kinds of key, each 32 random bytes stored as base64 in the secret store:

| Secret name | Used for | Rotation |
|---|---|---|
| `SensitiveDataEncryptionKeyV1`, `V2`, … | AES-GCM | Add `V2` and make it current. `V1` stays so old rows still decrypt. A background job re-encrypts old rows; remove `V1` once none are left |
| `SensitiveDataLookupKey` | HMAC lookup hash | Expensive: every lookup hash has to be recomputed from decrypted values. Rotate only if the key is compromised |

* Generate a key (PowerShell):

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

* The protector takes its keys through its constructor, so it doesn't depend on any feature. `src/program.cs` registers it as a singleton, reading the keys from the secret store:
   * a missing key throws, and there is no default key
   * `Program` resolves the protector once at startup, so a missing key stops the deploy instead of the first request
* Dev keys are random per developer and live in user secrets. A tracked file (anything under `src/_config/`) is not a secret store: anything committed is public.

## 4. Storage and use

One sensitive value, three columns on the feature entity:

```csharp
builder.Property(person => person.NationalIdentificationNumberCiphertext).HasMaxLength(100);
builder.Property(person => person.NationalIdentificationNumberLookupHash).HasMaxLength(44).IsFixedLength(); // base64 of 32 bytes
builder.HasIndex(person => person.NationalIdentificationNumberLookupHash).IsUnique();
builder.Property(person => person.NationalIdentificationNumberMasked).HasMaxLength(11);
```

* Ciphertext length = version prefix + base64 of (28 + plaintext bytes). A 10-digit CPR → `v1:` + 52 characters.

Lookup, at the boundary:

```csharp
string lookupHash = _sensitiveDataProtector.ComputeLookupHash(cpr.Normalized);
bool isRegistered = await _dbContext.People.AnyAsync(person => person.NationalIdentificationNumberLookupHash == lookupHash, cancellationToken);
```

Decryption, only in the outbound adapter (`Integration/`):

```csharp
// the only place the CPR is plaintext again, right before the HTTP call
string? cpr = _sensitiveDataProtector.Decrypt(person.NationalIdentificationNumberCiphertext);
if (cpr == null)
{
    return null; // fail closed: never send a ciphertext or an empty value onward
}
```
