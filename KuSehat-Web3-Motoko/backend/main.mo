import { "http_request" } from "ic:canisters/http_outcall";
import Text "mo:base/Text";
import Nat64 "mo:base/Nat64";
import Error "mo:base/Error";

actor {
    // PENTING: Ganti dengan alamat IP lokal Anda tempat API Flask berjalan
    let FLASK_API_URL = "http://127.0.0.1:5003/"; 

    // Fungsi helper untuk membuat panggilan POST ke API Flask
    private func post(endpoint: Text, bodyJson: Text): async (Text) {
        let url = FLASK_API_URL # endpoint;
        let request_body = Text.encodeUtf8(bodyJson);
        
        let request : HttpRequest = {
            url;
            method = #POST;
            headers = [("Content-Type", "application/json")];
            body = ?request_body;
            transform = ?{
                function = transform;
                context = Blob.fromArray([]);
            };
        };

        // Alokasikan cycles untuk panggilan HTTP
        let cycles : Nat64 = 2_000_000_000;
        switch (await http_request(request, cycles)) {
            case (#Ok http_response) {
                return Text.decodeUtf8(http_response.body);
            };
            case (#Err err) {
                return "{\"success\": false, \"message\": \"HTTP Request Failed: " # debug_show(err) # "\"}";
            };
        };
    };

    // Fungsi untuk registrasi
    public shared func register(nama: Text, email: Text, password: Text): async Text {
        let body = "{\"nama\": \"" # nama # "\", \"email\": \"" # email # "\", \"password\": \"" # password # "\"}";
        return await post("/api/register", body);
    };

    // Fungsi untuk login
    public shared func login(email: Text, password: Text): async Text {
        let body = "{\"email\": \"" # email # "\", \"password\": \"" # password # "\"}";
        return await post("/api/login", body);
    };
    
    // Fungsi untuk update data user
    public shared func updateUser(userId: Nat, nama: Text, email: Text, oldPass: Text, newPass: Text): async Text {
        let body = "{\"user_id\": " # Nat.toText(userId) # ", \"nama\": \"" # nama # "\", \"email\": \"" # email # "\", \"old_password\": \"" # oldPass # "\", \"new_password\": \"" # newPass # "\"}";
        return await post("/api/update_user", body);
    };

    // Fungsi untuk top up
    public shared func topup(userId: Nat, jumlah: Nat, metode: Text): async Text {
        let body = "{\"user_id\": " # Nat.toText(userId) # ", \"jumlah\": " # Nat.toText(jumlah) # ", \"metode\": \"" # metode # "\"}";
        return await post("/api/topup", body);
    };

    // Fungsi untuk deteksi penyakit
    public shared func detect(userId: Nat, imageBase64: Text): async Text {
        let body = "{\"user_id\": " # Nat.toText(userId) # ", \"image_base64\": \"" # imageBase64 # "\"}";
        return await post("/api/detect", body);
    };

    // Fungsi untuk menukar gambar
    public shared func exchange(userId: Nat, tujuan: Text, imageBase64: Text): async Text {
        let body = "{\"user_id\": " # Nat.toText(userId) # ", \"tujuan\": \"" # tujuan # "\", \"image_base64\": \"" # imageBase64 # "\"}";
        return await post("/api/exchange", body);
    };

    // Fungsi transform wajib untuk http_outcalls
    query func transform(raw: HttpResponse) : async HttpResponse {
        { ...raw, headers = [] };
    };
};
