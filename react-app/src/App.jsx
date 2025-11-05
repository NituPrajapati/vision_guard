import './App.css'
import { FiLogIn } from "react-icons/fi";
import { FaFileAlt, FaGithub, FaLinkedin, FaArrowUp, FaShieldAlt, FaLock, FaClock, FaCheckCircle } from "react-icons/fa";
import { BsFillWebcamFill, BsSpeedometer2, BsEye } from "react-icons/bs";
import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import LoginModal from "./components/LoginModal";
import RegisterModal from "./components/RegisterModal";
import HistoryModal from "./components/HistoryModal";

// Get API URL from environment variable
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

function App() {
  const [resultUrls, setResultUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [user, setUser] = useState(null);
  const [toast, setToast] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Send cookies with every request
  axios.defaults.withCredentials = true;
  axios.defaults.baseURL = API_URL;

  const fetchUser = async () => {
    try {
      const res = await axios.get(`${API_URL}/auth/user`, { withCredentials: true });
      if (res.data?.username) {
        setUser({ name: res.data.username });
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  // Handle scroll to top button visibility
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showUserMenu && !event.target.closest('.user-menu-container')) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showUserMenu]);

  const handleLogout = async () => {
    try {
      await axios.post("/auth/logout", {}, { withCredentials: true });
      setUser(null);
      setShowUserMenu(false);
      setToast('Logged out successfully');
      setTimeout(() => setToast(''), 2500);
    } catch (err) {
      console.error("Logout failed:", err);
      // Clear user state even if request fails
      setUser(null);
      setShowUserMenu(false);
    }
  };


  //  Handle Static Detection (upload image/video)
  const handleStaticDetection = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/detect`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Handle response - backend returns result_urls (Cloudinary URLs) or result_paths (local fallback)
      const urls = res.data.result_urls || res.data.result_paths || [];
      const detectionType = res.data.type || 'image';
      
      // Store URLs with type information
      setResultUrls(urls.map(url => ({
        path: url,
        type: detectionType
      })));
    } catch (err) {
      console.error(err);
      setToast(err.response?.data?.detail || 'Detection failed');
      setTimeout(() => setToast(''), 3000);
    }
    setLoading(false);
    // Reset file input
    event.target.value = '';
  };

  // Handle Live Detection (webcam)
  const handleLiveDetection = async () => {
  setLoading(true);
  try {
    await axios.post(`${API_URL}/live/start`, { cam_index: 0 });
    setIsLive(true);   // show the live stream
  } catch (err) {
    console.error(err);
  }
  setLoading(false);
};

const handleStopLive = async () => {
  try {
    await axios.post(`${API_URL}/live/stop`);
    setIsLive(false);  // hide the live stream
  } catch (err) {
    console.error(err);
  }
};



  return (
    <>
      <div className='min-h-screen h-full bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 overflow-x-hidden'>
        {/* Navbar */}
        <nav className='relative top-0 w-full backdrop-blur-md bg-slate-900/80 border-b border-slate-700/50 shadow-xl justify-between item-center flex text-white sticky top-0 z-40'>
          <div className="flex items-center gap-3 p-6">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center shadow-lg">
              <BsEye className="text-white text-xl" />
            </div>
            <p className='text-2xl font-bold tracking-tight'>
              VISION <span className='bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent'>GUARD</span>
            </p>
          </div>
          <div className="flex items-center gap-4 p-2">
            {!user ? (
              <>
                <button 
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium hover:text-pink-400 transition-colors duration-200" 
                  onClick={() => setShowLogin(true)}
                >
                  Sign In
                </button>
                <button 
                  className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 rounded-lg text-sm font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105" 
                  onClick={() => setShowRegister(true)}
                >
                  Get Started <FiLogIn size={16} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setShowHistory(true)}
                  className="px-4 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105 backdrop-blur-sm"
                >
                  History
                </button>
                <div className="relative user-menu-container">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="w-10 h-10 rounded-full bg-pink-500 flex items-center justify-center text-white text-lg font-semibold hover:bg-pink-600 transition-colors cursor-pointer"
                    title={user.name || 'User'}
                  >
                    {user.name?.[0]?.toUpperCase() || 'U'}
                  </button>
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-56 bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl py-2 z-50 border border-slate-700/50">
                      <div className="px-4 py-3 border-b border-slate-700/50">
                        <p className="text-sm font-semibold text-white">{user.name || 'User'}</p>
                        <p className="text-xs text-gray-400 flex items-center gap-1 mt-1">
                          <FaCheckCircle className="text-green-400 text-xs" />
                          Active session
                        </p>
                      </div>
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
                      >
                        <span>Logout</span>
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </nav>

        {/* Modals - rendered outside navbar for proper positioning */}
        {showLogin && <LoginModal onClose={() => setShowLogin(false)} onSuccess={() => { setShowLogin(false); fetchUser(); setToast('Logged in successfully'); setTimeout(()=>setToast(''), 2500); }} />}
        {showRegister && <RegisterModal onClose={() => setShowRegister(false)} onSuccess={() => { setShowRegister(false); fetchUser(); setToast('Registered successfully'); setTimeout(()=>setToast(''), 2500); }} />}
        {showHistory && <HistoryModal onClose={() => setShowHistory(false)} />}

        {toast && (
          <div className="fixed top-20 right-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 py-3 rounded-lg shadow-2xl z-50 flex items-center gap-2 animate-slide-in-right border border-green-400/30">
            <FaCheckCircle className="text-lg" />
            <span className="font-medium">{toast}</span>
          </div>
        )}

        {/* Hero Section */}
        <div className='relative pt-8 pb-12 px-4'>
          {/* Trust Badges */}
          <div className="flex justify-center gap-6 mb-6 flex-wrap">
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 backdrop-blur-sm rounded-full border border-slate-700/50">
              <FaShieldAlt className="text-green-400" />
              <span className="text-sm text-gray-300">Secure & Private</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 backdrop-blur-sm rounded-full border border-slate-700/50">
              <BsSpeedometer2 className="text-blue-400" />
              <span className="text-sm text-gray-300">Fast Processing</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 backdrop-blur-sm rounded-full border border-slate-700/50">
              <FaLock className="text-purple-400" />
              <span className="text-sm text-gray-300">AI-Powered</span>
            </div>
          </div>

          {/* Main Heading */}
          <div className='flex text-center justify-center mb-6'>
            <div className="max-w-4xl">
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-center mb-4 leading-tight">
                <span className="bg-gradient-to-r from-pink-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
                  Advanced Object Detection
                </span>
                <br />
                <span className="text-white">Made Simple</span>
              </h1>
              <p className="text-lg md:text-xl text-gray-300 text-center mt-3 font-light">
                Every <span className="italic text-pink-400">object</span> has a story — we help you see it.
              </p>
              <p className="text-sm text-gray-400 text-center mt-2 max-w-2xl mx-auto">
                Powered by YOLO and Mobile SSD models for accurate, real-time detection
              </p>
            </div>
          </div>
        </div>

        {/* Video background */}
        <div className="flex items-center justify-center px-4 mb-12">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-pink-500 via-purple-500 to-cyan-500 rounded-3xl blur-lg opacity-30 group-hover:opacity-50 transition duration-300"></div>
            <video autoPlay loop muted className="relative w-full max-w-4xl h-[450px] object-cover rounded-3xl shadow-2xl border border-slate-700/50">
              <source src="Recording 2025-09-07 081146.mp4" type="video/mp4"  />
            </video>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4 items-center justify-center mb-12 px-4">
          {/* Live Detection */}
          <button
            onClick={handleLiveDetection}
            disabled={loading}
            className="px-8 py-4 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 rounded-xl shadow-xl flex items-center gap-3 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-pink-500/30 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-white"
          >
            <BsFillWebcamFill size={20}/> 
            <span>Start Live Detection</span>
          </button>
          <button 
            onClick={handleStopLive}
            disabled={!isLive}
            className="px-6 py-4 bg-slate-700/50 hover:bg-slate-700 rounded-xl shadow-lg transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-white border border-slate-600/50"
          >
            Stop Detection
          </button>
          {/* Static Detection */}
          <label className="px-8 py-4 bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-700 hover:to-cyan-700 rounded-xl shadow-xl flex items-center gap-3 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-cyan-500/30 cursor-pointer font-semibold text-white">
            <FaFileAlt size={20}/>
            <span>Upload Image/Video</span>
            <input type="file" accept="image/*,video/*" onChange={handleStaticDetection} className="hidden" disabled={loading} />
          </label>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto px-4 mb-12">
          <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50 hover:border-pink-500/50 transition-all duration-300 hover:scale-105">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center mb-4">
              <BsFillWebcamFill className="text-white text-xl" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Live Detection</h3>
            <p className="text-gray-400 text-sm">Real-time object detection using your webcam with instant results</p>
          </div>
          <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50 hover:border-purple-500/50 transition-all duration-300 hover:scale-105">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-600 flex items-center justify-center mb-4">
              <FaFileAlt className="text-white text-xl" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Static Detection</h3>
            <p className="text-gray-400 text-sm">Upload images or videos for precise object detection and analysis</p>
          </div>
          <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50 hover:border-cyan-500/50 transition-all duration-300 hover:scale-105">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mb-4">
              <FaClock className="text-white text-xl" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Detection History</h3>
            <p className="text-gray-400 text-sm">Access and manage all your detection results with ease</p>
          </div>
        </div>

        {/* Results */}
        <div className="flex flex-col items-center mt-6 px-4">
          {loading && (
            <div className="text-center mb-8 w-full">
              <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-pink-500 border-t-transparent mb-4"></div>
              <p className="text-white text-xl font-medium">Processing your detection...</p>
              <p className="text-gray-400 text-sm mt-2">This may take a few moments</p>
            </div>
          )}
          <div className="flex flex-wrap justify-center gap-6 max-w-7xl">
            {isLive && (
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-pink-500 to-purple-500 rounded-2xl blur-lg opacity-50"></div>
              <div className="relative bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-gray-300 font-medium">LIVE</span>
                </div>
                <img
                  src={`${API_URL}/live/stream`}
                  alt="Live Detection Stream"
                  className="w-full max-w-4xl rounded-xl shadow-2xl"
                />
              </div>
            </div>
            )}
            {resultUrls.map((item, index) => {
              const url = typeof item === 'string' ? item : item.path;
              const type = typeof item === 'string' ? 'image' : (item.type || 'image');
              // If URL is already a full URL (Cloudinary), use it directly
              // If it starts with /results/, it's a backend path - use backend URL
              // Otherwise, assume it's a relative path and prepend backend URL
              let fullUrl = '';
              if (url) {
                if (url.startsWith('http://') || url.startsWith('https://')) {
                  fullUrl = url; // Full Cloudinary URL
                } else if (url.startsWith('/results/')) {
                  fullUrl = `${API_URL}${url}`; // Backend static file path
                } else {
                  fullUrl = `${API_URL}/${url.startsWith('/') ? url.slice(1) : url}`;
                }
              }
            
              return fullUrl ? (
                <div key={index} className="relative group">
                  <div className="absolute -inset-1 bg-gradient-to-r from-pink-500 via-purple-500 to-cyan-500 rounded-2xl blur-lg opacity-30 group-hover:opacity-50 transition duration-300"></div>
                  <div className="relative bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/50">
                    {type === 'video' ? (
                      <video
                        src={fullUrl}
                        controls
                        className="w-full max-w-2xl rounded-xl shadow-2xl"
                      >
                        Your browser does not support the video tag.
                      </video>
                    ) : (
                      <img
                        src={fullUrl}
                        alt="Detection Result"
                        className="w-full max-w-2xl rounded-xl shadow-2xl"
                      />
                    )}
                    <div className="absolute top-6 right-6 bg-green-500/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-semibold text-white flex items-center gap-1">
                      <FaCheckCircle className="text-xs" />
                      Detected
                    </div>
                  </div>
                </div>
              ) : null;
            })}
          </div>
        </div>

        <footer className="text-center mt-20 p-8 bg-gradient-to-b from-slate-900 to-black text-white border-t border-slate-800/50">
          <div className="max-w-6xl mx-auto">
            {/* Social Links */}
            <div className="flex justify-center items-center gap-6 mb-4">
              <a
                href="https://www.linkedin.com/in/nitu-prajapati-9430562b1/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-white hover:text-pink-400 transition-colors duration-300 hover:scale-110 transform"
                aria-label="LinkedIn Profile"
              >
                <FaLinkedin size={24} />
                <span className="text-sm font-medium">LinkedIn</span>
              </a>
              <span className="text-gray-400">|</span>
              <a
                href="https://github.com/NituPrajapati"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-white hover:text-pink-400 transition-colors duration-300 hover:scale-110 transform"
                aria-label="GitHub Profile"
              >
                <FaGithub size={24} />
                <span className="text-sm font-medium">GitHub</span>
              </a>
            </div>
            
            {/* Documentation Links */}
            <div className="flex justify-center items-center gap-4 mb-4">
              <a
                href="https://docs.ultralytics.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-300 hover:text-pink-400 transition-colors duration-300 underline"
              >
                YOLO Documentation
              </a>
              <span className="text-gray-500">|</span>
              <a
                href="https://www.tensorflow.org/lite/models/object_detection/overview"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-300 hover:text-pink-400 transition-colors duration-300 underline"
              >
                Mobile SSD Documentation
              </a>
            </div>
            
            {/* Copyright */}
            <div className="text-sm tracking-wide text-gray-300">
              <p>© 2025 Vision Guard. All rights reserved.</p>
            </div>
          </div>
        </footer>

        {/* Scroll to Top Button */}
        {showScrollTop && (
          <button
            onClick={scrollToTop}
            className="fixed bottom-8 right-8 bg-gradient-to-br from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white p-4 rounded-full shadow-2xl transition-all duration-300 hover:scale-110 z-50 flex items-center justify-center border-2 border-white/10 hover:border-white/20 backdrop-blur-sm"
            aria-label="Scroll to top"
          >
            <FaArrowUp size={18} />
          </button>
        )}
      </div>
    </>
  )
}

export function Login({ setToken }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const handleSubmit = async e => {
    e.preventDefault();
    const res = await axios.post(`${API_URL}/api/login`, {username, password});
    setToken(res.data.token);
  };
  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input type="text" onChange={e => setUsername(e.target.value)} />Name:
        <input type="password" onChange={e => setPassword(e.target.value)} />Password:
      </div>
      <button type="submit">Login</button>
    </form>
  );
}

export default App
