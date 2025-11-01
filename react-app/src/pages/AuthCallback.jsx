import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const error = params.get("error");
    if (error) {
      alert("Google auth failed: " + error);
      navigate("/");
      return;
    }
    if (token) {
      localStorage.setItem("token", token);
      navigate("/");
    } else {
      navigate("/");
    }
  }, [navigate]);

  return null;
}



