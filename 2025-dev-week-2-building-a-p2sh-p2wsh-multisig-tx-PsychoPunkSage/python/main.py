import hashlib
import struct
import ecdsa
import base58
import binascii
import random

def debug_print(msg, data):
    print(f"DEBUG - {msg}: {data}")

def double_sha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def hash160(data):
    sha256_hash = hashlib.sha256(data).digest()
    return hashlib.new('ripemd160', sha256_hash).digest()

# Custom signature encoder to match Bitcoin's expected format
def custom_sigencode_der(r, s, order):
    # Ensure r and s are within acceptable range
    r = r % order
    s = s % order
    
    # BIP 62: low S values
    if s > order // 2:
        s = order - s
    
    # Convert to bytes
    r_bytes = r.to_bytes((r.bit_length() + 7) // 8, byteorder='big')
    s_bytes = s.to_bytes((s.bit_length() + 7) // 8, byteorder='big')
    
    # Remove any unnecessary leading zero bytes
    while len(r_bytes) > 1 and r_bytes[0] == 0 and r_bytes[1] < 0x80:
        r_bytes = r_bytes[1:]
    while len(s_bytes) > 1 and s_bytes[0] == 0 and s_bytes[1] < 0x80:
        s_bytes = s_bytes[1:]
    
    # Add leading zero if high bit is set
    if r_bytes[0] & 0x80:
        r_bytes = b'\x00' + r_bytes
    if s_bytes[0] & 0x80:
        s_bytes = b'\x00' + s_bytes
    
    # Build DER structure
    r_der = b'\x02' + bytes([len(r_bytes)]) + r_bytes
    s_der = b'\x02' + bytes([len(s_bytes)]) + s_bytes
    
    # Create the complete DER signature
    der_sig = b'\x30' + bytes([len(r_der) + len(s_der)]) + r_der + s_der
    
    return der_sig

# Function to extract r and s from a DER signature
def extract_rs_from_der(der_sig):
    # Skip the first two bytes (0x30 and length)
    index = 2
    
    # Skip the next two bytes (0x02 and R length)
    r_len = der_sig[index + 1]
    index += 2
    
    # Extract R
    r = int.from_bytes(der_sig[index:index+r_len], byteorder='big')
    index += r_len
    
    # Skip the next two bytes (0x02 and S length)
    s_len = der_sig[index + 1]
    index += 2
    
    # Extract S
    s = int.from_bytes(der_sig[index:index+s_len], byteorder='big')
    
    return r, s

def main():
    print("\n=== Starting Transaction Creation ===\n")
    
    # Set deterministic random seed for reproducible results
    random.seed(1234)
    
    # Keys and Script setup
    priv_key1_hex = "39dc0a9f0b185a2ee56349691f34716e6e0cda06a7f9707742ac113c4e2317bf"
    priv_key2_hex = "5077ccd9c558b7d04a81920d38aa11b4a9f9de3b23fab45c3ef28039920fdd6d"
    
    priv_key1 = bytes.fromhex(priv_key1_hex)
    priv_key2 = bytes.fromhex(priv_key2_hex)
    
    # This is our actual multisig script (referred to as redeem script in the README)
    multisig_script = bytes.fromhex("5221032ff8c5df0bc00fe1ac2319c3b8070d6d1e04cfbf4fedda499ae7b775185ad53b21039bbc8d24f89e5bc44c5b0d1980d6658316a6b2440023117c3c03a4975b04dd5652ae")
    debug_print("Multisig Script", multisig_script.hex())
    
    # Get the SHA256 hash of the multisig script
    multisig_hash = hashlib.sha256(multisig_script).digest()
    debug_print("SHA256 of Multisig Script", multisig_hash.hex())
    
    # Create the witness program: 0x00 0x20 <32-byte SHA256 of multisig script>
    witness_program = bytes([0x00, 0x20]) + multisig_hash
    debug_print("Witness Program (P2WSH)", witness_program.hex())
    
    # In P2SH-P2WSH, the redeem script is the witness program
    redeem_script = witness_program
    debug_print("Redeem Script", redeem_script.hex())
    
    # Create P2SH script hash (HASH160 of redeem script)
    script_hash = hash160(redeem_script)
    debug_print("P2SH Script Hash", script_hash.hex())
    
    # Create P2SH address
    version_byte = bytes([0x05])  # 0x05 for P2SH mainnet
    data = version_byte + script_hash
    checksum = double_sha256(data)[:4]
    address = base58.b58encode(data + checksum).decode('utf-8')
    debug_print("P2SH Address", address)
    
    # Verify address matches the expected one from the spec
    expected_address = "325UUecEQuyrTd28Xs2hvAxdAjHM7XzqVF"
    if address != expected_address:
        print(f"WARNING: Calculated address {address} doesn't match expected {expected_address}")
    
    # Transaction structure
    version = struct.pack("<I", 1)  # Version 1
    marker = bytes([0x00])  # Marker byte for segwit
    flag = bytes([0x01])  # Flag byte for segwit
    
    # Single input
    input_count = bytes([0x01])
    prev_tx = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000000")
    prev_index = struct.pack("<I", 0)  # index 0
    
    # For P2SH-P2WSH, script_sig is just a push of the redeem script (witness program)
    script_sig = bytes([len(redeem_script)]) + redeem_script
    debug_print("Script Sig", script_sig.hex())
    
    sequence = bytes.fromhex("ffffffff")
    
    # Construct input
    tx_in = prev_tx + prev_index + bytes([len(script_sig)]) + script_sig + sequence
    
    # Output
    output_count = bytes([0x01])
    value = struct.pack("<Q", 100000)  # 0.001 BTC in satoshis
    
    # Use P2SH script for output
    p2sh_output_script = bytes([0xa9, 0x14]) + script_hash + bytes([0x87])
    debug_print("Output Script", p2sh_output_script.hex())
    
    tx_out = value + bytes([len(p2sh_output_script)]) + p2sh_output_script
    
    # Locktime
    locktime = struct.pack("<I", 0)  # 0, little-endian
    
    # BIP143 sighash calculation
    # 1. Hash prevouts (double SHA256 of all input outpoints)
    hash_prevouts = double_sha256(prev_tx + prev_index)
    debug_print("Hash Prevouts", hash_prevouts.hex())
    
    # 2. Hash sequence (double SHA256 of all input sequences)
    hash_sequence = double_sha256(sequence)
    debug_print("Hash Sequence", hash_sequence.hex())
    
    # 3. Hash outputs (double SHA256 of all outputs)
    hash_outputs = double_sha256(tx_out)
    debug_print("Hash Outputs", hash_outputs.hex())
    
    # 4. Build sighash preimage according to BIP143
    # Script code is the multisig script with a length prefix for P2WSH
    script_code = bytes([len(multisig_script)]) + multisig_script
    
    # Amount of the input being spent - for the first input (in this case, 0.001 BTC)
    amount = struct.pack("<Q", 100000)
    
    sighash_type = struct.pack("<I", 1)  # SIGHASH_ALL (1)
    
    sighash_preimage = (
        version +
        hash_prevouts +
        hash_sequence +
        prev_tx + prev_index +
        script_code +
        amount +
        sequence +
        hash_outputs +
        locktime +
        sighash_type
    )
    
    # Calculate the hash that needs to be signed
    sighash = double_sha256(sighash_preimage)
    debug_print("Sighash", sighash.hex())
    
    # Create signing keys
    signing_key1 = ecdsa.SigningKey.from_string(priv_key1, curve=ecdsa.SECP256k1)
    signing_key2 = ecdsa.SigningKey.from_string(priv_key2, curve=ecdsa.SECP256k1)
    
    # Get DER signatures using the library's built-in method
    der_sig1 = signing_key1.sign_digest_deterministic(sighash, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der)
    der_sig2 = signing_key2.sign_digest_deterministic(sighash, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der)
    
    # Extract r and s values
    r1, s1 = extract_rs_from_der(der_sig1)
    r2, s2 = extract_rs_from_der(der_sig2)
    
    # Encode with our custom encoder to ensure Bitcoin compatibility
    order = ecdsa.SECP256k1.generator.order()
    sig1_bitcoin = custom_sigencode_der(r1, s1, order) + b'\x01'  # Add SIGHASH_ALL byte
    sig2_bitcoin = custom_sigencode_der(r2, s2, order) + b'\x01'  # Add SIGHASH_ALL byte
    
    debug_print("Signature 1", sig1_bitcoin.hex())
    debug_print("Signature 2", sig2_bitcoin.hex())
    
    # IMPORTANT: Here we swap the signatures to match the expected order
    # Create witness stack for P2WSH
    # Order: [0 (due to off-by-one bug in OP_CHECKMULTISIG), sig1, sig2, multisig script]
    witness = bytes([0x04])  # 4 witness items
    witness += bytes([0x00])  # Empty signature (dummy) for CHECKMULTISIG bug
    witness += bytes([len(sig2_bitcoin)]) + sig2_bitcoin  # First signature (from key1)
    witness += bytes([len(sig1_bitcoin)]) + sig1_bitcoin  # Second signature (from key2)
    witness += bytes([len(multisig_script)]) + multisig_script  # The actual multisig script
    
    debug_print("Witness", witness.hex())
    
    # Construct final transaction
    final_tx = version + marker + flag + input_count + tx_in + output_count + tx_out + witness + locktime
    
    debug_print("Final Transaction", final_tx.hex())
    
    # Write to file
    with open("out.txt", "w") as f:
        f.write(final_tx.hex())
    
    print("\n=== Transaction Creation Complete ===\n")
    print("Transaction hex has been written to out.txt")
    print(f"P2SH Address: {address}")

if __name__ == "__main__":
    main()