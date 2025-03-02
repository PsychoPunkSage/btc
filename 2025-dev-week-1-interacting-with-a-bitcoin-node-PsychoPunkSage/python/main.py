# from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
# import json
# import time

# # Node access params
# RPC_URL = "http://alice:password@127.0.0.1:18443"

# def create_or_load_wallet(rpc, wallet_name="testwallet"):
#     """Create or load a wallet"""
#     try:
#         rpc.loadwallet(wallet_name)
#         print(f"Loaded existing wallet: {wallet_name}")
#     except JSONRPCException:
#         rpc.createwallet(wallet_name)
#         print(f"Created new wallet: {wallet_name}")
#     return AuthServiceProxy(f"{RPC_URL}/wallet/{wallet_name}")

# def mine_blocks(rpc, address, num_blocks):
#     """Mine specified number of blocks to an address"""
#     print(f"Mining {num_blocks} blocks to {address}")
#     for i in range(num_blocks):
#         rpc.generatetoaddress(1, address)
#         if i % 10 == 0:
#             print(f"Mined {i+1} blocks")

# def ensure_sufficient_balance(rpc, required_btc):
#     """Ensure wallet has sufficient balance, mine more if needed"""
#     balance = rpc.getbalance()
#     print(f"Current balance: {balance} BTC")
    
#     while balance < required_btc:
#         print(f"Insufficient balance ({balance} BTC), mining more blocks...")
#         mine_blocks(rpc, rpc.getnewaddress(), 10)
#         # Wait a bit for balance to update
#         time.sleep(1)
#         balance = rpc.getbalance()
#         print(f"New balance: {balance} BTC")

# def create_and_send_tx(rpc, payment_address, amount_btc, message):
#     """Create and send transaction with exact fee rate"""
#     print("Creating transaction...")
    
#     # Convert message to hex
#     message_hex = message.encode('utf-8').hex()
    
#     # Create initial raw transaction
#     raw_tx = rpc.createrawtransaction(
#         [],  # Empty inputs, will be filled by fundrawtransaction
#         [
#             {payment_address: amount_btc},
#             {"data": message_hex}
#         ]
#     )
    
#     # Fund the transaction with exact fee rate
#     funded_tx = rpc.fundrawtransaction(
#         raw_tx,
#         {
#             "fee_rate": 21,
#             "changePosition": 2
#         }
#     )
    
#     # Sign the transaction
#     signed_tx = rpc.signrawtransactionwithwallet(funded_tx["hex"])
#     if not signed_tx["complete"]:
#         raise Exception("Failed to sign transaction")
    
#     # Decode the signed transaction to verify details
#     decoded_tx = rpc.decoderawtransaction(signed_tx["hex"])
#     print(f"Transaction virtual size: {decoded_tx['vsize']} vBytes")
#     print("Transaction outputs:")
#     for i, vout in enumerate(decoded_tx['vout']):
#         if 'value' in vout:
#             print(f"  Output {i}: {vout['value']} BTC")
#         if 'scriptPubKey' in vout and 'hex' in vout['scriptPubKey']:
#             print(f"  Output {i} script: {vout['scriptPubKey']['hex'][:30]}...")
    
#     # Calculate and verify fee
#     inputs_value = sum(rpc.getrawtransaction(vin['txid'], True)['vout'][vin['vout']]['value'] 
#                       for vin in decoded_tx['vin'])
#     outputs_value = sum(vout['value'] for vout in decoded_tx['vout'] if 'value' in vout)
#     fee_btc = inputs_value - outputs_value
#     fee_sats = int(fee_btc * 100000000)  # Convert to satoshis
#     expected_fee = decoded_tx['vsize'] * 21
#     print(f"Fee: {fee_sats} satoshis (expected: {expected_fee} satoshis)")
    
#     if abs(fee_sats - expected_fee) > 1:  # Allow 1 satoshi rounding difference
#         raise Exception(f"Fee {fee_sats} sats doesn't match expected fee {expected_fee} sats")
    
#     # Send the transaction
#     txid = rpc.sendrawtransaction(signed_tx["hex"])
#     print(f"Transaction sent with ID: {txid}")
    
#     return txid

# def main():
#     try:
#         # Connect to Bitcoin node
#         print("Connecting to Bitcoin node...")
#         rpc = AuthServiceProxy(RPC_URL)
        
#         # Check connection
#         info = rpc.getblockchaininfo()
#         print(f"Connected to node: {info['chain']}")
        
#         # Create/load wallet
#         wallet_rpc = create_or_load_wallet(rpc)
        
#         # Generate new address
#         mining_address = wallet_rpc.getnewaddress()
#         print(f"Mining address: {mining_address}")
        
#         # Mine initial blocks
#         print("Mining initial blocks...")
#         mine_blocks(wallet_rpc, mining_address, 101)
        
#         # Ensure we have enough balance
#         ensure_sufficient_balance(wallet_rpc, 100.0)
        
#         # Create and send transaction
#         payment_address = "bcrt1qq2yshcmzdlznnpxx258xswqlmqcxjs4dssfxt2"
#         message = "We are all Satoshi!!"
        
#         txid = create_and_send_tx(
#             wallet_rpc,
#             payment_address,
#             100.0,
#             message
#         )
        
#         # Write txid to file
#         print(f"Writing txid to out.txt: {txid}")
#         with open("out.txt", "w") as f:
#             f.write(txid)
            
#     except Exception as e:
#         print(f"Error: {str(e)}")
#         raise

