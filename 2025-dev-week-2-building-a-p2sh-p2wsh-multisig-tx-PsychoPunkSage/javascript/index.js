// P2SH-P2WSH Multisig Transaction using bitcoinjs-lib
const bitcoin = require('bitcoinjs-lib');
const fs = require('fs');
const crypto = require('crypto');
const bs58 = require('bs58');
const { ECPairFactory } = require('ecpair');
const ecc = require('tiny-secp256k1');

// Initialize ECPair factory with the required elliptic curve implementation
const ECPair = ECPairFactory(ecc);

// Function to debug print values
function debugPrint(msg, data) {
    console.log(`DEBUG - ${msg}: ${data}`);
}

// Function to create double SHA256 hash
function doubleSha256(buffer) {
    return crypto.createHash('sha256').update(
        crypto.createHash('sha256').update(buffer).digest()
    ).digest();
}

// Function to decode a Bitcoin address
function decodeAddress(address) {
    const decoded = bs58.decode(address);
    // Remove version byte and checksum (4 bytes)
    return decoded.slice(1, decoded.length - 4);
}

// Main function to create the transaction
function createMultisigTransaction() {
    console.log("\n=== Starting Transaction Creation ===\n");

    // Keys and Script setup - using the same keys from the Rust code
    const privKey1 = "39dc0a9f0b185a2ee56349691f34716e6e0cda06a7f9707742ac113c4e2317bf";
    const privKey2 = "5077ccd9c558b7d04a81920d38aa11b4a9f9de3b23fab45c3ef28039920fdd6d";

    // Create redeem script (2-of-2 multisig) - using the exact same script from Rust code
    const redeemScript = Buffer.from("5221032ff8c5df0bc00fe1ac2319c3b8070d6d1e04cfbf4fedda499ae7b775185ad53b21039bbc8d24f89e5bc44c5b0d1980d6658316a6b2440023117c3c03a4975b04dd5652ae", "hex");
    debugPrint("Redeem Script", redeemScript.toString('hex'));

    // Get witness program (SHA256 of redeem script)
    const witnessProgram = crypto.createHash('sha256').update(redeemScript).digest();
    debugPrint("Witness Program", witnessProgram.toString('hex'));

    // Create P2WSH script: 0x00 0x20 <32-byte SHA256 of redeem script>
    const p2wshScript = Buffer.concat([
        Buffer.from([0x00, 0x20]), // OP_0 followed by push of 32 bytes
        witnessProgram
    ]);
    debugPrint("P2WSH Script", p2wshScript.toString('hex'));

    // Create P2SH script hash (HASH160 of P2WSH script)
    const scriptHash = crypto.createHash('ripemd160').update(
        crypto.createHash('sha256').update(p2wshScript).digest()
    ).digest();
    debugPrint("P2SH Script Hash", scriptHash.toString('hex'));

    // Create P2SH script: OP_HASH160 <script_hash> OP_EQUAL
    // Not directly used in this script, but shown for completeness
    const p2shScript = Buffer.concat([
        Buffer.from([0xa9]),  // OP_HASH160
        Buffer.from([0x14]),  // Push 20 bytes
        scriptHash,
        Buffer.from([0x87])   // OP_EQUAL
    ]);

    // Transaction structure - following the exact same format as the Rust code
    // Version 2
    const version = Buffer.from([0x02, 0x00, 0x00, 0x00]); // Version 2, little-endian

    // Segwit marker and flag
    const marker = Buffer.from([0x00]); // Marker byte for segwit
    const flag = Buffer.from([0x01]);   // Flag byte for segwit

    // Single input (null hash, index 0)
    const inputCount = Buffer.from([0x01]);
    const prevTx = Buffer.alloc(32, 0); // null hash, as in the Rust code
    const prevIndex = Buffer.from([0x00, 0x00, 0x00, 0x00]); // index 0, little-endian

    // Script sig for P2SH-P2WSH is just a push of the P2WSH script
    const scriptSig = Buffer.concat([
        Buffer.from([p2wshScript.length]), // Length of P2WSH script
        p2wshScript
    ]);
    debugPrint("Script Sig", scriptSig.toString('hex'));

    const sequence = Buffer.from([0xff, 0xff, 0xff, 0xff]); // Sequence = FFFFFFFF

    // Construct input
    const txIn = Buffer.concat([
        prevTx,
        prevIndex,
        Buffer.from([scriptSig.length]), // scriptSig length
        scriptSig,
        sequence
    ]);

    // Output
    const outputCount = Buffer.from([0x01]);
    const value = Buffer.from([0xa0, 0x86, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]); // 100000 satoshis in little-endian

    // Create output script for the required address: 325UUecEQuyrTd28Xs2hvAxdAjHM7XzqVF
    const outputAddress = "325UUecEQuyrTd28Xs2hvAxdAjHM7XzqVF";
    const outputScriptHash = decodeAddress(outputAddress);
    debugPrint("Output Script Hash", outputScriptHash.toString('hex'));

    // Create P2SH output script: OP_HASH160 <script_hash> OP_EQUAL
    const outputScript = Buffer.concat([
        Buffer.from([0xa9]),  // OP_HASH160
        Buffer.from([outputScriptHash.length]), // Push 20 bytes
        outputScriptHash,
        Buffer.from([0x87])   // OP_EQUAL
    ]);
    debugPrint("Output Script", outputScript.toString('hex'));

    const txOut = Buffer.concat([
        value,
        Buffer.from([outputScript.length]), // Length of output script
        outputScript
    ]);

    // Locktime
    const locktime = Buffer.from([0x00, 0x00, 0x00, 0x00]); // 0, little-endian

    // BIP143 sighash calculation
    // 1. Hash prevouts (double SHA256 of all input outpoints)
    const prevouts = Buffer.concat([prevTx, prevIndex]);
    const hashPrevouts = doubleSha256(prevouts);
    debugPrint("Hash Prevouts", hashPrevouts.toString('hex'));

    // 2. Hash sequence (double SHA256 of all input sequences)
    const hashSequence = doubleSha256(sequence);
    debugPrint("Hash Sequence", hashSequence.toString('hex'));

    // 3. Hash outputs (double SHA256 of all outputs)
    const hashOutputs = doubleSha256(txOut);
    debugPrint("Hash Outputs", hashOutputs.toString('hex'));

    // 4. Build sighash preimage according to BIP143
    // Script code is the redeem script with a length prefix
    const scriptCode = Buffer.concat([
        Buffer.from([redeemScript.length]), // Length of redeem script
        redeemScript
    ]);

    // Input amount (0 for our dummy input)
    const amount = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);

    const sighashType = Buffer.from([0x01, 0x00, 0x00, 0x00]); // SIGHASH_ALL (1), little-endian

    const sighashPreimage = Buffer.concat([
        version,
        hashPrevouts,
        hashSequence,
        prevTx,
        prevIndex,
        scriptCode,
        amount,
        sequence,
        hashOutputs,
        locktime,
        sighashType
    ]);

    // Calculate the hash that needs to be signed
    const sighash = doubleSha256(sighashPreimage);
    debugPrint("Sighash", sighash.toString('hex'));

    // Generate signatures with both private keys using bitcoinjs-lib
    const network = bitcoin.networks.bitcoin;

    // Create key pairs from private keys using the ECPair factory
    const keyPair1 = ECPair.fromPrivateKey(Buffer.from(privKey1, 'hex'), { network });
    const keyPair2 = ECPair.fromPrivateKey(Buffer.from(privKey2, 'hex'), { network });

    // Sign the hash with both keys and convert Uint8Array to Buffer
    const sig1 = Buffer.from(keyPair1.sign(sighash));
    const sig2 = Buffer.from(keyPair2.sign(sighash));

    // Encode signatures with SIGHASH_ALL
    const sig1Obj = bitcoin.script.signature.encode(sig1, 0x01); // 0x01 is SIGHASH_ALL
    const sig2Obj = bitcoin.script.signature.encode(sig2, 0x01);

    debugPrint("Signature 1", sig1Obj.toString('hex'));
    debugPrint("Signature 2", sig2Obj.toString('hex'));

    // Create witness stack
    let witness = Buffer.alloc(0);

    // Number of witness stack items (4)
    witness = Buffer.concat([witness, Buffer.from([0x04])]);

    // 1. Empty item (dummy for CHECKMULTISIG bug)
    witness = Buffer.concat([witness, Buffer.from([0x00])]);

    // 2. Second signature
    witness = Buffer.concat([
        witness,
        Buffer.from([sig2Obj.length]), // Length of sig2
        sig2Obj
    ]);

    // 3. First signature
    witness = Buffer.concat([
        witness,
        Buffer.from([sig1Obj.length]), // Length of sig1
        sig1Obj
    ]);

    // 4. Redeem script
    witness = Buffer.concat([
        witness,
        Buffer.from([redeemScript.length]), // Length of redeem script
        redeemScript
    ]);

    debugPrint("Witness", witness.toString('hex'));

    // Construct final transaction
    const finalTx = Buffer.concat([
        version,     // Version
        marker,      // Segwit marker
        flag,        // Segwit flag
        inputCount,  // Input count
        txIn,        // Input
        outputCount, // Output count
        txOut,       // Output
        witness,     // Witness data
        locktime     // Locktime
    ]);

    const finalTxHex = finalTx.toString('hex');
    debugPrint("Final Transaction", finalTxHex);

    // Write to file
    fs.writeFileSync('out.txt', finalTxHex);

    console.log("\n=== Transaction Creation Complete ===\n");
    console.log("Transaction hex has been written to out.txt");

    return finalTxHex;
}

// Run the function
try {
    createMultisigTransaction();
} catch (error) {
    console.error("Error creating transaction:", error);
}