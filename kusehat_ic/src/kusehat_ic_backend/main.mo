import {
  HttpRequest,
  HttpResponse,
  HttpTransform,
  HttpTransformArgs,
} from "ic:canisters/http_request";
import Nat "mo:base/Nat";
import Text "mo:base/Text";

actor {
  // Ganti dengan URL publik Flask API Anda saat deploy di mainnet
  // Untuk development lokal, Anda bisa menggunakan IP lokal Anda
  // Catatan: 'localhost' tidak akan berfungsi dari canister. Gunakan IP seperti 'http://192.168.1.5:8000'
  let flaskApiHost : Text = "http://127.0.0.1:8000"; // Ganti ini jika perlu

  // Token API statis yang Anda berikan
  let apiToken : Text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTU3NzU2ODksImlkIjoiMSJ9.C2v_OnjLV8CuNInnZ4iTRoa6_jWYZsf_wJRREbqMS5g";

  // Fungsi helper untuk membuat permintaan HTTP POST dengan token
  private func makeApiRequest(url: Text, jsonBody: Text): async Text {
    let request_headers = [
      ("Content-Type", "application/json"),
      ("Authorization", "Bearer " # apiToken) // Menambahkan token di header
    ];

    let request = {
      url: url;
      method: { #"POST" };
      body: ?(Text.encode(jsonBody));
      headers: request_headers;
      // Transformasi tidak diperlukan untuk request sederhana ini
      transform: ?{ function = transform; context = #{} };
    };

    // Lakukan panggilan HTTP
    let (response) : (HttpResponse) = await HttpRequest.http_request(request, 2_000_000_000);

    // Kembalikan body dari response
    switch (response.body) {
      case (?body) {
        return Text.decode(body);
      }
      case (_) {
        return "{\"error\": \"Failed to decode response body\"}";
      }
    };
  };

  // Endpoint untuk Registrasi
  public query func register(username: Text, password: Text): async Text {
    let url = flaskApiHost # "/auth/register";
    let jsonBody = "{\"username\": \"" # username # "\", \"password\": \"" # password # "\"}";
    return await makeApiRequest(url, jsonBody);
  };

  // Endpoint untuk Login
  public query func login(username: Text, password: Text): async Text {
    let url = flaskApiHost # "/auth/login";
    let jsonBody = "{\"username\": \"" # username # "\", \"password\": \"" # password # "\"}";
    return await makeApiRequest(url, jsonBody);
  };

  // Endpoint untuk Top Up
  public query func topup(user_id: Text, metode: Text, jumlah: Nat): async Text {
    let url = flaskApiHost # "/user/topup";
    let jsonBody = "{\"user_id\": \"" # user_id # "\", \"metode\": \"" # metode # "\", \"jumlah\": " # Nat.toText(jumlah) # "}";
    return await makeApiRequest(url, jsonBody);
  };

  // Fungsi transform yang dibutuhkan oleh http_request
  // Ini membersihkan header response sebelum dikembalikan ke canister
  query func transform(args: HttpTransformArgs): async HttpResponse {
    var transformedResponse = args.response;
    // Kosongkan header untuk keamanan
    transformedResponse.headers = [];
    return transformedResponse;
  };
}