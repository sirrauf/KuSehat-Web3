<template>
  <div>
    <HeaderNav 
      :is-logged-in="!!user" 
      @show-section="showSection" 
      @logout="handleLogout"
    />

    <main class="container">
      <PricingSection v-show="activeSection === 'pricing'" />
      <LoginSection v-show="activeSection === 'login'" @login-submit="handleLogin" />
      <RegisterSection v-show="activeSection === 'register'" @register-submit="handleRegister" />
      <DiseasePriceSection v-show="activeSection === 'diseaseprice'" />

      <DashboardSection 
        v-if="user" 
        v-show="activeSection === 'dashboard'" 
        :user="user" 
        @diagnose-submit="handleDiagnosis" 
      />
      </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// Impor semua komponen Anda
import HeaderNav from '~/components/HeaderNav.vue';
import PricingSection from '~/components/PricingSection.vue';
import LoginSection from '~/components/LoginSection.vue';
import RegisterSection from '~/components/RegisterSection.vue';
import DashboardSection from '~/components/DashboardSection.vue';
import DiseasePriceSection from '~/components/DiseasePriceSection.vue';

// Impor canister setelah dfx generate
// import { kusehat_backend } from 'declarations/kusehat_backend';

const activeSection = ref('pricing');
const user = ref(null); // Akan diisi data dari API setelah login

const showSection = (sectionId) => {
  activeSection.value = sectionId;
};

// --- Handlers ---
const handleLogin = async (loginData) => {
  console.log('Data login diterima dari komponen:', loginData);
  try {
    // Ganti dengan pemanggilan canister asli
    // const response = await kusehat_backend.login(loginData.email, loginData.password);
    // const result = JSON.parse(new TextDecoder().decode(new Uint8Array(response[0])));
    // if(result.user) {
    //    user.value = await fetchUserData(); // Panggil fungsi untuk mengambil data user lengkap
    //    showSection('dashboard');
    // } else {
    //    alert('Login gagal: ' + result.error);
    // }
    
    // --- Kode Placeholder ---
    alert(`Login berhasil untuk ${loginData.email} (Placeholder)`);
    user.value = {
        nama: 'User Exodia',
        saldo: '150000.00',
        is_premium: true,
        uploads_today: 1,
        riwayat_penukaran: [
            { Tanggal: '2025-08-01 10:30', Tujuan: 'deteksi', Reward: '0.00', Gambar: 'sample1.jpg' },
            { Tanggal: '2025-07-30 15:00', Tujuan: 'data_ai', Reward: '200000.00', Gambar: 'sample2.jpg' },
        ]
    };
    showSection('dashboard');
    // --- Akhir Placeholder ---
  } catch (error) {
    console.error("Login failed:", error);
    alert("Terjadi kesalahan saat login!");
  }
};

const handleRegister = async (registerData) => {
    console.log('Data registrasi diterima:', registerData);
    alert(`Registrasi untuk ${registerData.email} berhasil (Placeholder)`);
    showSection('login');
};

const handleLogout = () => {
  user.value = null;
  showSection('pricing');
  alert("Anda telah logout.");
};

const handleDiagnosis = (file) => {
    console.log("File untuk diagnosa diterima:", file);
    alert(`Memproses file ${file.name} untuk diagnosa... (Placeholder)`);
};

onMounted(() => {
  // Anda bisa menambahkan logika untuk memeriksa sesi login di sini
  if (!user.value) {
      showSection('pricing');
  }
});
</script>

<style>
/* Impor CSS global Anda */
@import '~/assets/main.css';

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}
</style>