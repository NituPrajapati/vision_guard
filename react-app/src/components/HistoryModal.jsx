import { useEffect, useState } from "react";
import axios from "axios";
import { FaDownload, FaTimes, FaTrash } from "react-icons/fa";

export default function HistoryModal({ onClose }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingItemId, setDeletingItemId] = useState(null);
  const [showDeleteItemConfirm, setShowDeleteItemConfirm] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError("");
    axios
      .get("/history", { withCredentials: true })
      .then((res) => setHistory(res.data || []))
      .catch((err) => {
        console.error("Failed to fetch history:", err);
        setError(err.response?.data?.detail || "Failed to fetch history");
        setHistory([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const downloadResult = async (downloadId, filename) => {
    try {
      const response = await axios.get(`/download/${downloadId}`, {
        responseType: 'blob',
        withCredentials: true
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `detected_${filename}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Download failed");
    }
  };

  const getImageUrl = (resultUrl, resultPath) => {
    // Get API URL from environment variable
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";
    
    // Prefer result_url (Cloudinary) over result_path (local fallback)
    const url = resultUrl || resultPath;
    if (!url) return "";
    
    // If it's already a full URL (Cloudinary), use it directly
    if (url.startsWith("http://") || url.startsWith("https://")) {
      return url;
    }
    
    // If it starts with /results/, it's a backend static file path
    if (url.startsWith("/results/")) {
      return `${API_URL}${url}`;
    }
    
    // If it starts with /, prepend backend URL
    if (url.startsWith("/")) {
      return `${API_URL}${url}`;
    }
    
    // Otherwise, prepend backend URL
    return `${API_URL}/${url}`;
  };

  const handleDeleteAll = async () => {
    setDeleting(true);
    try {
      await axios.delete("/history/delete-all", { withCredentials: true });
      setHistory([]);
      setShowDeleteConfirm(false);
      // Optionally show success message
    } catch (err) {
      console.error("Failed to delete history:", err);
      setError(err.response?.data?.detail || "Failed to delete history");
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteItem = async (downloadId) => {
    setDeletingItemId(downloadId);
    try {
      await axios.delete(`/history/${downloadId}`, { withCredentials: true });
      // Remove the item from the history state
      setHistory(history.filter(h => h.download_id !== downloadId));
      setShowDeleteItemConfirm(null);
    } catch (err) {
      console.error("Failed to delete item:", err);
      setError(err.response?.data?.detail || "Failed to delete item");
    } finally {
      setDeletingItemId(null);
    }
  };

  // Close modal when clicking outside
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && !showDeleteConfirm && !showDeleteItemConfirm) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col relative">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white rounded-t-xl z-10">
          <h2 className="text-2xl font-bold text-gray-800">Detection History</h2>
          <div className="flex items-center gap-4">
            {/* Delete All Button - Center */}
            {history.length > 0 && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 bg-red-500 text-white rounded-lg shadow-md hover:bg-red-600 transition-colors flex items-center gap-2"
                title="Delete all history"
              >
                <FaTrash size={14} />
                <span className="text-sm font-medium">Delete All</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full p-2 transition-colors"
              title="Close"
            >
              <FaTimes size={20} />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500 mb-2"></div>
                <p className="text-gray-600">Loading history...</p>
              </div>
            </div>
          )}
          
          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
          
          {!loading && history.length === 0 && !error && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">No history available</p>
              <p className="text-gray-400 text-sm mt-2">Your detection history will appear here</p>
            </div>
          )}
          
          {!loading && history.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {history.map((h, i) => {
                const isVideo = h.detection_type === 'video';
                return (
                  <div 
                    key={i} 
                    className="relative border-2 border-gray-200 rounded-lg p-4 bg-gradient-to-br from-gray-50 to-white hover:shadow-lg transition-shadow duration-200"
                  >
                    {/* Action Buttons - Top Right */}
                    <div className="absolute top-4 right-4 flex gap-2 z-10">
                      {/* Download Button */}
                      <button
                        title="Download"
                        onClick={() => downloadResult(h.download_id, h.filename)}
                        className="p-2 rounded-full bg-pink-500 text-white shadow-md hover:bg-pink-600 transition-colors"
                      >
                        <FaDownload size={16} />
                      </button>
                      {/* Delete Button */}
                      <button
                        title="Delete"
                        onClick={() => setShowDeleteItemConfirm(h.download_id)}
                        className="p-2 rounded-full bg-red-500 text-white shadow-md hover:bg-red-600 transition-colors"
                      >
                        <FaTrash size={16} />
                      </button>
                    </div>
                    
                    {/* File Info */}
                    <div className="mb-3 pr-20">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-sm text-gray-800 truncate">{h.filename}</p>
                        {isVideo && (
                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
                            VIDEO
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {h.timestamp ? new Date(h.timestamp).toLocaleString() : 'No date'}
                      </p>
                      {h.labels && Array.isArray(h.labels) && h.labels.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {h.labels.map((label, idx) => (
                            <span 
                              key={idx}
                              className="px-2 py-1 text-xs bg-pink-100 text-pink-700 rounded-full"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    {/* Detection Result (Image or Video) */}
                    <div className="bg-gray-100 rounded-lg overflow-hidden">
                      {isVideo ? (
                        <video
                          src={getImageUrl(h.result_url, h.result_path)}
                          controls
                          className="w-full h-auto max-h-80 object-contain rounded-lg"
                          preload="metadata"
                        >
                          Your browser does not support the video tag.
                        </video>
                      ) : (
                        <img
                          src={getImageUrl(h.result_url, h.result_path)}
                          alt={`Detection result for ${h.filename}`}
                          className="w-full h-auto max-h-80 object-contain rounded-lg"
                          onError={(e) => {
                            console.error("Failed to load image:", h.result_url || h.result_path);
                            e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23ddd' width='400' height='300'/%3E%3Ctext fill='%23999' font-family='sans-serif' font-size='18' dy='10.5' font-weight='bold' x='50%25' y='50%25' text-anchor='middle'%3EImage not found%3C/text%3E%3C/svg%3E";
                          }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>

      {/* Confirmation Dialog for Delete All */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-800 mb-2">Delete All History?</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete all your detection history? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAll}
                disabled={deleting}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {deleting ? (
                  <>
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <FaTrash size={14} />
                    <span>Delete All</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog for Delete Single Item */}
      {showDeleteItemConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-800 mb-2">Delete This Item?</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this detection? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteItemConfirm(null)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                disabled={deletingItemId !== null}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteItem(showDeleteItemConfirm)}
                disabled={deletingItemId !== null}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {deletingItemId === showDeleteItemConfirm ? (
                  <>
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <FaTrash size={14} />
                    <span>Delete</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
