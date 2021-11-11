import base64
import os
from typing import Any

import uvicorn
from evmosgrpc.broadcaster import broadcast
from evmosgrpc.builder import ExternalWallet
from evmosgrpc.constants import CHAIN_ID
from evmosgrpc.messages.msgsend import create_msg_send
from evmosgrpc.transaction import create_tx_raw
from evmosgrpc.transaction import Transaction
from evmoswallet.eth.ethereum import sha3_256
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.protobuf.json_format import MessageToDict

from schemas import BroadcastData
from schemas import MessageData
from schemas import SendAphotons

origin = os.getenv('FRONTEND_WEBPAGE', '*')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def generate_message(tx: Transaction, builder: ExternalWallet, msg: Any):
    tx.create_tx_template(builder, msg)
    to_sign = tx.create_sig_doc()
    bodyBytes = base64.b64encode(tx.body.SerializeToString())
    authInfoBytes = base64.b64encode(tx.info.SerializeToString())
    chainId = CHAIN_ID
    accountNumber = int(builder.account_number)
    return {
        'bodyBytes': bodyBytes,
        'authInfoBytes': authInfoBytes,
        'chainId': chainId,
        'accountNumber': accountNumber,
        'signBytes': base64.b64encode(sha3_256(to_sign).digest())
    }


@app.post('/send_aphotons', response_model=MessageData)
def create_msg(data: SendAphotons):
    builder = ExternalWallet(
        data.wallet.address,
        data.wallet.algo,
        base64.b64decode(data.wallet.pubkey),
    )
    tx = Transaction()
    msg = create_msg_send(
        builder.address,
        data.destination,
        data.amount,
    )
    return generate_message(tx, builder, msg)


@app.post('/broadcast')
def signed_msg(data: BroadcastData):
    raw = create_tx_raw(
        body_bytes=base64.b64decode(data.bodyBytes),
        auth_info=base64.b64decode(data.authBytes),
        signature=base64.b64decode(data.signature),
    )
    result = broadcast(raw)
    dictResponse = MessageToDict(result)
    if 'code' in dictResponse['txResponse'].keys():
        return {'res': dictResponse['txResponse']['rawLog']}
    return {'res': dictResponse['txResponse']['txhash']}


if __name__ == '__main__':
    uvicorn.run(app)
