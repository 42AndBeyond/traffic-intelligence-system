import { useEffect, useState } from "react";
import api from "../api";

const COLORS = { LOW: "#16a34a", MODERATE: "#eab308", HIGH: "#dc2626" };

export default function VideoAnalysis() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    setReport(null);
    setStatus(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api.post("/api/video/upload", form);
      setJobId(r.data.job_id);
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed. Is the backend running?");
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;
    const timer = setInterval(async () => {
      try {
        const s = await api.get(`/api/video/${jobId}/status`);
        setStatus(s.data);
        if (s.data.status === "done") {
          clearInterval(timer);
          const r = await api.get(`/api/video/${jobId}/report`);
          setReport(r.data);
        } else if (s.data.status === "error") {
          clearInterval(timer);
          setError(s.data.error || "Processing failed");
        }
      } catch {
        clearInterval(timer);
        setError("Lost connection to backend");
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId]);

  const busy = uploading || (status && status.status !== "done" && status.status !== "error");

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <h2>Video Analysis</h2>
      <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={upload} disabled={!file || busy} style={{ marginLeft: 8 }}>
        {busy ? "Processing..." : "Analyze"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {!file && !report && <p>Upload a traffic video to begin.</p>}

      {status && !report && !error && (
        <div style={{ marginTop: 12 }}>
          <p>Status: {status.status} — {status.progress}%</p>
          <div style={{ background: "#333", height: 10, borderRadius: 5 }}>
            <div style={{ width: `${status.progress}%`, height: 10, borderRadius: 5, background: "#3b82f6" }} />
          </div>
        </div>
      )}

      {report && (
        <>
          <div style={{ margin: "12px 0", padding: 12, borderRadius: 8,
            background: COLORS[report.overall_density], color: "white" }}>
            <b>Overall traffic: {report.overall_density}</b>
          </div>
          <p style={{ fontSize: 13, color: "#555" }}>{report.density_criteria}</p>

          <p>
            Frames: {report.frames_processed}/{report.frames_read} | Duration: {report.duration_sec}s |
            FPS: {report.fps} | Unique objects: {report.unique_objects}
          </p>
          <p>{Object.entries(report.objects_by_category).map(([k, v]) => `${k}: ${v}`).join(" | ")}</p>

          <h3>Traffic over time</h3>
          <div style={{ display: "flex", height: 24, borderRadius: 4, overflow: "hidden" }}>
            {report.density_timeline.map((x) => (
              <div key={x.time} title={`${x.time}s — ${x.level} (${x.vehicles} vehicles)`}
                style={{ flex: 1, background: COLORS[x.level] }} />
            ))}
          </div>
          <p style={{ fontSize: 13 }}>
            LOW {report.density_summary_percent.LOW}% | MODERATE {report.density_summary_percent.MODERATE}% | HIGH {report.density_summary_percent.HIGH}%
          </p>

          <h3>Risk events</h3>
          <p>{report.risk_events.length === 0 ? "No risk events detected." : `${report.risk_events.length} events`}</p>

          <h3>Tracked objects</h3>
          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead><tr><th>ID</th><th>Category</th><th>First seen (s)</th><th>Last seen (s)</th><th>Frames</th></tr></thead>
            <tbody>
              {report.tracks.map((t) => (
                <tr key={t.id}>
                  <td>#{t.id}</td><td>{t.category}</td><td>{t.first_seen}</td><td>{t.last_seen}</td><td>{t.frames}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}