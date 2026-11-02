import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Bell,
  Check,
  CheckCheck,
  ChevronRight,
  ClipboardList,
  Clock3,
  FileText,
  FlaskConical,
  HeartPulse,
  Image as ImageIcon,
  LayoutDashboard,
  LogOut,
  RefreshCw,
  Search,
  ShieldCheck,
  Upload,
  Users,
  Wifi,
  WifiOff,
  X,
  ZoomIn,
  ZoomOut,
  ExternalLink,
  Plus,
  AlertTriangle,
  LockKeyhole,
} from "lucide-react";
import { api, ApiError } from "./api";
import { enqueue, pending, remove } from "./outbox";
import type {
  Case,
  Clinical,
  Document,
  Imaging,
  Mutation,
  Order,
  SourceField,
  User,
} from "./types";
import "./styles.css";

const labels: Record<string, string> = {
  awaiting_review: "Awaiting review",
  under_review: "In review",
  awaiting_results: "Awaiting results",
  reviewed: "Review complete",
  result_received: "Result received",
  requested: "Requested",
  accepted: "Accepted",
  cancelled: "Cancelled",
};
const human = (s: string) =>
  labels[s] || s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const date = (s: string) =>
  new Date(
    s.endsWith("Z") || /[+-]\d\d:\d\d$/.test(s) ? s : s + "Z",
  ).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
