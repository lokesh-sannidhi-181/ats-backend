import { useState } from "react";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [mode, setMode] = useState("single");
  const [file, setFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState(null);
  const [bulkResults, setBulkResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const handleFileChange = (e) => { setFile(e.target.files[0]); setResult(null); };
  const handleFilesChange = (e) => { setFiles(Array.from(e.target.files).slice(0, 50)); setBulkResults(null); };

  const handleSingleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("job_description", jobDescription);
    try {
      const res = await axios.post(`${API_BASE_URL}/analyze`, formData);
      setResult(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const handleBulkAnalyze = async () => {
    if (!files.length) return;
    setLoading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    formData.append("job_description", jobDescription);
    try {
      const res = await axios.post(`${API_BASE_URL}/analyze-bulk`, formData);
      setBulkResults(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const scoreClass = (s) => s >= 70 ? "score-high" : s >= 40 ? "score-medium" : "score-low";
  const medal = (r) => r === 1 ? "🥇" : r === 2 ? "🥈" : r === 3 ? "🥉" : `#${r}`;
  const levelColor = (l) => l === "Senior" ? "#22c55e" : l === "Mid-Level" ? "#f59e0b" : "#60a5fa";

  return (
    <div className="container">
<div className="header">
  <h1>
    <span style={{ WebkitTextFillColor: 'initial' }}>🎯 </span>
    ATS Resume Checker
  </h1>
  <p>AI-powered resume analysis</p>
</div>
      {/* Mode Toggle */}
      <div className="mode-toggle">
        <button className={`mode-btn ${mode === "single" ? "active" : ""}`}
          onClick={() => { setMode("single"); setResult(null); setBulkResults(null); }}>
          📄 Single Resume
        </button>
        <button className={`mode-btn ${mode === "bulk" ? "active" : ""}`}
          onClick={() => { setMode("bulk"); setResult(null); setBulkResults(null); }}>
          📦 Bulk Analysis (upto 50)
        </button>
      </div>

      {/* Upload */}
      <label className="upload-card">
        <input type="file" accept=".pdf,.docx"
          multiple={mode === "bulk"}
          onChange={mode === "single" ? handleFileChange : handleFilesChange} />
        <div className="upload-icon">{mode === "single" ? "📄" : "📦"}</div>
        <h3>{mode === "single" ? "Click to upload Resume" : "Click to upload up to 50 Resumes"}</h3>
        <p>Supports PDF and DOCX</p>
        {mode === "single" && file && <p className="file-selected">✅ {file.name}</p>}
        {mode === "bulk" && files.length > 0 && <p className="file-selected">✅ {files.length} file(s) selected</p>}
      </label>

      {/* Job Description */}
      <div className="jd-card">
        <h3>📋 Job Description <span className="optional">(optional but recommended)</span></h3>
        <textarea className="jd-textarea"
          placeholder="Paste the job description here for match scoring and gap analysis..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          rows={6} />
      </div>

      <button className="analyze-btn"
        onClick={mode === "single" ? handleSingleAnalyze : handleBulkAnalyze}
        disabled={loading || (mode === "single" ? !file : !files.length)}>
        {loading ? "Analyzing..." : mode === "single" ? "Analyze Resume" : `Analyze ${files.length} Resumes`}
      </button>

      {loading && <div className="loading">🤖 Analyzing resumes with NLP...</div>}

      {/* ── Single Result ── */}
      {result && mode === "single" && (
        <>
          <div className="verdict-banner">
            <span>📊 {result.overall_verdict}</span>
          </div>

          <div className="scores-row">
            <div className="score-card">
              <div className={`score-circle ${scoreClass(result.ats_score)}`}>{result.ats_score}</div>
              <div className="score-label">ATS Score</div>
              <div className="score-sublabel">Overall Quality</div>
            </div>
            {jobDescription && (
              <div className="score-card">
                <div className={`score-circle ${scoreClass(result.match_score)}`}>{result.match_score}</div>
                <div className="score-label">Match Score</div>
                <div className="score-sublabel">JD Alignment</div>
              </div>
            )}
            <div className="score-card">
              <div className="score-circle" style={{
                borderColor: levelColor(result.experience_level),
                color: levelColor(result.experience_level),
                background: "#0f172a"
              }}>
                {result.experience_level === "Senior" ? "Sr" : result.experience_level === "Mid-Level" ? "Mid" : "Jr"}
              </div>
              <div className="score-label">Level</div>
              <div className="score-sublabel">{result.experience_level}</div>
            </div>
          </div>

          <div className="section-card">
            <h3>📬 Contact Info Detected</h3>
            <div className="contact-grid">
              <div className={`contact-item ${result.contact_info.email ? "found" : "missing"}`}>
                📧 {result.contact_info.email || "Email not found"}
              </div>
              <div className={`contact-item ${result.contact_info.phone ? "found" : "missing"}`}>
                📱 {result.contact_info.phone || "Phone not found"}
              </div>
              <div className={`contact-item ${result.contact_info.linkedin ? "found" : "missing"}`}>
                💼 {result.contact_info.linkedin || "LinkedIn not found"}
              </div>
              <div className={`contact-item ${result.contact_info.github ? "found" : "missing"}`}>
                🐙 {result.contact_info.github || "GitHub not found"}
              </div>
            </div>
          </div>

          <div className="section-card">
            <h3>📑 Resume Sections</h3>
            <div style={{ marginBottom: 8 }}>
              {result.sections_found.map((s, i) => (
                <span key={i} className="tag tag-skill">✅ {s}</span>
              ))}
            </div>
            {result.sections_missing.length > 0 && (
              <div>
                {result.sections_missing.map((s, i) => (
                  <span key={i} className="tag tag-missing">❌ {s}</span>
                ))}
              </div>
            )}
          </div>

          <div className="section-card">
            <h3>🧠 Skills by Category</h3>
            {Object.entries(result.skill_breakdown).map(([cat, skills]) =>
              skills.length > 0 ? (
                <div key={cat} className="skill-category">
                  <div className="skill-cat-label">{cat.replace(/_/g, " ").toUpperCase()}</div>
                  <div>{skills.map((s, i) => <span key={i} className="tag tag-skill">{s}</span>)}</div>
                </div>
              ) : null
            )}
          </div>

          <div className="section-card">
            <h3>⚡ Action Verbs Used ({result.action_verbs_used.length})</h3>
            {result.action_verbs_used.length > 0
              ? result.action_verbs_used.map((v, i) => <span key={i} className="tag tag-verb">{v}</span>)
              : <p className="empty-msg">No strong action verbs found — add words like Led, Built, Optimized</p>
            }
          </div>

          <div className="section-card">
            <h3>📈 Keyword Density</h3>
            <div className="density-bar-wrap">
              <div className="density-bar" style={{ width: `${Math.min(100, result.keyword_density * 10)}%` }} />
            </div>
            <p className="density-label">{result.keyword_density}% keyword density</p>
          </div>

          {jobDescription && (
            <>
              <div className="section-card">
                <h3>✅ Matched Requirements</h3>
                {result.matched_requirements.length > 0
                  ? result.matched_requirements.map((r, i) => <span key={i} className="tag tag-skill">{r}</span>)
                  : <p className="empty-msg">No matches found</p>}
              </div>
              <div className="section-card">
                <h3>🚫 Missing Requirements</h3>
                {result.missing_requirements.length > 0
                  ? result.missing_requirements.map((r, i) => <span key={i} className="tag tag-missing">{r}</span>)
                  : <p className="empty-msg">All requirements matched!</p>}
              </div>
            </>
          )}

          <div className="section-card">
            <h3>❌ Missing ATS Keywords</h3>
            {result.missing_keywords.map((k, i) => <span key={i} className="tag tag-missing">{k}</span>)}
          </div>

          <div className="section-card">
            <h3>💪 Strengths</h3>
            {result.strengths.map((s, i) => (
              <div key={i} className="list-item"><div className="dot dot-green" /><span>{s}</span></div>
            ))}
          </div>

          <div className="section-card">
            <h3>⚠️ Weaknesses</h3>
            {result.weaknesses.map((w, i) => (
              <div key={i} className="list-item"><div className="dot dot-red" /><span>{w}</span></div>
            ))}
          </div>

          <div className="section-card">
            <h3>💡 Suggestions</h3>
            {result.suggestions.map((s, i) => (
              <div key={i} className="list-item"><div className="dot dot-blue" /><span>{s}</span></div>
            ))}
          </div>
        </>
      )}

      {/* ── Bulk Results ── */}
      {bulkResults && mode === "bulk" && (
        <div className="section-card">
          <h3>🏆 Candidate Rankings — {bulkResults.total} Resumes Analyzed</h3>
          <div className="bulk-table">
            <div className="bulk-header">
              <span>Rank</span>
              <span>Candidate</span>
              <span>Level</span>
              <span>ATS</span>
              {jobDescription && <span>Match</span>}
              <span>Skills</span>
              <span>Verdict</span>
            </div>

            {bulkResults.candidates.map((c, i) => (
              <div key={i}>
                {/* Main Row */}
                <div
                  className={`bulk-row ${c.rank <= 3 ? "top-rank" : ""}`}
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  style={{ cursor: "pointer" }}
                >
                  <span className="rank-medal">{medal(c.rank)}</span>
                  <span className="candidate-name">{c.filename.replace(/\.(pdf|docx)$/i, "")}</span>
                  <span style={{ color: levelColor(c.experience_level), fontSize: "0.85rem", fontWeight: 600 }}>
                    {c.experience_level}
                  </span>
                  <span className={`score-badge ${scoreClass(c.ats_score)}`}>{c.ats_score}</span>
                  {jobDescription && (
                    <span className={`score-badge ${scoreClass(c.match_score)}`}>{c.match_score}</span>
                  )}
                  <span className="skills-count">{c.skills_found.length} skills</span>
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                    {c.overall_verdict.split("—")[0]}
                  </span>
                </div>

                {/* Expanded Detail */}
                {expanded === i && (
                  <div className="expanded-row">
                    <div className="exp-section">
                      <strong>📊 VERDICT</strong>
                      <div className="verdict-banner" style={{ marginBottom: 0 }}>
                        {c.overall_verdict}
                      </div>
                    </div>

                    <div className="exp-section">
                      <strong>🛠 SKILLS FOUND ({c.skills_found.length})</strong>
                      <div>
                        {c.skills_found.length > 0
                          ? c.skills_found.map((s, j) => (
                              <span key={j} className="tag tag-skill">{s}</span>
                            ))
                          : <p className="empty-msg">No skills detected</p>
                        }
                      </div>
                    </div>

                    <div className="exp-section">
                      <strong>🧠 SKILLS BY CATEGORY</strong>
                      {Object.entries(c.skill_breakdown).map(([cat, skills]) =>
                        skills.length > 0 ? (
                          <div key={cat} className="skill-category">
                            <div className="skill-cat-label">{cat.replace(/_/g, " ")}</div>
                            <div>
                              {skills.map((s, j) => (
                                <span key={j} className="tag tag-skill">{s}</span>
                              ))}
                            </div>
                          </div>
                        ) : null
                      )}
                    </div>

                    {c.skill_gap.length > 0 && (
                      <div className="exp-section">
                        <strong>🚫 SKILL GAP</strong>
                        <div>
                          {c.skill_gap.slice(0, 8).map((s, j) => (
                            <span key={j} className="tag tag-missing">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="exp-section">
                      <strong>⚡ ACTION VERBS ({c.action_verbs_used.length})</strong>
                      <div>
                        {c.action_verbs_used.length > 0
                          ? c.action_verbs_used.map((v, j) => (
                              <span key={j} className="tag tag-verb">{v}</span>
                            ))
                          : <p className="empty-msg">No strong action verbs found</p>
                        }
                      </div>
                    </div>

                    <div className="exp-section">
                      <strong>📑 SECTIONS FOUND</strong>
                      <div>
                        {c.sections_found.map((s, j) => (
                          <span key={j} className="tag tag-skill">✅ {s}</span>
                        ))}
                      </div>
                    </div>

                    {c.matched_requirements.length > 0 && (
                      <div className="exp-section">
                        <strong>✅ MATCHED REQUIREMENTS</strong>
                        <div>
                          {c.matched_requirements.slice(0, 8).map((s, j) => (
                            <span key={j} className="tag tag-skill">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {c.missing_requirements.length > 0 && (
                      <div className="exp-section">
                        <strong>🚫 MISSING REQUIREMENTS</strong>
                        <div>
                          {c.missing_requirements.slice(0, 6).map((s, j) => (
                            <span key={j} className="tag tag-missing">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="exp-section">
                      <strong>💡 SUGGESTIONS</strong>
                      {c.suggestions.map((s, j) => (
                        <div key={j} className="list-item">
                          <div className="dot dot-blue" />
                          <span>{s}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}