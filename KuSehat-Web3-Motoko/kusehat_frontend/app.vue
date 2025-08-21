<template>
  <div class="container">
    <h1>Kusehat App Interface</h1>
    <p>Berinteraksi dengan Flask API melalui Canister Motoko.</p>

    <div class="card">
      <h2>Register</h2>
      <input v-model="registerForm.name" placeholder="Name" />
      <input v-model="registerForm.email" placeholder="Email" type="email" />
      <input v-model="registerForm.password" placeholder="Password" type="password" />
      <button @click="handleRegister">Register</button>
    </div>

    <div class="card">
      <h2>Login</h2>
      <input v-model="loginForm.email" placeholder="Email" type="email" />
      <input v-model="loginForm.password" placeholder="Password" type="password" />
      <button @click="handleLogin">Login</button>
    </div>

    <div class="card">
      <h2>Top Up</h2>
      <input v-model="topupForm.user_id" placeholder="User ID" />
      <input v-model="topupForm.metode" placeholder="Metode (e.g., gopay)" />
      <input v-model.number="topupForm.jumlah" placeholder="Jumlah" type="number" />
      <textarea v-model="topupForm.token" placeholder="Paste JWT Token Here"></textarea>
      <button @click="handleTopup">Top Up</button>
    </div>
    
    <div class="response-card" v-if="apiResponse">
        <h3>API Response:</h3>
        <pre>{{ apiResponse }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { Actor, HttpAgent } from "@dfinity/agent";
// Impor candid dari file yang digenerate oleh dfx
import { idlFactory as kusehat_backend_idl, canisterId as kusehat_backend_id } from 'declarations/kusehat_backend';

// Konfigurasi agent untuk berinteraksi dengan canister
const agent = new HttpAgent({ host: window.location.origin });
// Untuk dev local, ganti host jika perlu:
// const agent = new HttpAgent({ host: "http://localhost:4943" });

const backend = Actor.createActor(kusehat_backend_idl, {
  agent,
  canisterId: kusehat_backend_id,
});

// State untuk form
const registerForm = ref({ name: '', email: '', password: '' });
const loginForm = ref({ email: '', password: '' });
const topupForm = ref({ user_id: '1', metode: 'gopay', jumlah: 10000, token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTU3NzU2ODksImlkIjoiMSJ9.C2v_OnjLV8CuNInnZ4iTRoa6_jWYZsf_wJRREbqMS5g' });
const apiResponse = ref('');

// Handlers
const handleRegister = async () => {
  apiResponse.value = 'Loading...';
  const result = await backend.register(registerForm.value);
  handleResult(result);
};

const handleLogin = async () => {
  apiResponse.value = 'Loading...';
  const result = await backend.login(loginForm.value);
  handleResult(result);
};

const handleTopup = async () => {
  apiResponse.value = 'Loading...';
  // Pastikan jumlah adalah BigInt (Nat di Motoko) jika perlu, tapi Number biasanya cukup untuk Candid
  const args = {
    ...topupForm.value,
    jumlah: BigInt(topupForm.value.jumlah)
  };
  const result = await backend.topup(args);
  handleResult(result);
};

const handleResult = (result) => {
    if (result.Ok) {
        apiResponse.value = result.Ok;
    } else if (result.Err) {
        apiResponse.value = `Error: ${result.Err}`;
    }
}
</script>

<style>
body { font-family: sans-serif; background-color: #f4f4f9; color: #333; }
.container { max-width: 600px; margin: 2rem auto; padding: 1rem; }
.card { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #ccc; box-sizing: border-box; }
textarea { height: 80px; resize: vertical; }
button { width: 100%; padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background-color: #0056b3; }
.response-card { margin-top: 1.5rem; padding: 1rem; background: #e9ecef; border-radius: 8px; }
pre { white-space: pre-wrap; word-wrap: break-word; }
</style>