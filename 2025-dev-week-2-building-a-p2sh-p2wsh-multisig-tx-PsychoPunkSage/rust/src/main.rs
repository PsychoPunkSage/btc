use bitcoin::hashes::{hash160, sha256, Hash};
use bs58;
use secp256k1::{Message, Secp256k1, SecretKey};
use std::fs::File;
use std::io::Write;

fn debug_print(msg: &str, data: &str) {
    println!("DEBUG - {}: {}", msg, data);
}

fn double_sha256(data: &[u8]) -> [u8; 32] {
    let sha256_1 = sha256::Hash::hash(data);
    let sha256_2 = sha256::Hash::hash(&sha256_1[..]);
    let mut result = [0u8; 32];
    result.copy_from_slice(&sha256_2[..]);
    result
}

fn decode_address(address: &str) -> Vec<u8> {
    // Decode a base58 address and return the script hash
    let decoded = bs58::decode(address).into_vec().unwrap();
    decoded[1..decoded.len() - 4].to_vec()
}

fn main() {
    println!("\n=== Starting Transaction Creation ===\n");

    // Keys and Script setup
    let priv_key1 = "39dc0a9f0b185a2ee56349691f34716e6e0cda06a7f9707742ac113c4e2317bf";
    let priv_key2 = "5077ccd9c558b7d04a81920d38aa11b4a9f9de3b23fab45c3ef28039920fdd6d";

    // Create redeem script (2-of-2 multisig)
    let redeem_script = hex::decode("5221032ff8c5df0bc00fe1ac2319c3b8070d6d1e04cfbf4fedda499ae7b775185ad53b21039bbc8d24f89e5bc44c5b0d1980d6658316a6b2440023117c3c03a4975b04dd5652ae").unwrap();
    debug_print("Redeem Script", &hex::encode(&redeem_script));

    // Get witness program (SHA256 of redeem script)
    let witness_program = sha256::Hash::hash(&redeem_script).to_byte_array();
    debug_print("Witness Program", &hex::encode(&witness_program));

    // Create P2WSH script: 0x00 0x20 <32-byte SHA256 of redeem script>
    let mut p2wsh_script = Vec::new();
    p2wsh_script.push(0x00);
    p2wsh_script.push(0x20);
    p2wsh_script.extend_from_slice(&witness_program);
    debug_print("P2WSH Script", &hex::encode(&p2wsh_script));

    // Create P2SH script hash (HASH160 of P2WSH script)
    let script_hash = hash160::Hash::hash(&p2wsh_script).to_byte_array();
    debug_print("P2SH Script Hash", &hex::encode(&script_hash));

    // Transaction structure
    let version = 2u32.to_le_bytes(); // Version 2
    let marker = [0x00]; // Marker byte for segwit
    let flag = [0x01]; // Flag byte for segwit

    // Single input
    let input_count = [0x01];
    let prev_tx = [0u8; 32]; // null hash
    let prev_index = 0u32.to_le_bytes(); // index 0

    // For P2SH-P2WSH, script_sig is just a push of the P2WSH script
    let mut script_sig = Vec::new();
    script_sig.push(p2wsh_script.len() as u8);
    script_sig.extend_from_slice(&p2wsh_script);
    debug_print("Script Sig", &hex::encode(&script_sig));

    let sequence = hex::decode("ffffffff").unwrap();

    // Construct input
    let mut tx_in = Vec::new();
    tx_in.extend_from_slice(&prev_tx);
    tx_in.extend_from_slice(&prev_index);
    tx_in.push(script_sig.len() as u8);
    tx_in.extend_from_slice(&script_sig);
    tx_in.extend_from_slice(&sequence);

    // Output
    let output_count = [0x01];
    let value = 100000u64.to_le_bytes(); // 0.001 BTC in satoshis

    // Create output script for the required address: 325UUecEQuyrTd28Xs2hvAxdAjHM7XzqVF
    let output_address = "325UUecEQuyrTd28Xs2hvAxdAjHM7XzqVF";
    let output_script_hash = decode_address(output_address);
    debug_print("Output Script Hash", &hex::encode(&output_script_hash));

    // Create P2SH output script: OP_HASH160 <script_hash> OP_EQUAL
    let mut output_script = Vec::new();
    output_script.push(0xa9);
    output_script.push(output_script_hash.len() as u8);
    output_script.extend_from_slice(&output_script_hash);
    output_script.push(0x87);
    debug_print("Output Script", &hex::encode(&output_script));

    let mut tx_out = Vec::new();
    tx_out.extend_from_slice(&value);
    tx_out.push(output_script.len() as u8);
    tx_out.extend_from_slice(&output_script);

    // Locktime
    let locktime = 0u32.to_le_bytes(); // 0, little-endian

    // BIP143 sighash calculation
    // 1. Hash prevouts (double SHA256 of all input outpoints)
    let mut prevouts = Vec::new();
    prevouts.extend_from_slice(&prev_tx);
    prevouts.extend_from_slice(&prev_index);
    let hash_prevouts = double_sha256(&prevouts);
    debug_print("Hash Prevouts", &hex::encode(&hash_prevouts));

    // 2. Hash sequence (double SHA256 of all input sequences)
    let hash_sequence = double_sha256(&sequence);
    debug_print("Hash Sequence", &hex::encode(&hash_sequence));

    // 3. Hash outputs (double SHA256 of all outputs)
    let hash_outputs = double_sha256(&tx_out);
    debug_print("Hash Outputs", &hex::encode(&hash_outputs));

    // 4. Build sighash preimage according to BIP143
    // Script code is the redeem script with a length prefix
    let mut script_code = Vec::new();
    script_code.push(redeem_script.len() as u8);
    script_code.extend_from_slice(&redeem_script);

    // Input amount (0 for coinbase-like input)
    let amount = 0u64.to_le_bytes();

    let sighash_type = 1u32.to_le_bytes(); // SIGHASH_ALL (1)

    let mut sighash_preimage = Vec::new();
    sighash_preimage.extend_from_slice(&version);
    sighash_preimage.extend_from_slice(&hash_prevouts);
    sighash_preimage.extend_from_slice(&hash_sequence);
    sighash_preimage.extend_from_slice(&prev_tx);
    sighash_preimage.extend_from_slice(&prev_index);
    sighash_preimage.extend_from_slice(&script_code);
    sighash_preimage.extend_from_slice(&amount);
    sighash_preimage.extend_from_slice(&sequence);
    sighash_preimage.extend_from_slice(&hash_outputs);
    sighash_preimage.extend_from_slice(&locktime);
    sighash_preimage.extend_from_slice(&sighash_type);

    // Calculate the hash that needs to be signed
    let sighash = double_sha256(&sighash_preimage);
    debug_print("Sighash", &hex::encode(&sighash));

    // Generate signatures with both private keys
    let secp = Secp256k1::new();
    let secret_key1 = SecretKey::from_slice(&hex::decode(priv_key1).unwrap()).unwrap();
    let secret_key2 = SecretKey::from_slice(&hex::decode(priv_key2).unwrap()).unwrap();

    let message = Message::from_slice(&sighash).unwrap();
    let sig1_obj = secp.sign_ecdsa(&message, &secret_key1);
    let sig2_obj = secp.sign_ecdsa(&message, &secret_key2);

    let mut sig1 = sig1_obj.serialize_der().to_vec();
    sig1.push(0x01); // SIGHASH_ALL
    let mut sig2 = sig2_obj.serialize_der().to_vec();
    sig2.push(0x01); // SIGHASH_ALL

    debug_print("Signature 1", &hex::encode(&sig1));
    debug_print("Signature 2", &hex::encode(&sig2));

    // Create witness stack
    // Important: Bitcoin serializes the witness differently than other tx parts!
    // First byte (0x04) is the number of witness items, not length
    // Each item is prefixed with a compact size (varint)
    let mut witness = Vec::new();

    // Number of witness stack items (4)
    witness.push(0x04);

    // 1. Empty item (dummy for CHECKMULTISIG bug) - using empty array
    witness.push(0x00); // Length = 0

    // 2. Second signature (using sig2 as per the original ordering)
    witness.push(sig2.len() as u8); // Length of sig2
    witness.extend_from_slice(&sig2);

    // 3. First signature
    witness.push(sig1.len() as u8); // Length of sig1
    witness.extend_from_slice(&sig1);

    // 4. Redeem script (witness script) - full script, not a hash
    witness.push(redeem_script.len() as u8); // Length of redeem script
    witness.extend_from_slice(&redeem_script);

    debug_print("Witness", &hex::encode(&witness));

    // Construct final transaction
    let mut final_tx = Vec::new();
    final_tx.extend_from_slice(&version);
    final_tx.extend_from_slice(&marker);
    final_tx.extend_from_slice(&flag);
    final_tx.extend_from_slice(&input_count);
    final_tx.extend_from_slice(&tx_in);
    final_tx.extend_from_slice(&output_count);
    final_tx.extend_from_slice(&tx_out);
    final_tx.extend_from_slice(&witness);
    final_tx.extend_from_slice(&locktime);

    debug_print("Final Transaction", &hex::encode(&final_tx));

    // Write to file
    let mut file = File::create("out.txt").expect("Failed to create file");
    file.write_all(hex::encode(&final_tx).as_bytes())
        .expect("Failed to write to file");

    println!("\n=== Transaction Creation Complete ===\n");
    println!("Transaction hex has been written to out.txt");
}
