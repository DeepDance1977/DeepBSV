VALID_GETMININGCANDIDATE_RESPONSE = {
    "id": "cand_00112233445566778899",
    "prevhash": "00000000000000000123456789abcdef0123456789abcdef0123456789abcdef",
    "version": 536870912,
    "nbits": "1d00ffff",
    "time": 1700000000,
    "height": 820000,
    "coinbasevalue": 625000000,
    "coinbase": "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff",
    "merkleproof": [
        "1111111111111111111111111111111111111111111111111111111111111111",
        "2222222222222222222222222222222222222222222222222222222222222222"
    ]
}

RPC_ERROR_RESPONSE = {
    "result": None,
    "error": {
        "code": -10,
        "message": "Node is syncing, mining candidate unavailable"
    },
    "id": "deepbsv"
}
