import { "http_request" } from "mo:base/ExperimentalInternetComputer";
import Text "mo:base/Text";
import Nat "mo:base/Nat";
import ExperimentalCycles "mo:base/ExperimentalCycles";

actor KusehatBackend {

    // Tipe data untuk argumen fungsi
    public type RegisterArgs = {
        name: Text;
        email: Text;
        password: Text;
    };

    public type LoginArgs = {
        email: Text;
        password: Text;
    };

    public type TopupArgs = {
        user_id: Text;
        metode: Text;
        jumlah: Nat;
        token: Text; // Token dikirim dari frontend
    };

    // Helper untuk mengubah [Nat8] (blob) menjadi Text
    private func blobToText(b: [Nat8]) : Text {
        var t = "";
        for (c in b) {
            t #= Text.fromChar(Char.fromNat(c));
        };
        return t;
    };

    // Fungsi untuk REGISTER
    public shared update func register(args: RegisterArgs) : async Result.Result<Text, Text> {
        let url = "http://localhost:8000/auth/register";

        // Membuat body JSON secara manual
        let json_body = "{ \"name\": \"" # args.name # "\", \"email\": \"" # args.email # "\", \"password\": \"" # args.password # "\" }";

        let request_headers: [http_request.Header] = [
            { name = "Content-Type"; value = "application/json" }
        ];

        let request : http_request.HttpRequest = {
            url;
            method = #POST;
            headers = request_headers;
            body = some Text.encodeUtf8(json_body);
        };

        // Panggilan HTTP keluar membutuhkan cycles
        ExperimentalCycles.add(2_000_000_000); // Menambahkan cycles untuk panggilan

        switch (await http_request.http_request(request, null)) {
            case (Result.Ok(response)) {
                return Result.Ok(blobToText(response.body));
            };
            case (Result.Err(err)) {
                return Result.Err(err.0 # ": " # err.1);
            };
        };
    };

    // Fungsi untuk LOGIN
    public shared update func login(args: LoginArgs) : async Result.Result<Text, Text> {
        let url = "http://localhost:8000/auth/login";
        let json_body = "{ \"email\": \"" # args.email # "\", \"password\": \"" # args.password # "\" }";

        let request : http_request.HttpRequest = {
            url;
            method = #POST;
            headers = [{ name = "Content-Type"; value = "application/json" }];
            body = some Text.encodeUtf8(json_body);
        };

        ExperimentalCycles.add(2_000_000_000);

        switch (await http_request.http_request(request, null)) {
            case (Result.Ok(response)) {
                return Result.Ok(blobToText(response.body));
            };
            case (Result.Err(err)) {
                return Result.Err(err.0 # ": " # err.1);
            };
        };
    };

    // Fungsi untuk TOP UP
    public shared update func topup(args: TopupArgs) : async Result.Result<Text, Text> {
        let url = "http://localhost:8000/user/topup";
        let json_body = "{ \"user_id\": \"" # args.user_id # "\", \"metode\": \"" # args.metode # "\", \"jumlah\": " # Nat.toText(args.jumlah) # " }";

        let request_headers: [http_request.Header] = [
            { name = "Content-Type"; value = "application/json" },
            { name = "Authorization"; value = "Bearer " # args.token } // Menggunakan token
        ];

        let request : http_request.HttpRequest = {
            url;
            method = #POST;
            headers = request_headers;
            body = some Text.encodeUtf8(json_body);
        };

        ExperimentalCycles.add(2_000_000_000);

        switch (await http_request.http_request(request, null)) {
            case (Result.Ok(response)) {
                return Result.Ok(blobToText(response.body));
            };
            case (Result.Err(err)) {
                return Result.Err(err.0 # ": " # err.1);
            };
        };
    };
}