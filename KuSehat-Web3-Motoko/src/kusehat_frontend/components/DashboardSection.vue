<template>
  <section id="dashboard">
    <div v-if="user">
      <h2>Selamat datang {{ user.nama }}</h2>
      <p><strong>Saldo Anda:</strong> IDR {{ user.saldo }}</p>
      <p v-if="user.is_premium" style="color: green; font-weight: bold;">🛡️ Paket Premium Aktif</p>
      <p v-else style="color: blue; font-weight: bold;">🔰 Paket Basic Aktif</p>
    </div>

    <h3>Riwayat Penukaran Gambar</h3>
    <div v-if="user && user.riwayat_penukaran?.length > 0">
      <table>
        <thead>
          <tr>
            <th>Tanggal</th>
            <th>Tujuan</th>
            <th>Reward</th>
            <th>Gambar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(ex, index) in user.riwayat_penukaran" :key="index">
            <td>{{ ex.Tanggal }}</td>
            <td>{{ ex.Tujuan }}</td>
            <td>IDR {{ ex.Reward }}</td>
            <td><img :src="'/path/to/uploads/' + ex.Gambar" width="50" alt="gambar tukar"></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else>Belum ada penukaran gambar.</p>

    <hr>
    
    <h3>Deteksi Penyakit Kulit dengan AI</h3>
    <form @submit.prevent="submitDiagnosis">
      <p><strong>Pilih metode deteksi:</strong></p>
      <button type="button" @click="aktifkanKamera">📷 Aktifkan Kamera</button>
      <video ref="videoPlayer" width="300" autoplay style="display: none; margin-top: 10px;"></video>
      <br><br>

      <p>Atau unggah gambar:</p>
      <input type="file" @change="handleFileSelect" accept="image/*" required><br><br>
      <button type="submit">Upload dan Diagnosa</button>
      <p v-if="user">Upload ke-{{ user.uploads_today }} dari 3</p>
    </form>
  </section>
</template>

<script setup>
import { ref } from 'vue';

defineProps({
  user: Object
});

const emit = defineEmits(['diagnoseSubmit']);
const videoPlayer = ref(null);
const selectedFile = ref(null);

const aktifkanKamera = () => {
  if (videoPlayer.value) {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        videoPlayer.value.srcObject = stream;
        videoPlayer.value.style.display = 'block';
      })
      .catch(err => alert("Kamera tidak bisa diakses: " + err));
  }
};

const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0];
};

const submitDiagnosis = () => {
  if (!selectedFile.value) {
    alert('Silakan pilih file gambar terlebih dahulu.');
    return;
  }
  emit('diagnoseSubmit', selectedFile.value);
};
</script>