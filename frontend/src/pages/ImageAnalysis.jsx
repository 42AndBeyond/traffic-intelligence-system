import { useState } from "react";
import api, { API_URL } from "../api";

const COLORS = { LOW: "#16a34a", MODERATE: "#eab308", HIGH: "#dc2626" };

export default function ImageAnalysis() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSelect = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError("");
  };

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api.post("/api/image/analyze", form);
      setResult(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Analysis failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <h2>Image Analysis</h2>
      <input type="file" accept="image/*" onChange={onSelect} />
      <button onClick={analyze} disabled={!file || loading} style={{ marginLeft: 8 }}>
        {loading ? "Analyzing..." : "Analyze"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {!result && preview && <img src={preview} alt="preview" style={{ width: "100%", marginTop: 12 }} />}
      {!preview && <p>Upload a road image to begin.</p>}

      {result && (
        <>
          <img src={API_URL + result.annotated_url} alt="annotated" style={{ width: "100%", marginTop: 12 }} />

          <div style={{ margin: "12px 0", padding: 12, borderRadius: 8,
            background: COLORS[result.traffic.level], color: "white" }}>
            <b>Traffic: {result.traffic.level}</b> — {result.traffic.vehicle_count} vehicles
          </div>
          <p style={{ fontSize: 13, color: "#555" }}>{result.traffic.criteria}</p>

          <h3>Detected objects ({result.total_objects})</h3>
          <p>{Object.entries(result.counts).map(([k, v]) => `${k}: ${v}`).join(" | ")}</p>

          <h3>Risk indicators</h3>
          <p style={{ fontSize: 13, color: "#555" }}>{result.risk_note}</p>
          {result.risk_indicators.length === 0
            ? <p>No visible hazard indicators.</p>
            : <ul>{result.risk_indicators.map((r, i) => <li key={i}>{r.message}</li>)}</ul>}

          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead><tr><th>ID</th><th>Category</th><th>Confidence</th></tr></thead>
            <tbody>
              {result.detections.map((d) => (
                <tr key={d.id}><td>#{d.id}</td><td>{d.category}</td><td>{(d.confidence * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}