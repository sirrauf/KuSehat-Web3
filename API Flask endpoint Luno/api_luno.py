from flask import Flask, jsonify
from luno_python.client import Client

app = Flask(__name__)

# Konfigurasi API Luno (ganti dengan API key milikmu sendiri)
LUNO_API_KEY_ID = "jnm42w8w23t8v"
LUNO_API_KEY_SECRET = "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc"
# Inisialisasi Luno client
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# ================================
# Endpoint: Ambil alamat deposit
# ================================
@app.route("/api/luno/address/<asset>", methods=["GET"])
def get_luno_address(asset):
    """
    Ambil alamat deposit kripto (funding address) dari Luno.
    Contoh:
      /api/luno/address/btc
      /api/luno/address/eth
    """
    asset = asset.upper()
    try:
        res = luno_client.get_funding_address(asset=asset)
        return jsonify({
            "status": "success",
            "asset": asset,
            "address": res.get("address", None),
            "response": res
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "asset": asset,
            "message": str(e)
        }), 400

# ================================
# Endpoint: Ambil saldo akun
# ================================
@app.route("/api/luno/balance/<asset>", methods=["GET"])
def get_luno_balance(asset):
    """
    Ambil saldo akun di Luno berdasarkan aset.
    Contoh:
      /api/luno/balance/btc
      /api/luno/balance/eth
    """
    asset = asset.upper()
    try:
        res = luno_client.get_balances()
        balances = res.get("balance", [])
        for b in balances:
            if b["asset"] == asset:
                return jsonify({
                    "status": "success",
                    "asset": asset,
                    "balance": b.get("balance"),
                    "reserved": b.get("reserved"),
                    "unconfirmed": b.get("unconfirmed")
                })
        return jsonify({"status": "error", "message": f"Asset {asset} tidak ditemukan."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
