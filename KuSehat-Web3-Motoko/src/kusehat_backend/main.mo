// main.mo
import Text "mo:base/Text";
import Nat "mo:base/Nat";
import Result "mo:base/Result";
import Error "mo:base/Error";

actor KuSehat {

    // --- Type Definitions ---

    public type UserProfile = {
        nama: Text;
        email: Text;
        saldo: Float;
        riwayat_penukaran: [ExchangeHistory];
    };

    public type ExchangeHistory = {
        tujuan: Text;
        tanggal: Text; // ISO 8601 format
        reward: Float;
    };

    public type DiagnosisResult = {
        penyakit: Text;
        kepercayaan: Text;
        penjelasan: Text;
        image_url: Text;
    };

    public type ExchangeReward = {
        message: Text;
        saldo_baru: Float;
    };
    
    public type DepositAddress = {
        address: Text;
    };

    // Alamat URL backend Flask Anda
    private let backendUrl = "http://127.0.0.1:5000/api";

    // --- Public Functions (Canister Methods) ---

    // Registrasi Pengguna
    public query func register(nama: Text, email: Text, password: Text): async Result.Result<Text, Text> {
        let url = backendUrl # "/register";
        let requestBody = Text.encodeUtf8(
            "{ \"nama\": \"" # nama # "\", \"email\": \"" # email # "\", \"password\": \"" # password # "\" }"
        );
        
        let requestHeaders : [(Text, Text)] = [("Content-Type", "application/json")];

        let http_request : HttpRequest = {
            method = "POST";
            url = url;
            headers = requestHeaders;
            body = requestBody;
        };

        // ... Logika untuk membuat panggilan HTTP (membutuhkan library http_request)
        // Karena Motoko Playground tidak mendukung outcall, ini adalah pseudo-code
        // return await handleHttpResponse(http_request);
        return Result.Ok("Panggilan ke /register disimulasikan");
    };

    // Login Pengguna
    public query func login(email: Text, password: Text): async Result.Result<Text, Text> {
        let url = backendUrl # "/login";
        // ... (implementasi serupa dengan register)
        return Result.Ok("Panggilan ke /login disimulasikan");
    };

    // Mendapatkan Profil User (membutuhkan autentikasi/session)
    public query func getProfile(): async Result.Result<UserProfile, Text> {
        let url = backendUrl # "/user";
        // ... (implementasi serupa, perlu mengirim cookie session)
        // Mock data
        return Result.Ok({
            nama = "User Demo";
            email = "demo@example.com";
            saldo = 50000.0;
            riwayat_penukaran = [];
        });
    };
    
    // Mendapatkan Alamat Top-Up
    public query func getTopUpAddress(metode: Text, jumlah: Float): async Result.Result<DepositAddress, Text> {
        let url = backendUrl # "/topup/address";
        // ... (implementasi serupa)
        return Result.Ok({ address = "bc1q-simulated-address-for-testing" });
    };

    // Fungsi lain seperti 'diagnose' dan 'exchange' akan membutuhkan penanganan 'multipart/form-data'
    // yang lebih kompleks dan saat ini sulit dilakukan secara native di Motoko tanpa library eksternal.
}