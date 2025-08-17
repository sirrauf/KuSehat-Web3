<template>
  <section id="register">
    <h2>Daftar Akun</h2>
    <form @submit.prevent="submitRegister">
      <label>Nama:</label><br>
      <input type="text" v-model="form.nama" required><br><br>
      <label>Email:</label><br>
      <input type="email" v-model="form.email" required><br><br>
      <label>Password:</label><br>
      <input type="password" v-model="form.password" required><br><br>
      <button type="submit">Daftar</button>
    </form>
  </section>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['registerSubmit']);

const form = ref({
  nama: '',
  email: '',
  password: ''
});

const submitRegister = () => {
  emit('registerSubmit', { ...form.value });
};
</script>