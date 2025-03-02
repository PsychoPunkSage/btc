/**
 * This script uses bcoin's internal methods to create a transaction
 * exactly as bcoin expects it, which should pass verification.
 */

const bcoin = require('bcoin');
const { Script, TX, MTX, KeyRing, Coin, CoinView, Stack } = bcoin;
const fs = require('fs');

// Set up network
bcoin.set('regtest');

// Create the private keys
const privateKey1 = '39dc0a9f0b185a2ee56349691f34716e6e0cda06a7f9707742ac113c4e2317bf';
const privateKey2 = '5077ccd9c558b7d04a81920d38aa11b4a9f9de3b23fab45c3ef28039920fdd6d';

// Create key rings from private keys
const keyRing1 = KeyRing.fromPrivate(Buffer.from(privateKey1, 'hex'));
const keyRing2 = KeyRing.fromPrivate(Buffer.from(privateKey2, 'hex'));

// Get public keys
const pubKey1 = keyRing1.getPublicKey();
const pubKey2 = keyRing2.getPublicKey();

console.log('Public key 1:', pubKey1.toString('hex'));
console.log('Public key 2:', pubKey2.toString('hex'));

// Create the redeem script (in the same order specified in the requirements)
const redeemScript = Script.fromMultisig(2, 2, [
    Buffer.from('032ff8c5df0bc00fe1ac2319c3b8070d6d1e04cfbf4fedda499ae7b775185ad53b', 'hex'),
    Buffer.from('039bbc8d24f89e5bc44c5b0d1980d6658316a6b2440023117c3c03a4975b04dd56', 'hex')
]);

console.log('Redeem script hex:', redeemScript.toRaw().toString('hex'));

// Create P2WSH script
const p2wsh = Script.fromProgram(0, Script.hash256(redeemScript.toRaw()));

// Create P2SH address from the P2WSH script
const p2sh = Script.fromScripthash(Script.hash160(p2wsh.toRaw()));
const address = p2sh.getAddress().toString();

console.log('P2SH-P2WSH address:', address);

// Now, let's create an MTX (mutable transaction)
const mtx = new MTX();

// Add the input exactly as specified in the requirements
mtx.addInput({
    prevout: {
        hash: Buffer.from('0000000000000000000000000000000000000000000000000000000000000000', 'hex'),
        index: 0
    },
    sequence: 0xffffffff
});

// Add the output
mtx.addOutput({
    value: 100000,
    address: address
});

// Create the coin
const coin = Coin.fromJSON({
    version: 2,
    height: 0,
    value: 100000,
    script: Script.fromAddress(address).toRaw().toString('hex'),
    coinbase: false,
    hash: '0000000000000000000000000000000000000000000000000000000000000000',
    index: 0
});

// Make sure the script is correctly set
mtx.inputs[0].script = Script.fromRaw(
    Buffer.concat([
        Buffer.from([p2wsh.toRaw().length]),
        p2wsh.toRaw()
    ])
);

// Sign the transaction with bcoin's internal methods
(async () => {
    try {
        // First, we need to add the coin to the view
        const view = new CoinView();
        view.addCoin(coin);

        // Stack of signatures
        const stack = new Stack();

        // Add empty element for CHECKMULTISIG bug
        stack.push(Buffer.alloc(0));

        // Sign with key1
        const signature1 = mtx.signature(
            0, redeemScript, coin.value, keyRing1.privateKey, 1
        );
        stack.push(Buffer.concat([signature1, Buffer.from([0x01])])); // SIGHASH_ALL

        // Sign with key2
        const signature2 = mtx.signature(
            0, redeemScript, coin.value, keyRing2.privateKey, 1
        );
        stack.push(Buffer.concat([signature2, Buffer.from([0x01])])); // SIGHASH_ALL

        // Add redeem script
        stack.push(redeemScript.toRaw());

        // Set the witness
        mtx.inputs[0].witness.fromStack(stack);

        // Finalize and convert to regular TX
        const tx = mtx.toTX();

        // Verify
        const valid = tx.verify(view);
        console.log('Transaction valid:', valid);

        // Write to file
        fs.writeFileSync('bcoin_generated.txt', tx.toRaw().toString('hex'));

        // Also copy to out.txt for testing
        fs.writeFileSync('out.txt', tx.toRaw().toString('hex'));

        console.log('Transaction hex written to bcoin_generated.txt and out.txt');
        console.log('Now run the tests to see if it passes');

        // Print hex for verification
        console.log('\nTransaction hex:');
        console.log(tx.toRaw().toString('hex'));

        // Print witness data for verification
        console.log('\nWitness data:');
        for (let i = 0; i < tx.inputs[0].witness.items.length; i++) {
            console.log(`Item ${i}:`, tx.inputs[0].witness.items[i].toString('hex'));
        }
    } catch (error) {
        console.error('Error:', error.message);
    }
})();