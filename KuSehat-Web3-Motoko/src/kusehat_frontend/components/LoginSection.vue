<template>
  <section id="login">
    <h2>Login</h2>
    <form @submit.prevent="submitLogin">
      <label>Email:</label><br>
      <input type="email" v-model="form.email" required><br><br>
      <label>Password:</label><br>
      <input type="password" v-model="form.password" required><br><br>
      <button type="submit">Login</button>
    </form>
  </section>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['loginSubmit']);

const form = ref({
  email: '',
  password: ''
});

const submitLogin = () => {
  emit('loginSubmit', { ...form.value });
};
</script>