import { HttpRequest; HttpResponse; HttpTransform; HttpTransformArgs } from "ic:canisters/http_request";

actor KuSehatBackend {

    // URL Flask API Anda. Gunakan IP lokal saat development.
    // Saat production, ganti dengan URL server Flask Anda yang sudah di-deploy.
    private let flaskApiUrl = "http://127.0.0.1:5002/api";

    // Fungsi proxy generik untuk meneruskan request ke Flask
    private func proxyRequest(endpoint: Text, body: Blob, method: Text): async (Blob, [Text]) {
        let url = flaskApiUrl # endpoint;

        let request_headers = [
            ("Content-Type", "application/json"),
        ];

        let request : HttpRequest = {
            method = method;
            url = url;
            headers = request_headers;
            body = body;
            // Transformasi untuk membersihkan response headers
            transform = ?{
                function = transform;
                context = Blob.fromArray([]);
            };
        };

        // Lakukan panggilan HTTP ke luar (outcall)
        let response = await HttpRequest.http_request(request, 1_000_000_000); // 1 M cycles

        switch (response) {
            case (#Ok(res)) {
                // Ekstrak cookie dari header response Flask
                let cookieHeader = "";
                for (header in res.headers) {
                    if (header.0.toLower() == "set-cookie") {
                        cookieHeader := header.1;
                    };
                };
                return (res.body, [cookieHeader]);
            };
            case (#Err(err)) {
                // Di production, log error ini
                return (Blob.fromArray(Text.encodeUtf8("Error: " # err.0)), []);
            };
        }
    };

    // --- Public Methods untuk dipanggil Frontend ---

    public query func transform(raw: HttpTransformArgs) : async HttpResponse {
        var transformed = raw.response;
        // Hanya simpan header yang kita butuhkan
        var headersToKeep : [(Text,Text)] = [];
        for(h in transformed.headers) {
            if(h.0.toLower() == "content-type" or h.0.toLower() == "set-cookie") {
                headersToKeep := headersToKeep # [h];
            };
        };
        transformed.headers := headersToKeep;
        return transformed;
    };

    public shared func login(email: Text, password: Text): async (Blob, [Text]) {
        let body = "{ \"email\": \"" # email # "\", \"password\": \"" # password # "\" }";
        return await proxyRequest("/login", Blob.fromArray(Text.encodeUtf8(body)), "POST");
    };

    public shared func register(nama: Text, email: Text, password: Text): async (Blob, [Text]) {
        let body = "{ \"nama\": \"" # nama # "\", \"email\": \"" # email # "\", \"password\": \"" # password # "\" }";
        return await proxyRequest("/register", Blob.fromArray(Text.encodeUtf8(body)), "POST");
    };

    // Anda bisa menambahkan fungsi lain untuk setiap endpoint API
    // seperti getUserProfile, diagnose, dll.
}