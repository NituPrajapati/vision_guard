import './App.css'
import { FiLogIn } from "react-icons/fi";
import { FaFileAlt } from "react-icons/fa";
import { BsFillWebcamFill } from "react-icons/bs";
import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import LoginModal from "./components/LoginModal";
import RegisterModal from "./components/RegisterModal";
import HistoryModal from "./components/HistoryModal";

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

  // Send cookies with every request
  axios.defaults.withCredentials = true;

  const fetchUser = async () => {
    try {
      const res = await axios.get("/auth/user", { withCredentials: true });
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
      const res = await axios.post("http://localhost:5000/detect", formData, {
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
    await axios.post("http://localhost:5000/live/start", { cam_index: 0 });
    setIsLive(true);   // show the live stream
  } catch (err) {
    console.error(err);
  }
  setLoading(false);
};

const handleStopLive = async () => {
  try {
    await axios.post("http://localhost:5000/live/stop");
    setIsLive(false);  // hide the live stream
  } catch (err) {
    console.error(err);
  }
};



  return (
    <>
      <div className='min-h-screen h-full bg-gradient-to-b from-gray-800 to-gray-700 overflow-x-hidden'>
        {/* Navbar */}
        <nav className='relative top-0 w-full h-22 shadow-2xl justify-between item-center flex text-white'>
          <p className='text-3xl p-6 tracking-wider'>
            VISION <span className='text-pink-500'>GUARD</span>
          </p>
          <div className="flex items-center gap-6 p-2">
            {!user ? (
              <>
                <button className="flex items-center gap-2 text-xl" onClick={() => setShowLogin(true)}>Login</button>
                <span className="w-px h-6 bg-white"></span>
                <button className="flex items-center gap-2 text-xl" onClick={() => setShowRegister(true)}>
                  Register <FiLogIn size={24} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setShowHistory(true)}
                  className="px-3 py-1 bg-gray-600 rounded-lg hover:bg-gray-500 text-sm"
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
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-2 z-50">
                      <div className="px-4 py-2 border-b border-gray-200">
                        <p className="text-sm font-semibold text-gray-900">{user.name || 'User'}</p>
                        <p className="text-xs text-gray-500">Logged in</p>
                      </div>
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 transition-colors"
                      >
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
            {showLogin && <LoginModal onClose={() => setShowLogin(false)} onSuccess={() => { setShowLogin(false); fetchUser(); setToast('Logged in successfully'); setTimeout(()=>setToast(''), 2500); }} />}
            {showRegister && <RegisterModal onClose={() => setShowRegister(false)} onSuccess={() => { setShowRegister(false); fetchUser(); setToast('Registered successfully'); setTimeout(()=>setToast(''), 2500); }} />}
            {showHistory && <HistoryModal onClose={() => setShowHistory(false)} />}
          </div>
        </nav>

        {toast && (
          <div className="fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded shadow-lg z-50">{toast}</div>
        )}

        {/* Quote */}
        <div className='flex text-center justify-center m-8'>
          <p className="text-6xl font-serif text-center pt-20 bg-gradient-to-r from-pink-500 to-cyan-400 bg-clip-text text-transparent">
            “Every <span className="italic">object</span> has a story — we <br/> help you see it.”
          </p>
        </div>

        {/* Video background */}
        <div className="flex items-center justify-center">
          <video autoPlay loop muted className="w-1/2 h-[400px] object-cover rounded-2xl shadow-2xl">
            <source src="Recording 2025-09-07 081146.mp4" type="video/mp4"  />
          </video>
        </div>

        {/* Buttons */}
        <div className="flex gap-6 items-center justify-center m-12">
          {/* Live Detection */}
          <button
            onClick={handleLiveDetection}
            className="px-6 py-3 bg-pink-500 hover:bg-pink-600 rounded-xl shadow-lg flex transition duration-300 hover:scale-105 hover:shadow-[#6b8d8d]"
          >
            Live Detection <FaFileAlt size={20}/>
          </button>
          <button 
            onClick={handleStopLive}
            className="px-6 py-3 bg-gray-600 rounded-xl"
          >
            Stop Live Detection
          </button>
          {/* Static Detection */}
          <label className="px-6 py-3 bg-[#4a5151] hover:bg-[#6b8d8d] rounded-xl shadow-lg flex transition duration-300 hover:scale-105 hover:shadow-pink-500/50 cursor-pointer">
            Static Detection <BsFillWebcamFill size={20}/>
            <input type="file" accept="image/*,video/*" onChange={handleStaticDetection} className="hidden" />
          </label>
        </div>

        {/* Results */}
        <div className="flex flex-col items-center mt-6">
          {loading && (
            <div className="text-center mb-6 w-full">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500 mb-2"></div>
              <p className="text-white text-lg">Processing...</p>
            </div>
          )}
          <div className="flex flex-wrap justify-center gap-4">
            {isLive && (
            <img
              src="http://localhost:5000/live/stream"
              alt="Live Detection Stream"
              className="w-1/2 rounded-xl shadow-xl m-2"
            />
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
                  fullUrl = `http://localhost:5000${url}`; // Backend static file path
                } else {
                  fullUrl = `http://localhost:5000/${url.startsWith('/') ? url.slice(1) : url}`;
                }
              }
            
              return fullUrl ? (
                type === 'video' ? (
                  <video
                    key={index}
                    src={fullUrl}
                    controls
                    className="max-w-xl w-1/2 rounded-xl shadow-xl m-2"
                  >
                    Your browser does not support the video tag.
                  </video>
                ) : (
                  <img
                    key={index}
                    src={fullUrl}
                    alt="Detection Result"
                    className="max-w-xl w-1/2 rounded-xl shadow-xl m-2"
                  />
                )
              ) : null;
            })}
          </div>
        </div>

        <footer className="text-center mt-10 p-4 bg-[#4a5151] text-white text-sm tracking-wide">
          @2025.
        </footer>
      </div>
    </>
  )
}

export function Login({ setToken }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const handleSubmit = async e => {
    e.preventDefault();
    const res = await axios.post('http://localhost:5000/api/login', {username, password});
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
