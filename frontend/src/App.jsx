import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import ImageAnalysis from "./pages/ImageAnalysis";
import VideoAnalysis from "./pages/VideoAnalysis";

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: 16, justifyContent: "center", padding: 12 }}>
        <NavLink to="/">Image</NavLink>
        <NavLink to="/video">Video</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<ImageAnalysis />} />
        <Route path="/video" element={<VideoAnalysis />} />
      </Routes>
    </BrowserRouter>
  );
}