# if __name__ == "__main__":
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
import time
import socket
import sys

# Node access params
RPC_URL = "http://alice:password@127.0.0.1:18443"

def wait_for_rpc_connection(max_retries=60, retry_interval=1):
    """Wait for RPC connection to be established"""
    print("Waiting for Bitcoin node to start...")
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Try to create a socket connection first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 18443))
            sock.close()
            
            if result == 0:
                # Port is open, try RPC connection
                rpc = AuthServiceProxy(RPC_URL)
                rpc.getblockchaininfo()
                print("Successfully connected to Bitcoin node")
                return rpc
        except (socket.error, ConnectionRefusedError, JSONRPCException) as e:
            if "Verifying blocks" in str(e):
                print("Node is still verifying blocks...")
            elif "Loading block index" in str(e):
                print("Node is still loading block index...")
            elif retry_count % 5 == 0:  # Only print every 5th attempt
                print(f"Waiting for node to be ready... ({retry_count + 1}/{max_retries})")
        except Exception as e:
            if retry_count % 5 == 0:
                print(f"Unexpected error while connecting: {str(e)}")
        
        retry_count += 1
        time.sleep(retry_interval)
        
    raise Exception("Failed to connect to Bitcoin node after maximum retries")

def create_or_load_wallet(rpc, wallet_name="testwallet"):
    """Create or load a wallet"""
    try:
        rpc.loadwallet(wallet_name)
        print(f"Loaded existing wallet: {wallet_name}")
    except JSONRPCException:
        rpc.createwallet(wallet_name)
        print(f"Created new wallet: {wallet_name}")
    return AuthServiceProxy(f"{RPC_URL}/wallet/{wallet_name}")

def mine_blocks(rpc, address, num_blocks):
    """Mine specified number of blocks to an address"""
    print(f"Mining {num_blocks} blocks to {address}")
    for i in range(num_blocks):
        rpc.generatetoaddress(1, address)
        if i % 10 == 0:
            print(f"Mined {i+1} blocks")
    # Wait for blocks to be processed
    time.sleep(1)

def ensure_sufficient_balance(rpc, required_btc):
    """Ensure wallet has sufficient balance, mine more if needed"""
    balance = rpc.getbalance()
    print(f"Current balance: {balance} BTC")
    
    while balance < required_btc:
        print(f"Insufficient balance ({balance} BTC), mining more blocks...")
        mine_blocks(rpc, rpc.getnewaddress(), 10)
        balance = rpc.getbalance()
        print(f"New balance: {balance} BTC")

def send_with_op_return(rpc, address, amount, message):
    """Send transaction with OP_RETURN output"""
    # Convert message to hex
    message_hex = message.encode().hex()
    
    # Create raw transaction with empty inputs
    raw_tx = rpc.createrawtransaction(
        [],  # Empty inputs
        [
            {address: amount},  # Payment output
            {"data": message_hex}  # OP_RETURN output
        ]
    )
    
    # Fund the transaction with specific fee rate
    funded_tx = rpc.fundrawtransaction(
        raw_tx,
        {
            "fee_rate": 21,
            "changePosition": 1
        }
    )
    
    # Sign the transaction
    signed_tx = rpc.signrawtransactionwithwallet(funded_tx["hex"])
    if not signed_tx["complete"]:
        raise Exception("Failed to sign transaction")
    
    # Send the transaction
    txid = rpc.sendrawtransaction(signed_tx["hex"])
    
    # Wait for transaction to be processed
    time.sleep(1)
    
    # Verify transaction
    tx = rpc.gettransaction(txid, True, True)
    
    # Verify outputs in decoded transaction
    decoded = tx["decoded"]
    payment_output = next((out for out in decoded["vout"] if out.get("value") == amount), None)
    op_return_output = next((out for out in decoded["vout"] if out["scriptPubKey"]["type"] == "nulldata"), None)
    
    if not payment_output or payment_output["scriptPubKey"]["address"] != address:
        raise Exception("Payment output incorrect")
    
    if not op_return_output or not op_return_output["scriptPubKey"]["hex"].startswith("6a14"):
        raise Exception("OP_RETURN output incorrect")
    
    return txid

def main():
    try:
        # Connect to Bitcoin node with retry mechanism
        print("Connecting to Bitcoin node...")
        rpc = wait_for_rpc_connection()
        
        # Create/load wallet
        wallet_rpc = create_or_load_wallet(rpc)
        
        # Generate new address
        mining_address = wallet_rpc.getnewaddress()
        print(f"Mining address: {mining_address}")
        
        # Mine initial blocks
        print("Mining initial blocks...")
        mine_blocks(wallet_rpc, mining_address, 101)
        
        # Ensure we have enough balance
        ensure_sufficient_balance(wallet_rpc, 100.0)
        
        # Send transaction
        payment_address = "bcrt1qq2yshcmzdlznnpxx258xswqlmqcxjs4dssfxt2"
        message = "We are all Satoshi!!"
        
        txid = send_with_op_return(
            wallet_rpc,
            payment_address,
            100.0,
            message
        )
        
        print(f"Transaction sent: {txid}")
        
        # Verify transaction details
        tx = wallet_rpc.gettransaction(txid, True, True)
        print("Transaction details:")
        print(f"  Fee: {int(float(-tx['fee']) * 1e8)} satoshis")
        print(f"  vSize: {tx['decoded']['vsize']} vBytes")
        
        # Write txid to file
        print(f"Writing txid to out.txt: {txid}")
        with open("out.txt", "w") as f:
            f.write(txid)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()