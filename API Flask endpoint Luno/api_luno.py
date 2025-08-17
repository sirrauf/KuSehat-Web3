from flask import Flask, render_template
from luno_python.client import Client

app = Flask(__name__)

# Konfigurasi API Luno (ganti dengan API key kamu sendiri)
LUNO_API_KEY_ID = "jnm42w8w23t8v"
LUNO_API_KEY_SECRET = "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc"

# Inisialisasi Luno client
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

@app.route("/")
def home():
    return render_template("index.html", address=None, balance=None, asset=None, error=None)

# ================================
# Endpoint: Alamat deposit
# ================================
@app.route("/luno/address/<asset>")
def luno_address(asset):
    asset = asset.upper()
    try:
        res = luno_client.get_funding_address(asset=asset)
        return render_template("index.html",
                               address=res.get("address"),
                               balance=None,
                               asset=asset,
                               error=None)
    except Exception as e:
        return render_template("index.html",
                               address=None,
                               balance=None,
                               asset=asset,
                               error=str(e))

# ================================
# Endpoint: Saldo akun
# ================================
@app.route("/luno/balance/<asset>")
def luno_balance(asset):
    asset = asset.upper()
    try:
        res = luno_client.get_balances()
        balances = res.get("balance", [])
        for b in balances:
            if b["asset"] == asset:
                return render_template("index.html",
                                       address=None,
                                       balance=b.get("balance"),
                                       asset=asset,
                                       error=None)
        return render_template("index.html",
                               address=None,
                               balance=None,
                               asset=asset,
                               error=f"Asset {asset} tidak ditemukan.")
    except Exception as e:
        return render_template("index.html",
                               address=None,
                               balance=None,
                               asset=asset,
                               error=str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
