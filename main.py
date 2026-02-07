import asyncio
import os
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from spl.token.instructions import (
    get_associated_token_address,
    create_idempotent_associated_token_account,
    transfer_checked,
    TransferCheckedParams
)
from spl.token.constants import TOKEN_PROGRAM_ID

# --- CONSTANTS ---
RPC_URL = "https://api.devnet.solana.com"
TOKEN_MINT_ADDRESS = os.environ('token_address')
RAW_TREASURY_BYTES = os.environ('sol_key') # Your full 64-number list
DECIMALS = 9

async def send_study_reward(user_wallet_address: str, amount: float):
    """
    Sends tokens to a user. Handles account creation automatically.
    :param user_wallet_address: The public key of the user (string)
    :param amount: The number of tokens to send (e.g., 5.0)
    """
    try:
        async with AsyncClient(RPC_URL) as client:
            # 1. Setup Identities
            treasury = Keypair.from_bytes(bytes(RAW_TREASURY_BYTES))
            mint = Pubkey.from_string(TOKEN_MINT_ADDRESS)
            user_pubkey = Pubkey.from_string(user_wallet_address)

            # 2. Derive Token Accounts (ATAs)
            source_ata = get_associated_token_address(treasury.pubkey(), mint)
            dest_ata = get_associated_token_address(user_pubkey, mint)

            # 3. Create Instructions
            # ix1: Create account if missing. ix2: Transfer tokens.
            ix1 = create_idempotent_associated_token_account(treasury.pubkey(), user_pubkey, mint)
            ix2 = transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source_ata,
                    dest=dest_ata,
                    mint=mint,
                    owner=treasury.pubkey(),
                    amount=int(amount * (10**DECIMALS)),
                    decimals=DECIMALS
                )
            )

            # 4. Fetch Blockhash & Compile Message
            blockhash_resp = await client.get_latest_blockhash()
            message = MessageV0.try_compile(
                payer=treasury.pubkey(),
                instructions=[ix1, ix2],
                address_lookup_table_accounts=[],
                recent_blockhash=blockhash_resp.value.blockhash
            )

            # 5. Create Signed Transaction
            tx = VersionedTransaction(message, [treasury])

            # 6. Send to Blockchain
            resp = await client.send_transaction(tx)
            print(f"✅ Reward of {amount} tokens sent to {user_wallet_address[:6]}...")
            print(f"🔗 Transaction: https://explorer.solana.com/tx/{resp.value}?cluster=devnet")
            return resp.value

    except Exception as e:
        print(f"❌ Failed to send reward: {e}")
        return None

# --- HOW TO USE IT ---
if __name__ == "__main__":
    # Example: Send 5.5 tokens to a user when they finish a task
    target_user = "PASTE_A_USER_PUBKEY_HERE"
    asyncio.run(send_study_reward(target_user, 5.5))