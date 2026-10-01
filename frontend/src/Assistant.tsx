import { useEffect, useState } from "react";
import { api } from "./api";
import { Explanation, Source } from "./components";
import type { Answer, Profile } from "./types";

type Message = {
  role: "user" | "assistant";
  question?: string;
  answer?: Answer;
};
type Session = { session_id: string; session_token: string };

export default function Assistant({
  profile,
  schemeId,
}: {
  profile: Profile;
  schemeId?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        const stored = sessionStorage.getItem("scholar-session");
        const saved: Session | null = stored ? JSON.parse(stored) : null;
        if (saved) {
          const data = await api<{
            context: {
              messages: {
                role: "user" | "assistant";
                content: Answer & { question?: string };
              }[];
            };
          }>("/sessions/" + saved.session_id, undefined, saved.session_token);
          if (active) {
            setSession(saved);
            setMessages(
              data.context.messages.map((m) =>
                m.role === "user"
                  ? { role: m.role, question: m.content.question }
                  : { role: m.role, answer: m.content },
              ),
            );
          }
        } else {
          const created = await api<Session>("/sessions", {});
          if (active) {
            sessionStorage.setItem("scholar-session", JSON.stringify(created));
            setSession(created);
          }
        }
      } catch (err) {
        if (active)
          setError(
            err instanceof Error ? err.message : "Could not load conversation.",
          );
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, []);
  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim() || !session) return;
    const text = question;
    setQuestion("");
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", question: text }]);
    try {
      const answer = await api<Answer>(
        "/agent/query",
        {
          question: text,
          session_id: session.session_id,
          ...(Object.keys(profile).length ? { profile } : {}),
          ...(schemeId ? { scheme_ids: [schemeId] } : {}),
        },
        session.session_token,
      );
      setMessages((m) => [...m, { role: "assistant", answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant unavailable.");
    } finally {
      setBusy(false);
    }
  }
  function reset() {
    sessionStorage.removeItem("scholar-session");
    window.location.reload();
  }
  return (
    <section className="panel chat">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ANSWERS WITH EVIDENCE</span>
          <h2>Your scholarship guide</h2>
          <p>Ask about benefits, documents, or the rules behind a result.</p>
        </div>
        <button className="button subtle" onClick={reset}>
          New conversation
        </button>
      </div>
      {!messages.length && (
        <div className="chat-empty">
          <div className="assistant-symbol">✦</div>
          <h3>Start with a question</h3>
          <p>
            Every fact comes from the scholarship dataset. Eligibility comes
            from the rule engine.
          </p>
          <div className="suggestions">
            {[
              "What scholarships are available for OBC students?",
              "What documents are needed for the single girl child scholarship?",
              "Which scholarships require GATE?",
            ].map((q) => (
              <button key={q} onClick={() => setQuestion(q)}>
                {q} ↗
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="messages" aria-live="polite">
        {messages.map((m, i) => (
          <article className={"message " + m.role} key={i}>
            <span className="eyebrow">
              {m.role === "user" ? "YOU" : "SCHOLARSHIP GUIDE"}
            </span>
            {m.question ? (
              <p>{m.question}</p>
            ) : (
              m.answer && (
                <>
                  <p className="answer-text">{m.answer.answer}</p>
                  {m.answer.explanation_state === "DETERMINISTIC_FALLBACK" && (
                    <small>Showing verified dataset excerpts.</small>
                  )}
                  {m.answer.warnings.map((w, j) => (
                    <p className="notice" key={j}>
                      {w.message}
                    </p>
                  ))}
                  {m.answer.eligibility.map((r) => (
                    <details key={r.scheme_id}>
                      <summary>
                        {r.scheme_name}: {r.status.replaceAll("_", " ")}
                      </summary>
                      <Explanation result={r} />
                    </details>
                  ))}
                  <details>
                    <summary>Sources ({m.answer.citations.length})</summary>
                    {m.answer.citations.map((c, j) => (
                      <Source citation={c} key={j} />
                    ))}
                  </details>
                </>
              )
            )}
          </article>
        ))}
      </div>
      {busy && (
        <p className="loading" role="status">
          Retrieving sources and checking rules…
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <form className="chat-input" onSubmit={send}>
        <label className="sr-only" htmlFor="chat-question">
          Ask a scholarship question
        </label>
        <input
          id="chat-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a scholarship question…"
          maxLength={2000}
        />
        <button
          className="button primary"
          disabled={busy || !session || !question.trim()}
        >
          Send ↗
        </button>
      </form>
      <small className="chat-footnote">
        Dataset facts may need official verification. No missing profile values
        are assumed.
      </small>
    </section>
  );
}
