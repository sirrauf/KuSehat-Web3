// index.js
import { kusehat_backend } from "../../declarations/kusehat_backend";

const app = document.getElementById('app');

// --- Templat HTML untuk setiap bagian ---

const pricingHTML = `
<section id="pricing">
  <h2>Pricing List</h2>
  <table>
    <thead><tr><th>Paket</th><th>Fitur</th><th>Harga</th></tr></thead>
    <tbody>
      <tr><td>Basic</td><td>Fitur Deteksi Penyakit melalui kamera</td><td>IDR. 50.000</td></tr>
      <tr><td>Premium</td><td>1. Fitur Deteksi penyakit melalui kamera, 2. Fitur Deteksi penyakit melalui upload gambar</td><td>IDR. 150.000</td></tr>
    </tbody>
  </table>
</section>`;

const loginHTML = `
<section id="login">
  <h2>Login</h2>
  <form id="login-form">
    <label>Email:</label><br><input type="email" name="email" required><br><br>
    <label>Password:</label><br><input type="password" name="password" required><br><br>
    <button type="submit">Login</button>
  </form>
</section>`;

// ... definisikan template HTML untuk 'register', 'dashboard', dll.

// --- Logika Navigasi ---

function showSection(sectionName) {
    switch (sectionName) {
        case 'pricing':
            app.innerHTML = pricingHTML;
            break;
        case 'login':
            app.innerHTML = loginHTML;
            document.getElementById('login-form').addEventListener('submit', handleLogin);
            break;
        // ... case lainnya
        default:
            app.innerHTML = pricingHTML;
    }
}

// --- Event Handlers ---

async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;

    try {
        // Panggil fungsi 'login' dari canister Motoko
        const result = await kusehat_backend.login(email, password);
        if (result.Ok) {
            alert(result.Ok);
            // Tampilkan dashboard setelah login berhasil
            // showSection('dashboard');
        } else {
            alert(`Error: ${result.Err}`);
        }
    } catch (error) {
        console.error("Gagal memanggil canister:", error);
        alert("Terjadi kesalahan pada frontend.");
    }
}

// --- Inisialisasi ---
document.getElementById('nav-pricing').onclick = () => showSection('pricing');
document.getElementById('nav-login').onclick = () => showSection('login');
// ... tambahkan event listener untuk nav lainnya

// Tampilkan halaman default saat load
showSection('pricing');