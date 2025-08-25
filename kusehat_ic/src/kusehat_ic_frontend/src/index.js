import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
// Impor 'actor' dari file deklarasi yang dibuat oleh DFX
import { kusehat_ic_backend as backend } from '../../declarations/kusehat_ic_backend';

const App = () => {
  // State untuk form
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [topupUserId, setTopupUserId] = useState('1'); // Contoh user_id
  const [topupMetode, setTopupMetode] = useState('GOPAY');
  const [topupJumlah, setTopupJumlah] = useState('10000');

  // State untuk menampilkan response dari API
  const [apiResponse, setApiResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setApiResponse('Menghubungi canister...');
    const result = await backend.register(regUsername, regPassword);
    setApiResponse(result);
    setLoading(false);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setApiResponse('Menghubungi canister...');
    const result = await backend.login(loginUsername, loginPassword);
    setApiResponse(result);
    setLoading(false);
  };

  const handleTopup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setApiResponse('Menghubungi canister...');
    // Konversi jumlah ke tipe Nat (BigInt di JavaScript)
    const result = await backend.topup(topupUserId, topupMetode, BigInt(topupJumlah));
    setApiResponse(result);
    setLoading(false);
  };

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: '600px', margin: 'auto', padding: '20px' }}>
      <h1>Kusehat IC <-> Flask API</h1>
      
      {/* --- FORM REGISTRASI --- */}
      <section style={{ marginBottom: '30px', border: '1px solid #ccc', padding: '15px', borderRadius: '8px' }}>
        <h2>Register</h2>
        <form onSubmit={handleRegister}>
          <input type="text" placeholder="Username" value={regUsername} onChange={(e) => setRegUsername(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <input type="password" placeholder="Password" value={regPassword} onChange={(e) => setRegPassword(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <button type="submit" disabled={loading}>Register</button>
        </form>
      </section>

      {/* --- FORM LOGIN --- */}
      <section style={{ marginBottom: '30px', border: '1px solid #ccc', padding: '15px', borderRadius: '8px' }}>
        <h2>Login</h2>
        <form onSubmit={handleLogin}>
          <input type="text" placeholder="Username" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <input type="password" placeholder="Password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <button type="submit" disabled={loading}>Login</button>
        </form>
      </section>

      {/* --- FORM TOP UP --- */}
      <section style={{ marginBottom: '30px', border: '1px solid #ccc', padding: '15px', borderRadius: '8px' }}>
        <h2>Top Up</h2>
        <form onSubmit={handleTopup}>
          <input type="text" placeholder="User ID" value={topupUserId} onChange={(e) => setTopupUserId(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <input type="text" placeholder="Metode (e.g., GOPAY)" value={topupMetode} onChange={(e) => setTopupMetode(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <input type="number" placeholder="Jumlah" value={topupJumlah} onChange={(e) => setTopupJumlah(e.target.value)} required style={{ width: '95%', padding: '8px', marginBottom: '10px' }}/>
          <button type="submit" disabled={loading}>Top Up</button>
        </form>
      </section>

      {/* --- AREA RESPONSE --- */}
      <section>
        <h2>API Response</h2>
        <pre style={{ backgroundColor: '#f0f0f0', padding: '15px', borderRadius: '5px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {apiResponse || 'Menunggu aksi...'}
        </pre>
      </section>
    </div>
  );
};

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);