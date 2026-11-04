import { useEffect, useState } from "react";
import api from "./api";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    api.get("/health")
      .then((r) => setStatus(r.data.status))
      .catch(() => setStatus("backend not reachable"));
  }, []);

  return <h1>Backend status: {status}</h1>;
}
