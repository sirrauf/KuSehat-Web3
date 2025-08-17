<template>
  <header>
    <nav>
      <a @click="$emit('showSection', 'pricing')">Pricing</a>
      <a @click="$emit('showSection', 'login')">Login</a>
      <a @click="$emit('showSection', 'register')">Daftar</a>
      <a v-if="isLoggedIn" @click="$emit('showSection', 'dashboard')">Dashboard</a>
      <a v-if="isLoggedIn" @click="$emit('showSection', 'edituser')">Ganti Data User</a>
      <a v-if="isLoggedIn" @click="$emit('showSection', 'topup')">Top Up</a>
      <a v-if="isLoggedIn" @click="$emit('showSection', 'exchange')">Tukar Gambar</a>
      <a @click="$emit('showSection', 'diseaseprice')">Harga Penukaran</a>
      <a v-if="isLoggedIn" @click="$emit('logout')">Logout</a>
    </nav>
  </header>
</template>

<script setup>
defineProps({
  isLoggedIn: Boolean
});
defineEmits(['showSection', 'logout']);
</script>