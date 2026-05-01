import { useMemo, useState } from "react";
import ImageRoiCanvas from "./components/ImageRoiCanvas";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [teachImageFile, setTeachImageFile] = useState(null);
  const [detectImageFile, setDetectImageFile] = useState(null);
  const [teachImageUrl, setTeachImageUrl] = useState("");
  const [detectImageUrl, setDetectImageUrl] = useState("");
  const [roi, setRoi] = useState(null);
  const [templateId, setTemplateId] = useState("");
  const [result, setResult] = useState(null);
  const [debugResult, setDebugResult] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [runState, setRunState] = useState("idle");
  const [runMessage, setRunMessage] = useState("Upload an inspection image to auto-run detection.");

  const shownImage = useMemo(() => detectImageUrl || teachImageUrl, [detectImageUrl, teachImageUrl]);

  const setTeachImage = (file) => {
    setTeachImageFile(file);
    setTeachImageUrl(file ? URL.createObjectURL(file) : "");
    setDetectImageFile(null);
    setDetectImageUrl("");
    setResult(null);
    setDebugResult(null);
    setRunState("idle");
    setRunMessage("Template image loaded. Draw ROI, then click Teach ROI.");
  };

  const runDetect = async ({ debug = false, fileOverride = null } = {}) => {
    const file = fileOverride || detectImageFile;
    if (!file) return;
    setIsBusy(true);
    setRunState("running");
    setRunMessage(debug ? "Running debug inspection..." : "Running automatic inspection...");
    try {
      const form = new FormData();
      form.append("image", file);
      const query = templateId ? `?template_id=${encodeURIComponent(templateId)}` : "";
      const endpoint = debug ? "/detect/debug" : "/detect";
      const res = await fetch(`${API_BASE}${endpoint}${query}`, {
        method: "POST",
        body: form
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Inspection failed");
      setResult(json);
      setDebugResult(debug ? (json.debug || null) : null);
      setRunState("done");
      setRunMessage(
        `${debug ? "Debug" : "Auto"} inspection completed in ${json.processing_time_ms} ms (${json.status}).`
      );
    } catch (error) {
      setRunState("error");
      setRunMessage(error.message || "Inspection failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const setDetectImage = async (file) => {
    setDetectImageFile(file);
    setDetectImageUrl(file ? URL.createObjectURL(file) : "");
    setResult(null);
    setDebugResult(null);
    if (!file) return;
    await runDetect({ debug: false, fileOverride: file });
  };

  const teach = async () => {
    if (!teachImageFile || !roi) return;
    setIsBusy(true);
    try {
      const form = new FormData();
      form.append("image", teachImageFile);
      form.append("x", String(roi.x));
      form.append("y", String(roi.y));
      form.append("width", String(roi.width));
      form.append("height", String(roi.height));

      const res = await fetch(`${API_BASE}/teach`, {
        method: "POST",
        body: form
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Teach failed");
      setTemplateId(json.template_id);
      setRunState("done");
      setRunMessage(`Template saved: ${json.template_id}`);
    } catch (error) {
      setRunState("error");
      setRunMessage(error.message || "Teach failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const detectDebug = async () => {
    if (!detectImageFile) {
      setRunState("error");
      setRunMessage("Upload an inspection image first.");
      return;
    }
    await runDetect({ debug: true });
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1>Vision Inspection AI Trainer</h1>
        <p>Industrial ROI-based DataMatrix inspection with auto-detect on every new image.</p>
        <div className="topbar-meta">
          <span className="meta-chip">AUTO INSPECT</span>
          <span className="meta-chip">GS1 PARSER</span>
          <span className={`meta-chip ${result?.status === "GOOD" ? "good" : result?.status === "BAD" ? "bad" : ""}`}>
            {result?.status || "IDLE"}
          </span>
        </div>
      </header>

      <section className="panel">
        <div className="layout-grid">
          <div className="controls">
            <label>
              1) Teach Image
              <input type="file" accept="image/*" onChange={(e) => setTeachImage(e.target.files?.[0])} />
            </label>
            <label>
              2) Inspection Image (auto-detect)
              <input type="file" accept="image/*" onChange={(e) => setDetectImage(e.target.files?.[0])} />
            </label>
            <label>
              Template ID (optional override)
              <input value={templateId} onChange={(e) => setTemplateId(e.target.value)} placeholder="Auto from teach" />
            </label>
            <div className="button-row">
              <button onClick={teach} disabled={!teachImageFile || !roi || isBusy}>
                Teach ROI
              </button>
              <button onClick={detectDebug} disabled={!detectImageFile || isBusy}>
                Run Debug Inspection
              </button>
            </div>
            <div className={`run-state ${runState}`}>{isBusy ? "Processing..." : runMessage}</div>
          </div>

          <ImageRoiCanvas imageUrl={shownImage} detectionBox={result?.bounding_box} onRoiChange={setRoi} />
        </div>
      </section>

      <section className="panel results">
        <h2>Inspection Result</h2>
        {!result && <p>No inspection run yet.</p>}
        {result && (
          <div className="result-grid">
            <div>
              <strong>Status:</strong> <span className={result.status === "GOOD" ? "good" : "bad"}>{result.status}</span>
            </div>
            <div>
              <strong>Decoded Data:</strong> {result.decoded_data || "N/A"}
            </div>
            <div>
              <strong>Confidence:</strong> {result.confidence_score?.toFixed(3)}
            </div>
            <div>
              <strong>Processing Time:</strong> {result.processing_time_ms} ms
            </div>
            <div className="parsed-block">
              <strong>GS1 Parsed Fields</strong>
              <div className="parsed-grid">
                <div>GTIN: {result.parsed_data?.gtin || "N/A"}</div>
                <div>Expiry Date: {result.parsed_data?.expiry_date || "N/A"}</div>
                <div>Manufacture Date: {result.parsed_data?.manufacture_date || "N/A"}</div>
                <div>Lot/Batch: {result.parsed_data?.lot_batch || "N/A"}</div>
                <div>Serial: {result.parsed_data?.serial || "N/A"}</div>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="panel results">
        <h2>Debug Inspection</h2>
        {!debugResult && <p>No debug run yet. Click "Run Debug Inspection" if needed.</p>}
        {debugResult && (
          <div className="debug-grid">
            <div>
              <strong>Match score:</strong> {debugResult.match?.score?.toFixed(3)}
            </div>
            <div>
              <strong>Padded ROI:</strong>{" "}
              {`${debugResult.padded_roi?.x}, ${debugResult.padded_roi?.y}, ${debugResult.padded_roi?.width}, ${debugResult.padded_roi?.height}`}
            </div>
            <div>
              <strong>Raw ROI decode attempts:</strong>
              <ul className="attempt-list">
                {(debugResult.decode_attempts_raw_roi || []).map((attempt, idx) => (
                  <li key={`${attempt.variant}-${idx}`}>
                    {attempt.variant} @ x{attempt.scale} - {attempt.success ? "SUCCESS" : "fail"}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <strong>Preprocessed ROI decode attempts:</strong>
              <ul className="attempt-list">
                {(debugResult.decode_attempts_preprocessed_roi || []).map((attempt, idx) => (
                  <li key={`prep-${attempt.variant}-${idx}`}>
                    {attempt.variant} @ x{attempt.scale} - {attempt.success ? "SUCCESS" : "fail"}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <strong>Full-frame fallback attempts:</strong>
              <ul className="attempt-list">
                {(debugResult.full_frame_decode_attempts || []).map((attempt, idx) => (
                  <li key={`full-${attempt.variant}-${idx}`}>
                    {attempt.variant} @ x{attempt.scale} - {attempt.success ? "SUCCESS" : "fail"}
                  </li>
                ))}
              </ul>
            </div>
            <div className="debug-images">
              {Object.entries(debugResult.artifacts || {}).map(([name, path]) => (
                <figure key={name}>
                  <figcaption>{name}</figcaption>
                  <img src={`${API_BASE}${path}`} alt={name} />
                </figure>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