function Pill({ value }: { value: string }) {
  return (
    <span className={"pill " + value.toLowerCase()}>
      <i />
      {human(value)}
    </span>
  );
}
function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">
        <Activity size={25} />
      </span>
      <div>
        Shwaas<span>AI</span>
        <small>CLINICAL WORKSPACE</small>
      </div>
    </div>
  );
}
function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login">
      <div className="login-story">
        <Brand />
        <div>
          <span className="eyebrow">FROM SCREENING TO CARE</span>
          <h1>
            Every referral.
            <br />A clear next step.
          </h1>
          <p>
            A shared workspace for the people turning community screenings into
            clinical care.
          </p>
          <div className="login-points">
            <span>
              <ClipboardList /> Review the full screening record
            </span>
            <span>
              <ImageIcon /> Keep investigations together
            </span>
            <span>
              <CheckCheck /> Close the referral loop
            </span>
          </div>
        </div>
        <small>Research prototype · Clinician decisions remain essential</small>
      </div>
      <form
        className="login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          const f = new FormData(e.currentTarget);
          try {
            onLogin(
              await api<User>("/session", {
                method: "POST",
                body: JSON.stringify({
                  username: f.get("username"),
                  password: f.get("password"),
                }),
              }),
            );
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <span className="secure-icon">
          <LockKeyhole size={24} />
        </span>
        <span className="eyebrow">WELCOME BACK</span>
        <h2>Sign in to your workspace</h2>
        <p>Use your assigned clinician account.</p>
        <label>
          Username
          <input
            name="username"
            autoComplete="username"
            required
            placeholder="Your clinician username"
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            placeholder="Enter your password"
          />
        </label>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Open clinical workspace"}
          <ArrowRight size={17} />
        </button>
        <small>
          <ShieldCheck size={14} /> Access is restricted to your facility.
        </small>
      </form>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<User | null>(null),
    [boot, setBoot] = useState(true),
    [cases, setCases] = useState<Case[]>([]),
    [selected, setSelected] = useState<Case | null>(null),
    [selectedId, setSelectedId] = useState(""),
    [view, setView] = useState("cases"),
    [tab, setTab] = useState("overview"),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all"),
    [queue, setQueue] = useState<Mutation[]>([]),
    [online, setOnline] = useState(navigator.onLine),
    [notice, setNotice] = useState(""),
    [syncing, setSyncing] = useState(false),
    [editing, setEditing] = useState(false),
    [lastSync, setLastSync] = useState(""),
    [report, setReport] = useState<any>(null);
  const running = useRef(false);
  const fetchDetail = async (id: string) => {
    setSelected(await api<Case>("/cases/" + id));
  };
  const refresh = useCallback(async () => {
    if (!user || !navigator.onLine) return;
    try {
      const result = await api<{ cases: Case[] }>("/cases?limit=500");
      setCases(result.cases);
      setLastSync(new Date().toISOString());
      if (selectedId && !editing && !queue.some((q) => q.caseId === selectedId))
        setSelected(await api<Case>("/cases/" + selectedId));
    } catch (e) {
      setNotice((e as Error).message);
    }
  }, [user, selectedId, editing, queue]);
  const reloadQueue = async () => {
    if (user) {
      const q = await pending(user.username);
      setQueue(q);
      return q;
    }
    return [];
  };
  const flush = useCallback(async () => {
    if (!user || running.current || !navigator.onLine) return;
    running.current = true;
    setSyncing(true);
    try {
      const all = await pending(user.username);
      for (const m of all) {
        if (m.blocked || all.some((x) => x.caseId === m.caseId && x.blocked))
          continue;
        try {
          await api(m.path, { method: "POST", body: JSON.stringify(m.body) });
          await remove(m.id);
        } catch (e) {
          if (
            e instanceof ApiError &&
            [409, 422, 403, 404].includes(e.status)
          ) {
            m.blocked = e.message;
            await enqueue(m);
            break;
          } else {
            if (e instanceof ApiError && e.status === 401) {
              setUser(null);
              setSelectedId("");
              setSelected(null);
              setEditing(false);
            }
            setNotice(
              e instanceof ApiError && e.status === 401
                ? "Session expired. Sign in again to send your saved changes."
                : (e as Error).message,
            );
            break;
          }
        }
      }
      setQueue(await pending(user.username));
      await refresh();
    } catch (e) {
      setNotice("Local queue unavailable: " + (e as Error).message);
    } finally {
      running.current = false;
      setSyncing(false);
    }
  }, [user, refresh]);
  useEffect(() => {
    api<User>("/session")
      .then(setUser)
      .catch(() => {})
      .finally(() => setBoot(false));
    const on = () => setOnline(navigator.onLine);
    window.addEventListener("online", on);
    window.addEventListener("offline", on);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", on);
    };
  }, []);
  useEffect(() => {
    if (user) {
      reloadQueue().catch((e) => setNotice(String(e)));
      refresh();
    }
  }, [user]);
  useEffect(() => {
    if (!user) return;
    const t = setInterval(() => {
      refresh();
      flush();
    }, 8000);
    return () => clearInterval(t);
  }, [user, refresh, flush]);
  useEffect(() => {
    if (online && user) flush();
  }, [online, user]);
  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    setSelected(null);
    setEditing(false);
    fetchDetail(selectedId).catch((e) => setNotice(e.message));
  }, [selectedId]);
  async function mutate(
    path: string,
    body: Record<string, unknown>,
    label: string,
  ) {
    if (!user || !selected) return;
    const id = crypto.randomUUID();
    const m: Mutation = {
      id,
      owner: user.username,
      caseId: selected.id,
      label,
      path,
      body: { ...body, event_id: id },
      created: new Date().toISOString(),
    };
    await enqueue(m);
    setEditing(false);
    setQueue(await pending(user.username));
    setNotice(
      "Change saved to the local queue. It remains pending until the server acknowledges it.",
    );
    await flush();
    await fetchDetail(selected.id);
  }
  async function openCase(c: Case) {
    if (editing && !window.confirm("Discard the unsaved review draft?")) return;
    setSelectedId(c.id);
    setTab("overview");
    setView("cases");
  }
  const awaiting = cases.filter(
      (c) => c.clinical.status === "awaiting_review",
    ).length,
    urgent = cases.filter(
      (c) => c.red_flag && c.clinical.status !== "reviewed",
    ).length,
    results = cases.filter(
      (c) => c.clinical.status === "awaiting_results",
    ).length,
    reviewed = cases.filter((c) => c.clinical.status === "reviewed").length;
  const visible = cases
    .filter(
      (c) =>
        `${c.patient_code} ${c.village}`
          .toLowerCase()
          .includes(search.toLowerCase()) &&
        (filter === "all" ||
          (filter === "urgent"
            ? c.red_flag && c.clinical.status !== "reviewed"
            : c.clinical.status === filter)),
    )
    .sort((a, b) => Number(b.red_flag) - Number(a.red_flag));
  if (boot)
    return (
      <div className="boot">
        <Brand />
        <p>Opening the clinical workspace…</p>
      </div>
    );
  if (!user)
    return (
      <Login
        onLogin={(u) => {
          setCases([]);
          setSelectedId("");
          setSelected(null);
          setQueue([]);
          setEditing(false);
          setView("cases");
          setUser(u);
          setNotice("");
        }}
      />
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {[
            ["cases", "Case worklist", LayoutDashboard],
            ["investigations", "Investigations", FlaskConical],
            ["sync", "Sync centre", RefreshCw],
          ].map(([id, title, Icon]: any) => (
            <button
              className={view === id ? "active" : ""}
              key={id}
              onClick={() => {
                if (editing && !confirm("Discard the unsaved draft?")) return;
                setEditing(false);
                setView(id);
                setSelectedId("");
              }}
            >
              <Icon size={19} />
              {title}
              {id === "cases" && <b>{cases.length}</b>}
              {id === "sync" && queue.length > 0 && <b>{queue.length}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="tiny-dot" /> CONNECTED CARE
          <h4>Every referral deserves follow-through.</h4>
          <p>
            Screening, investigations and the next clinical action in one place.
          </p>
          <ShieldCheck size={21} />
        </div>
        <div className="profile">
          <div className="avatar">
            {user.full_name.replace(/^Dr\.?\s*/, "").slice(0, 1)}
          </div>
          <div>
            <strong>{user.full_name}</strong>
            <small>Clinician · Facility access</small>
          </div>
          <button
            aria-label="Sign out"
            title="Sign out"
            onClick={async () => {
              if (queue.length) {
                setNotice(
                  "Send or resolve your pending changes before signing out.",
                );
                setView("sync");
                return;
              }
              if (editing && !confirm("Discard the unsaved draft?")) return;
              await api("/session", { method: "DELETE" });
              setUser(null);
              setSelectedId("");
              setCases([]);
            }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span>
            <span className="facility-dot" />
            {user.facility}
            <ChevronRight size={14} />
            <b>
              {view === "sync"
                ? "Sync centre"
                : selected
                  ? "Case review"
                  : view === "investigations"
                    ? "Investigations"
                    : "Case worklist"}
            </b>
          </span>
          <div>
            <button
              className={"sync-chip " + (!online ? "offline" : "")}
              onClick={() => setView("sync")}
            >
              {online ? <Wifi size={14} /> : <WifiOff size={14} />}{" "}
              {!online
                ? "Offline"
                : syncing
                  ? "Sending changes…"
                  : queue.length
                    ? `${queue.length} pending`
                    : "Connected"}
            </button>
            <span className="prototype">PROTOTYPE</span>
          </div>
        </header>
        {notice && (
          <div className="notice" role="status">
            {notice}
            <button onClick={() => setNotice("")} aria-label="Dismiss notice">
              <X size={16} />
            </button>
          </div>
        )}
        <div className="content">
          {view === "sync" ? (
            <>
              <div className="page-title">
                <div>
                  <span className="eyebrow">RECORD CONTINUITY</span>
                  <h1>Sync centre</h1>
                  <p>Every change needs a server receipt.</p>
                </div>
                <button
                  className="primary"
                  onClick={() => flush()}
                  disabled={syncing || !online}
                >
                  <RefreshCw size={16} />
                  Retry pending changes
                </button>
              </div>
              <div className="panel sync-intro">
                <ShieldCheck />
                <div>
                  <h3>
                    {queue.length
                      ? "Your work is saved on this browser"
                      : "All review changes acknowledged"}
                  </h3>
                  <p>
                    Review edits and investigation updates use encrypted local
                    storage, stable event IDs and version checks. Attachments
                    upload only while connected.
                  </p>
                  <small>
                    Last worklist receipt:{" "}
                    {lastSync ? date(lastSync) : "Not received yet"} · Mobile
                    offline replay is a separate integration.
                  </small>
                </div>
              </div>
              {queue.length === 0 ? (
                <div className="empty">
                  <CheckCheck size={40} />
                  <h3>Nothing waiting to send</h3>
                  <p>
                    New records appear in the worklist after reaching the
                    backend.
                  </p>
                </div>
              ) : (
                queue.map((m) => (
                  <div className="panel queued" key={m.id}>
                    <div>
                      <Pill value={m.blocked ? "conflict" : "pending"} />
                      <h3>{m.label}</h3>
                      <small>
                        {m.caseId.slice(0, 8)} · {date(m.created)}
                      </small>
                      <p>
                        {m.blocked ||
                          "Waiting for the server to acknowledge this exact event."}
                      </p>
                      {m.body.notes != null && (
                        <blockquote>{String(m.body.notes)}</blockquote>
                      )}
                    </div>
                    <div className="queue-actions">
                      <button
                        onClick={() =>
                          openCase(
                            cases.find((c) => c.id === m.caseId) ||
                              ({ id: m.caseId } as Case),
                          )
                        }
                      >
                        Open latest record
                        <ArrowRight size={15} />
                      </button>
                      {m.blocked && (
                        <button
                          className="danger-link"
                          onClick={async () => {
                            if (
                              !confirm(
                                "Discard this local change? The server record will be retained.",
                              )
                            )
                              return;
                            await remove(m.id);
                            await reloadQueue();
                          }}
                        >
                          Discard local change
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </>
          ) : !selectedId ? (
            <>
              <div className="page-title">
                <div>
                  <span className="eyebrow">COMMUNITY TO CLINIC</span>
                  <h1>
                    {view === "investigations"
                      ? "Investigation tracker"
                      : "Care starts with a clear next step."}
                  </h1>
                  <p>
                    Review community referrals. Keep every person in the care
                    pathway.
                  </p>
                </div>
                <button className="secondary" onClick={() => refresh()}>
                  <RefreshCw size={16} />
                  Refresh records
                </button>
              </div>
              <div className="stats">
                {[
                  [awaiting, "Awaiting review", ClipboardList, "mint"],
                  [urgent, "Flagged for urgent review", AlertTriangle, "coral"],
                  [results, "Awaiting results", FlaskConical, "sand"],
                  [reviewed, "Reviews completed", CheckCheck, "blue"],
                ].map(([n, l, Icon, col]: any) => (
                  <button
                    className={"stat " + col}
                    key={l}
                    onClick={() =>
                      setFilter(
                        l.startsWith("Flagged")
                          ? "urgent"
                          : l === "Awaiting results"
                            ? "awaiting_results"
                            : l === "Reviews completed"
                              ? "reviewed"
                              : "awaiting_review",
                      )
                    }
                  >
                    <div>
                      <span>{l}</span>
                      <strong>{n.toString().padStart(2, "0")}</strong>
                    </div>
                    <Icon size={21} />
                  </button>
                ))}
              </div>
              <div className="panel worklist">
                <div className="section-heading">
                  <div>
                    <h2>
                      {view === "investigations"
                        ? "Cases awaiting investigations"
                        : "Referral worklist"}
                      <span className="count">{visible.length}</span>
                    </h2>
                    <p>
                      {view === "investigations"
                        ? "Open a case to track individual orders and their results."
                        : "Prioritised by recorded red flags, with clinician review status."}
                    </p>
                  </div>
                  <span className="live">
                    <i />{" "}
                    {lastSync ? "Updated " + date(lastSync) : "Connecting"}
                  </span>
                </div>
                <div className="filters">
                  <div className="filter-tabs">
                    {[
                      ["all", "All records"],
                      ["awaiting_review", "Needs review"],
                      ["awaiting_results", "Awaiting results"],
                      ["reviewed", "Completed"],
                    ].map(([id, l]) => (
                      <button
                        className={filter === id ? "selected" : ""}
                        onClick={() => setFilter(id)}
                        key={id}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                  <label className="search">
                    <Search size={16} />
                    <input
                      placeholder="Search code or village"
                      aria-label="Search cases"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>PERSON / RECORD</th>
                        <th>SCREENING</th>
                        <th>RECEIVED</th>
                        <th>REVIEW STATUS</th>
                        <th>ATTACHMENTS</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {visible
                        .filter(
                          (c) =>
                            view !== "investigations" ||
                            c.clinical.status === "awaiting_results",
                        )
                        .map((c) => (
                          <tr
                            key={c.id}
                            onClick={() => openCase(c)}
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") openCase(c);
                            }}
                          >
                            <td>
                              <div
                                className={
                                  "patient-icon " +
                                  (c.red_flag ? "flagged" : "")
                                }
                              >
                                <Users size={18} />
                              </div>
                              <div className="patient-cell">
                                <strong>{c.patient_code}</strong>
                                <small>
                                  {c.age} yrs · {human(c.sex)} · {c.village}
                                </small>
                              </div>
                            </td>
                            <td>
                              <Pill value={c.tier} />
                            </td>
                            <td>
                              {date(c.created_at)}
                              <small className="cell-small">
                                Server record
                              </small>
                            </td>
                            <td>
                              <Pill value={c.clinical.status} />
                              {queue.some((m) => m.caseId === c.id) && (
                                <small className="cell-small pending-text">
                                  Local change pending
                                </small>
                              )}
                            </td>
                            <td>
                              <span className="attachment-count">
                                <FileText size={15} />
                                {c.document_count}
                                <ImageIcon size={15} />
                                {c.image_count}
                              </span>
                            </td>
                            <td>
                              <ChevronRight size={18} />
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                  {visible.length === 0 && (
                    <div className="empty">
                      <Search />
                      <h3>No records in this view</h3>
                      <p>
                        Try another filter or wait for a volunteer screening to
                        reach the server.
                      </p>
                    </div>
                  )}
                </div>
                <div className="table-footer">
                  <span>Showing up to 500 received records</span>
                  <span>
                    <LockKeyhole size={13} /> Facility restricted
                  </span>
                </div>
              </div>
              <div className="care-note">
                <HeartPulse size={20} />
                <p>
                  <strong>Keep the next action visible.</strong> A screening
                  result supports referral review. The clinical assessment
                  belongs to you.
                </p>
                <span>REVIEW → INVESTIGATE → FOLLOW UP</span>
              </div>
            </>
          ) : !selected ? (
            <div className="empty">
              <RefreshCw className="spin" />
              <p>Loading the case record…</p>
              <button
                onClick={() => {
                  setSelectedId("");
                  setEditing(false);
                }}
              >
                Back to worklist
              </button>
            </div>
          ) : (
            <>
              <button
                className="back"
                onClick={() => {
                  if (editing && !confirm("Discard the unsaved draft?")) return;
                  setSelectedId("");
                  setEditing(false);
                }}
              >
                <ArrowLeft size={15} /> Back to worklist
              </button>
              <div className="case-heading">
                <div className="patient-icon large">
                  <Users size={27} />
                </div>
                <div>
                  <span className="eyebrow">COMMUNITY SCREENING RECORD</span>
                  <h1>{selected.patient_code}</h1>
                  <p>
                    {selected.age} years · {human(selected.sex)} ·{" "}
                    {selected.village} <span>•</span>{" "}
                    {date(selected.created_at)}
                  </p>
                </div>
                <Pill value={selected.clinical.status} />
              </div>
              {selected.red_flag && (
                <div className="red-flag">
                  <AlertTriangle size={20} />
                  <div>
                    <strong>A red flag was recorded during screening.</strong>
                    <p>
                      Review the original responses and assess the person
                      according to your clinical protocol.
                    </p>
                  </div>
                </div>
              )}
              {queue
                .filter((m) => m.caseId === selected.id && m.blocked)
                .map((m) => (
                  <div className="conflict-box" key={m.id}>
                    <h3>Review conflict: compare before resubmitting</h3>
                    <p>{m.blocked}</p>
                    <div className="comparison">
                      <div>
                        <b>Server · version {selected.clinical.version}</b>
                        <p>{selected.clinical.notes || "No notes"}</p>
                        <p>
                          Next:{" "}
                          {selected.clinical.next_action || "Not recorded"}
                        </p>
                      </div>
                      <div>
                        <b>Your queued draft</b>
                        <p>{String(m.body.notes || "")}</p>
                        <p>Next: {String(m.body.next_action || "")}</p>
                      </div>
                    </div>
                    {m.path.endsWith("/review") && (
                      <button
                        onClick={async () => {
                          const id = crypto.randomUUID();
                          await enqueue({
                            ...m,
                            id,
                            blocked: undefined,
                            body: {
                              ...m.body,
                              event_id: id,
                              expected_version: selected.clinical.version,
                            },
                            created: new Date().toISOString(),
                          });
                          await remove(m.id);
                          await reloadQueue();
                          await flush();
                          await fetchDetail(selected.id);
                        }}
                      >
                        Resubmit this draft against version{" "}
                        {selected.clinical.version}
                      </button>
                    )}
                  </div>
                ))}
              <div className="detail-grid">
                <section>
                  <div className="detail-tabs">
                    {[
                      ["overview", "Overview"],
                      ["questions", "Questionnaire"],
                      ["documents", "Documents"],
                      ["imaging", "Imaging"],
                      ["timeline", "Timeline"],
                    ].map(([id, l]) => (
                      <button
                        className={tab === id ? "selected" : ""}
                        onClick={() => setTab(id)}
                        key={id}
                      >
                        {l}
                        {id === "documents" && (
                          <b>{selected.documents?.length || 0}</b>
                        )}
                      </button>
                    ))}
                  </div>
                  {tab === "overview" && (
                    <>
                      <div className="panel">
                        <div className="section-heading">
                          <h2>
                            <ClipboardList size={18} /> Screening summary
                          </h2>
                          <Pill value={selected.tier} />
                        </div>
                        <div className="summary-grid">
                          <div>
                            <small>QUESTIONNAIRE SCORE</small>
                            <strong>
                              {selected.clinical_score}
                              <em> / {selected.questionnaire_max}</em>
                            </strong>
                          </div>
                          <div>
                            <small>ACOUSTIC PROXY SCORE</small>
                            <strong>
                              {selected.audio_model?.calibrated_score.toFixed(
                                2,
                              )}
                              <em> / 1.00</em>
                            </strong>
                          </div>
                        </div>
                        <p className="muted">
                          Acoustic output: respiratory abnormality proxy. It is
                          not a validated TB probability.
                        </p>
                        <div className="pathway">
                          <span className="eyebrow">
                            RECORDED SCREENING PATHWAY
                          </span>
                          <p>{selected.recommended_pathway}</p>
                        </div>
                        <div className="mini-facts">
                          <span>
                            <ShieldCheck size={15} />
                            Consent{" "}
                            {selected.consent_given
                              ? "recorded"
                              : "not recorded"}
                          </span>
                          <span>
                            <FileText size={15} />
                            {selected.documents?.length} original documents
                          </span>
                        </div>
                      </div>
                      <Investigations
                        item={selected}
                        mutate={mutate}
                        disabled={queue.some((m) => m.caseId === selected.id)}
                      />
                      <div className="panel record-brief">
                        <div className="section-heading">
                          <h2>
                            <Activity size={18} /> Record brief
                          </h2>
                          <span className="subtle-label">
                            COMPILED FROM THIS RECORD
                          </span>
                        </div>
                        <p>
                          {selected.patient_code}, {selected.age} years, was
                          screened in {selected.village}. Recorded positive
                          responses:{" "}
                          {Object.entries(selected.answers || {})
                            .filter(([, v]) => v === 2)
                            .map(([k]) => human(k))
                            .join(", ") || "none"}
                          . Uncertain responses:{" "}
                          {selected.uncertain_symptoms?.map(human).join(", ") ||
                            "none"}
                          .
                        </p>
                        <small>
                          This deterministic brief does not infer a diagnosis or
                          suggest treatment.
                        </small>
                      </div>
                    </>
                  )}
                  {tab === "questions" && (
                    <div className="panel">
                      <div className="section-heading">
                        <h2>Original symptom responses</h2>
                        <span className="subtle-label">READ ONLY</span>
                      </div>
                      {Object.entries(selected.answers || {}).map(([q, a]) => (
                        <div className="question-row" key={q}>
                          <span>{human(q)}</span>
                          <Pill
                            value={a === 2 ? "yes" : a === 1 ? "unsure" : "no"}
                          />
                        </div>
                      ))}
                      <p className="muted">
                        Original answers remain separate from the clinician’s
                        assessment.
                      </p>
                    </div>
                  )}
                  {tab === "documents" && (
                    <Documents
                      item={selected}
                      refresh={() => fetchDetail(selected.id)}
                      onError={setNotice}
                    />
                  )}
                  {tab === "imaging" && (
                    <ImagingPanel
                      item={selected}
                      refresh={() => fetchDetail(selected.id)}
                      onError={setNotice}
                    />
                  )}
                  {tab === "timeline" && (
                    <div className="panel">
                      <div className="section-heading">
                        <h2>Record timeline</h2>
                        <span className="subtle-label">SERVER EVENTS</span>
                      </div>
                      <div className="timeline">
                        <div>
                          <span className="timeline-dot" />
                          <b>Screening received</b>
                          <small>{date(selected.created_at)}</small>
                        </div>
                        {selected.timeline?.map((e) => (
                          <div key={e.id}>
                            <span className="timeline-dot" />
                            <b>{human(e.kind)}</b>
                            <small>
                              {e.actor} · {date(e.created_at)}
                            </small>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </section>
                <aside className="review-column">
                  <ReviewForm
                    key={selected.id + ":" + selected.clinical.version}
                    clinical={selected.clinical}
                    pending={queue.some((m) => m.caseId === selected.id)}
                    onDirty={() => setEditing(true)}
                    save={(body) =>
                      mutate(
                        "/cases/" + selected.id + "/review",
                        body,
                        "Clinical review",
                      )
                    }
                  />
                  <div className="panel snapshots">
                    <h3>
                      <FileText size={17} /> Report snapshots
                    </h3>
                    <p>A completed review creates an immutable record.</p>
                    {selected.reports?.map((r) => (
                      <button
                        key={r.id}
                        onClick={async () => {
                          try {
                            setReport(await api("/reports/" + r.id));
                          } catch (e) {
                            setNotice((e as Error).message);
                          }
                        }}
                      >
                        <FileText size={15} />
                        <span>
                          Review version {r.version}
                          <small>{date(r.created_at)}</small>
                        </span>
                        <ChevronRight size={16} />
                      </button>
                    ))}
                    {!selected.reports?.length && (
                      <small>No completed review yet.</small>
                    )}
                  </div>
                  <div className="record-id">
                    RECORD ID<code>{selected.id}</code>
                    <span>Clinical version {selected.clinical.version}</span>
                  </div>
                </aside>
              </div>
            </>
          )}
        </div>
        <footer className="footer">
          <span>ShwaasAI · Connected respiratory care</span>
          <span>Research prototype · Ni-kshay integration not connected</span>
        </footer>
      </main>
      {report && <Report data={report} close={() => setReport(null)} />}
    </div>
  );
}

function ReviewForm({
  clinical,
  pending,
  onDirty,
  save,
}: {
  clinical: Clinical;
  pending: boolean;
  onDirty: () => void;
  save: (body: Record<string, unknown>) => Promise<void>;
}) {
  const [notes, setNotes] = useState(clinical.notes),
    [next, setNext] = useState(clinical.next_action),
    [status, setStatus] = useState(clinical.status),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <form
      className="panel review-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
          await save({
            expected_version: clinical.version,
            status,
            notes,
            next_action: next,
          });
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="section-heading">
        <h2>
          <HeartPulse size={19} /> Clinical review
        </h2>
        <span className="version">v{clinical.version}</span>
      </div>
      <label>
        Review status
        <select
          value={status}
          disabled={pending}
          onChange={(e) => {
            onDirty();
            setStatus(e.target.value);
          }}
        >
          {[
            "awaiting_review",
            "under_review",
            "awaiting_results",
            "reviewed",
          ].map((s) => (
            <option value={s} key={s}>
              {human(s)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Assessment notes
        <textarea
          value={notes}
          disabled={pending}
          onChange={(e) => {
            onDirty();
            setNotes(e.target.value);
          }}
          maxLength={10000}
          required={status === "reviewed"}
          placeholder="Document your clinical assessment…"
          rows={6}
        />
      </label>
      <label>
        Next action
        <textarea
          value={next}
          disabled={pending}
          onChange={(e) => {
            onDirty();
            setNext(e.target.value);
          }}
          maxLength={2000}
          required={status === "reviewed"}
          rows={3}
          placeholder="What happens next, and who follows up?"
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={busy || pending}>
        {pending
          ? "Waiting for sync"
          : busy
            ? "Saving…"
            : "Save clinical review"}
        <Check size={17} />
      </button>
      <small>
        <LockKeyhole size={13} />
        Version checked. Changes are retained until acknowledged.
      </small>
    </form>
  );
}
function Investigations({
  item,
  mutate,
  disabled,
}: {
  item: Case;
  mutate: (
    path: string,
    body: Record<string, unknown>,
    label: string,
  ) => Promise<void>;
  disabled: boolean;
}) {
  const [kind, setKind] = useState("Chest X-ray"),
    [notes, setNotes] = useState(""),
    [error, setError] = useState("");
  const transitions: Record<string, string[]> = {
    requested: ["accepted", "cancelled"],
    accepted: ["result_received", "cancelled"],
    result_received: ["reviewed"],
    reviewed: [],
    cancelled: [],
  };
  return (
    <div className="panel">
      <div className="section-heading">
        <h2>
          <FlaskConical size={18} /> Investigations
        </h2>
        <span className="count">{item.investigations?.length || 0}</span>
      </div>
      {item.investigations?.map((o) => (
        <div className="order" key={o.id}>
          <div>
            <strong>{o.kind}</strong>
            <small>{o.notes || "No order note"}</small>
            <Pill value={o.status} />
          </div>
          <div>
            {transitions[o.status]?.map((s) => (
              <button
                key={s}
                disabled={disabled}
                onClick={async () => {
                  try {
                    await mutate(
                      "/cases/" + item.id + "/investigations/" + o.id,
                      {
                        expected_version: o.version,
                        status: s,
                        notes: o.notes,
                      },
                      human(o.kind) + " update",
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {s === "accepted"
                  ? "Accept order"
                  : s === "result_received"
                    ? "Mark result received"
                    : human(s)}
              </button>
            ))}
          </div>
        </div>
      ))}
      <form
        className="order-create"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await mutate(
              "/cases/" + item.id + "/investigations",
              { kind, notes },
              kind + " request",
            );
            setNotes("");
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <label>
          New investigation
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {[
              "Chest X-ray",
              "Sputum NAAT",
              "Smear microscopy",
              "Other investigation",
            ].map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </label>
        <label>
          Order note
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            placeholder="Clinical indication or instructions"
          />
        </label>
        <button disabled={disabled}>
          <Plus size={16} />
          Request investigation
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <small className="muted">
        Receipt is recorded separately from clinical review. Add results in
        Documents or Imaging.
      </small>
    </div>
  );
}

function Documents({
  item,
  refresh,
  onError,
}: {
  item: Case;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [active, setActive] = useState<Document | null>(null),
    [fields, setFields] = useState<SourceField[]>([]),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (active) {
      const latest = item.documents?.find((d) => d.id === active.id);
      if (latest) {
        setActive(latest);
        setFields(latest.fields);
      }
    }
  }, [item]);
  const upload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = e.currentTarget;
    setBusy(true);
    try {
      await api("/cases/" + item.id + "/documents", {
        method: "POST",
        body: new FormData(f),
      });
      f.reset();
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="panel">
        <div className="section-heading">
          <h2>
            <FileText size={19} /> Original reports & OCR
          </h2>
          <span className="subtle-label">SOURCE FIRST</span>
        </div>
        <p className="muted">
          Check extracted text against the original. Confirming transcription
          does not confirm the clinical finding.
        </p>
        <form className="upload-box" onSubmit={upload}>
          <Upload size={23} />
          <div>
            <strong>Add an existing report</strong>
            <small>PDF, PNG or JPEG · 20 MB maximum</small>
            <input
              name="file"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              required
              aria-label="Report file"
            />
          </div>
          <button disabled={busy}>
            {busy ? "Uploading…" : "Upload report"}
          </button>
        </form>
        {item.documents?.map((d) => (
          <button
            className={"document-row " + (active?.id === d.id ? "chosen" : "")}
            key={d.id}
            onClick={() => {
              setActive(d);
              setFields(d.fields);
            }}
          >
            <FileText size={21} />
            <div>
              <strong>{d.filename}</strong>
              <small>
                {Math.round(d.size / 1024)} KB · {d.fields.length} extracted
                fields
              </small>
            </div>
            <Pill value={d.verification} />
            <ChevronRight size={16} />
          </button>
        ))}
        {!item.documents?.length && (
          <div className="empty small">
            <FileText />
            <p>No original reports attached.</p>
          </div>
        )}
      </div>
      {active && (
        <div className="panel">
          <div className="section-heading">
            <h2>Verify transcription</h2>
            <a
              className="button"
              target="_blank"
              rel="noreferrer"
              href={"/clinical/documents/" + active.id + "/file"}
            >
              Open original
              <ExternalLink size={14} />
            </a>
          </div>
          <div className="source-preview">
            {active.media_type.startsWith("image") ? (
              <img
                src={"/clinical/documents/" + active.id + "/file"}
                alt={"Original source: " + active.filename}
              />
            ) : (
              <iframe
                title="Original PDF report"
                src={"/clinical/documents/" + active.id + "/file"}
              />
            )}
          </div>
          {fields.map((f, i) => (
            <div className="field-edit" key={i}>
              <input
                aria-label={"Field " + (i + 1) + " name"}
                value={f.name}
                placeholder="Field name"
                maxLength={120}
                onChange={(e) =>
                  setFields(
                    fields.map((v, j) =>
                      j === i ? { ...v, name: e.target.value } : v,
                    ),
                  )
                }
              />
              <textarea
                aria-label={"Field " + (i + 1) + " value"}
                value={f.value}
                placeholder="Extracted value"
                maxLength={2000}
                onChange={(e) =>
                  setFields(
                    fields.map((v, j) =>
                      j === i ? { ...v, value: e.target.value } : v,
                    ),
                  )
                }
              />
              <input
                type="number"
                min="1"
                max="20"
                aria-label="Source page"
                value={f.page}
                onChange={(e) =>
                  setFields(
                    fields.map((v, j) =>
                      j === i ? { ...v, page: Number(e.target.value) } : v,
                    ),
                  )
                }
              />
              <button
                aria-label="Remove field"
                onClick={() => setFields(fields.filter((_, j) => j !== i))}
              >
                <X size={14} />
              </button>
            </div>
          ))}
          <div className="action-row">
            <button
              disabled={fields.length >= 100}
              onClick={() =>
                setFields([...fields, { name: "", value: "", page: 1 }])
              }
            >
              <Plus size={15} />
              Add field
            </button>
            <button
              className="primary"
              disabled={busy || fields.some((f) => !f.name.trim())}
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/documents/" + active.id + "/confirm", {
                    method: "POST",
                    body: JSON.stringify({
                      expected_version: active.version,
                      fields,
                    }),
                  });
                  await refresh();
                } catch (e) {
                  onError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Check size={16} />
              Confirm transcription
            </button>
          </div>
          <code className="hash">SHA-256 {active.sha256}</code>
        </div>
      )}
    </>
  );
}

function ImagingPanel({
  item,
  refresh,
  onError,
}: {
  item: Case;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [status, setStatus] = useState<{
      archive: string;
      viewer: boolean;
    } | null>(null),
    [active, setActive] = useState<Imaging | null>(item.images?.[0] || null),
    [zoom, setZoom] = useState(1),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<{ archive: string; viewer: boolean }>("/pacs/status")
      .then(setStatus)
      .catch((e) => onError(e.message));
  }, []);
  const orders =
    item.investigations?.filter(
      (o) =>
        o.kind === "Chest X-ray" &&
        !["reviewed", "cancelled"].includes(o.status),
    ) || [];
  return (
    <>
      <div className="panel">
        <div className="section-heading">
          <h2>
            <ImageIcon size={18} /> Imaging workspace
          </h2>
          <Pill value={status?.archive || "checking"} />
        </div>
        <p className="muted">
          DICOM files stay in the private archive. Study receipt, patient
          association and clinical review are tracked separately.
        </p>
        {status?.archive !== "connected" && (
          <div className="setup-note">
            <AlertTriangle size={18} />
            <p>
              {status?.archive === "not_configured"
                ? "Start the Orthanc and OHIF services from the PACS setup guide to enable DICOM ingestion."
                : "The archive has not confirmed availability. Check the PACS services."}
            </p>
          </div>
        )}
        <form
          className="imaging-upload"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            const f = e.currentTarget;
            try {
              await api("/cases/" + item.id + "/imaging", {
                method: "POST",
                body: new FormData(f),
              });
              f.reset();
              await refresh();
            } catch (e) {
              onError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Link to investigation
            <select name="order_id" required disabled={!orders.length}>
              {orders.map((o) => (
                <option value={o.id} key={o.id}>
                  {o.kind} · {human(o.status)}
                </option>
              ))}
            </select>
          </label>
          <label>
            DICOM files
            <input
              type="file"
              name="files"
              multiple
              accept=".dcm,application/dicom"
              required
            />
          </label>
          <label className="checkbox">
            <input type="checkbox" name="identity_confirmed" value="true" />I
            checked the person’s identity against the DICOM header. Use this
            only when the patient ID differs.
          </label>
          <button
            className="primary"
            disabled={busy || !orders.length || status?.archive !== "connected"}
          >
            <Upload size={16} />
            {busy ? "Receiving images…" : "Upload to archive"}
          </button>
          {!orders.length && (
            <small>
              Create an open Chest X-ray investigation in Overview first.
            </small>
          )}
        </form>
      </div>
      {!!item.images?.length && (
        <div className="panel image-panel">
          <div className="section-heading">
            <h2>Received instances</h2>
            <span className="subtle-label">COMPLETENESS UNCONFIRMED</span>
          </div>
          <div className="instance-tabs">
            {item.images.map((i, n) => (
              <button
                className={active?.id === i.id ? "selected" : ""}
                key={i.id}
                onClick={() => {
                  setActive(i);
                  setZoom(1);
                }}
              >
                Image {n + 1}
              </button>
            ))}
          </div>
          {active && (
            <>
              <div className="xray-canvas">
                <img
                  alt="Archive-rendered X-ray preview"
                  style={{ transform: `scale(${zoom})` }}
                  src={"/clinical/imaging/" + active.id + "/preview"}
                />
                <span>RENDERED PREVIEW · NOT A DIAGNOSTIC WORKSTATION</span>
              </div>
              <div className="viewer-controls">
                <button
                  aria-label="Zoom out"
                  onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
                >
                  <ZoomOut size={17} />
                </button>
                <b>{Math.round(zoom * 100)}%</b>
                <button
                  aria-label="Zoom in"
                  onClick={() => setZoom(Math.min(3, zoom + 0.25))}
                >
                  <ZoomIn size={17} />
                </button>
                <button onClick={() => setZoom(1)}>Reset</button>
                {status?.viewer && (
                  <a
                    className="button primary"
                    target="_blank"
                    rel="noreferrer"
                    href={
                      "/clinical/pacs/viewer/viewer?StudyInstanceUIDs=" +
                      encodeURIComponent(active.study_uid)
                    }
                  >
                    Open OHIF viewer
                    <ExternalLink size={15} />
                  </a>
                )}
              </div>
              <div className="image-meta">
                <span>Patient ID: {active.patient_id || "Missing"}</span>
                <span>Identity: {human(active.identity_check)}</span>
                <code>Study: {active.study_uid}</code>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
function Report({ data, close }: { data: any; close: () => void }) {
  const s = data.snapshot as Case;
  return (
    <div className="modal-backdrop">
      <article className="report">
        <div className="report-actions">
          <button onClick={close}>
            <X size={16} />
            Close
          </button>
          <button className="primary" onClick={() => window.print()}>
            Print / save PDF
          </button>
        </div>
        <Brand />
        <span className="eyebrow">CLINICIAN REVIEW SNAPSHOT</span>
        <h1>{s.patient_code}</h1>
        <p>
          {s.age} years · {human(s.sex)} · {s.village}
        </p>
        <p>
          Report {data.id} · Review version {data.version} ·{" "}
          {date(data.created_at)}
        </p>
        <h3>Clinician assessment</h3>
        <p className="preserve">{s.clinical.notes}</p>
        <h3>Next action</h3>
        <p className="preserve">{s.clinical.next_action}</p>
        <p>
          Reviewed by {s.clinical.reviewer} · Status: {human(s.clinical.status)}
        </p>
        <h3>Screening evidence</h3>
        <p>
          Questionnaire {s.clinical_score}/{s.questionnaire_max}. Acoustic proxy
          score: {s.audio_model?.calibrated_score}. This is not a validated TB
          probability.
        </p>
        <table>
          <tbody>
            {Object.entries(s.answers || {}).map(([q, a]) => (
              <tr key={q}>
                <td>{human(q)}</td>
                <td>{a === 2 ? "Yes" : a === 1 ? "Unsure" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Source documents and transcription</h3>
        {s.documents?.map((d) => (
          <section key={d.id}>
            <strong>{d.filename}</strong>
            <p>
              Transcription: {human(d.verification)} · Checked by{" "}
              {d.confirmed_by || "Not confirmed"}
            </p>
            {d.fields.map((f, i) => (
              <p key={i}>
                {f.name}: {f.value} (page {f.page})
              </p>
            ))}
            <small className="hash">SHA-256 {d.sha256}</small>
          </section>
        ))}
        {!s.documents?.length && (
          <p>No source documents received at this snapshot.</p>
        )}
        <h3>Investigations</h3>
        {s.investigations?.map((o) => (
          <p key={o.id}>
            {o.kind}: {human(o.status)} — {o.notes}
          </p>
        ))}
        <h3>Imaging receipts</h3>
        {s.images?.map((i) => (
          <p key={i.id}>
            Study {i.study_uid} · {human(i.identity_check)} · Completeness
            unconfirmed
          </p>
        ))}
        <hr />
        <small>
          Research prototype. This snapshot records the clinician’s assessment
          and the available evidence at the time. Ni-kshay submission is not
          connected.
        </small>
      </article>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
