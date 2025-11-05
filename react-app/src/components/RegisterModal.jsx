import { useMemo, useState } from "react";
import axios from "axios";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export default function RegisterModal({ onClose, onSuccess }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isNameValid = useMemo(() => username.trim().length >= 3, [username]);
  const isEmailValid = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), [email]);
  const isPasswordValid = useMemo(() => password.length >= 6, [password]);
  const canSubmit = isNameValid && isEmailValid && isPasswordValid && !submitting;

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await axios.post("/auth/register", { username, email, password }, { withCredentials: true });
      alert("User registered");
      onClose();
      if (onSuccess) onSuccess();
    } catch (err) {
      const msg = err.response?.data?.detail || "Registration failed";
      setError(msg);
    }
    setSubmitting(false);
  };

  const handleGoogle = async () => {
    try {
      const res = await axios.get(`${API_URL}/auth/google/login`);
      const url = res.data.auth_url;
      if (url) window.location.href = url;
    } catch (err) {
      alert("Google auth init failed");
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-[100] overflow-y-auto">
      <div className="min-h-full flex items-center justify-center p-4 py-8">
        <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-[420px] relative">
        <h2 className="text-2xl font-semibold mb-5 text-gray-900">Register</h2>
        {error && <div className="mb-3 text-sm text-red-600">{error}</div>}
        <form onSubmit={handleRegister} className="flex flex-col gap-3">
          <label htmlFor="reg-name" className="text-sm text-gray-700">Username</label>
          <input
            id="reg-name"
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            readOnly={false}
            className={`w-full border p-2 rounded-lg bg-white text-gray-900 placeholder-gray-500 ${username && !isNameValid ? 'border-red-500' : 'border-gray-300'}`}
          />
          <label htmlFor="reg-email" className="text-sm text-gray-700">Email</label>
          <input
            id="reg-email"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
            readOnly={false}
            className={`w-full border p-2 rounded-lg bg-white text-gray-900 placeholder-gray-500 ${email && !isEmailValid ? 'border-red-500' : 'border-gray-300'}`}
          />
          <label htmlFor="reg-password" className="text-sm text-gray-700">Password</label>
          <div className="relative">
            <input
              id="reg-password"
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              readOnly={false}
              className={`w-full border p-2 pr-12 rounded-lg bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-pink-400 ${password && !isPasswordValid ? 'border-red-500' : 'border-gray-300'}`}
            />
            <button type="button" onClick={() => setShowPassword(s => !s)} className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-gray-600 select-none">{showPassword ? 'Hide' : 'Show'}</button>
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className={`rounded-lg py-2 mt-2 ${canSubmit ? 'bg-pink-500 hover:bg-pink-600 text-white' : 'bg-pink-300 text-white cursor-not-allowed'}`}
          >
            {submitting ? 'Registering...' : 'Register'}
          </button>
          <button
            type="button"
            onClick={() => { window.location.href = `${API_URL}/auth/google/login?redirect=1`; }}
            className="border border-gray-300 text-gray-700 rounded-lg py-2 hover:bg-gray-100"
          >
            Continue with Google
          </button>
        </form>
        <button
          onClick={onClose}
          className="absolute top-2 right-2 text-gray-500 hover:text-black"
        >
          ✖
        </button>
      </div>
      </div>
    </div>
  );
}
