import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { chatApi } from '../api/lists.js';
import { moviesApi } from '../api/movies.js';
import { useAuthedApi } from '../auth/AuthContext.jsx';
import { EmptyState } from '../components/Chrome.jsx';
import { MovieCard } from '../components/Movies.jsx';
import { useToast } from '../components/Toaster.jsx';

const SUGGESTIONS = [
  'A tense sci-fi night',
  'Comedies from 2024',
  'Movies like Dune',
  'Hidden gems I missed',
];

async function resolveCards(ids, cache) {
  const missing = [...new Set(ids)].filter((id) => !(id in cache));
  if (missing.length) {
    const found = await Promise.all(
      missing.slice(0, 10).map((id) => moviesApi.details(id).catch(() => null)),
    );
    found.forEach((card, i) => {
      if (card) cache[missing[i]] = card;
    });
  }
  return ids.map((id) => cache[id]).filter(Boolean);
}

function FollowUps({ onAsk }) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {['More like this', 'Why this pick?'].map((label) => (
        <button
          key={label}
          onClick={() => onAsk(label)}
          className="rounded-full border border-line px-3 py-1 text-xs text-ash transition hover:border-crimson hover:text-parchment"
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export function Assistant() {
  const authed = useAuthedApi();
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const cardCache = useRef({});
  const threadCache = useRef({});
  const bottomRef = useRef(null);
  const autoSent = useRef(false);

  const scrollDown = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });

  const loadSessions = useCallback(async () => {
    try {
      const d = await authed(() => chatApi.listSessions());
      setSessions(d.items ?? []);
    } catch {
      /* sidebar stays empty; thread still works */
    } finally {
      setLoadingList(false);
    }
  }, [authed]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const openSession = useCallback(
    async (id) => {
      setActiveId(id);
      setDrawer(false);
      setFailed(null);
      if (threadCache.current[id]) {
        setMessages(threadCache.current[id]);
        return;
      }
      setLoadingThread(true);
      setMessages([]);
      try {
        const d = await authed(() => chatApi.history(id));
        const withCards = await Promise.all(
          (d.messages ?? []).map(async (m) => ({
            ...m,
            movies: m.movieIds?.length ? await resolveCards(m.movieIds, cardCache.current) : [],
          })),
        );
        threadCache.current[id] = withCards;
        setMessages(withCards);
      } catch (e) {
        push(e.message, 'error');
      } finally {
        setLoadingThread(false);
      }
    },
    [authed, push],
  );

  const send = useCallback(
    async (text, { retry = false } = {}) => {
      const message = text.trim();
      if (!message || sending) return;
      setSending(true);
      setFailed(null);
      try {
        let sid = activeId;
        if (!sid) {
          const created = await authed(() => chatApi.createSession());
          sid = created.session.id;
          setActiveId(sid);
          setSessions((s) => [created.session, ...s]);
        }
        if (!retry) setMessages((m) => [...m, { role: 'user', content: message, movies: [] }]);
        scrollDown();
        const data = await authed(() => chatApi.send(sid, message));
        const entry = { role: 'assistant', content: data.reply, movies: data.movies ?? [] };
        setMessages((m) => [...m, entry]);
        const userEntry = { role: 'user', content: message, movies: [] };
        threadCache.current[sid] = [...(threadCache.current[sid] ?? []), ...(retry ? [] : [userEntry]), entry];
        setInput('');
        loadSessions();
      } catch (e) {
        setFailed({ text: message, message: e.code === 'agent_unavailable' ? 'The assistant is unavailable right now.' : e.message });
      } finally {
        setSending(false);
        setTimeout(scrollDown, 50);
      }
    },
    [activeId, authed, loadSessions, sending],
  );

  // Deep links: /assistant?q=… or ?movie=<id>
  useEffect(() => {
    if (autoSent.current) return;
    const q = params.get('q');
    const movie = params.get('movie');
    if (!q && !movie) return;
    autoSent.current = true;
    const text = q ?? `Tell me about movie ${movie} and suggest similar films`;
    setInput(text);
    send(text);
    setParams({}, { replace: true });
  }, [params, send, setParams]);

  const newChat = () => {
    setActiveId(null);
    setMessages([]);
    setFailed(null);
    setInput('');
    setDrawer(false);
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <button
        onClick={newChat}
        className="m-3 rounded-md bg-crimson px-4 py-2 text-sm font-medium text-white transition hover:bg-crimson-deep"
      >
        + New conversation
      </button>
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {loadingList ? (
          <div className="space-y-2 p-2" aria-busy="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="skeleton h-10 rounded-md" />
            ))}
          </div>
        ) : !sessions.length ? (
          <p className="p-3 text-sm text-ash">No conversations yet. Start your first one.</p>
        ) : (
          sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`block w-full truncate rounded-md px-3 py-2.5 text-left text-sm transition ${
                s.id === activeId ? 'bg-seam text-parchment' : 'text-ash hover:bg-coal hover:text-parchment'
              }`}
            >
              {s.title || 'Untitled conversation'}
            </button>
          ))
        )}
      </div>
    </div>
  );

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-7xl">
      <aside className="hidden w-60 shrink-0 border-r border-line bg-coal/50 md:block">{sidebar}</aside>
      {drawer && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60 animate-fade" onClick={() => setDrawer(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-coal shadow-lift animate-fade">{sidebar}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <button
            onClick={() => setDrawer(true)}
            aria-label="Open conversations"
            className="rounded-md border border-line px-2.5 py-1.5 text-sm text-ash md:hidden"
          >
            ☰
          </button>
          <h1 className="font-display text-xl">Assistant</h1>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-[760px]">
            {!activeId && !messages.length && !sending ? (
              <div className="py-8 animate-fade">
                <p className="font-display text-3xl sm:text-4xl">What are we watching tonight?</p>
                <p className="mt-2 text-sm text-ash">Picks are grounded in the catalogue — never invented.</p>
                <div className="mt-6 grid gap-2 sm:grid-cols-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-lg border border-line bg-coal px-4 py-3 text-left text-sm transition hover:border-crimson"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : loadingThread ? (
              <div className="space-y-4" aria-busy="true">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="skeleton h-20 rounded-lg" />
                ))}
              </div>
            ) : (
              <div className="flex flex-col gap-5">
                {messages.map((m, i) =>
                  m.role === 'user' ? (
                    <div key={i} className="self-end rounded-2xl rounded-br-md bg-seam px-4 py-2.5 text-sm animate-fade">
                      {m.content}
                    </div>
                  ) : (
                    <div key={i} className="animate-fade">
                      <p className="whitespace-pre-wrap text-[15px] leading-[1.65]">{m.content}</p>
                      {m.movies?.length > 0 && (
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          {m.movies.map((card) => (
                            <MovieCard key={card.tmdb_id} movie={card} variant="compact" />
                          ))}
                        </div>
                      )}
                      <FollowUps onAsk={(label) => send(`${label} — ${m.movies?.[0]?.title ?? 'these picks'}`)} />
                    </div>
                  ),
                )}
                {sending && (
                  <div className="flex items-center gap-3 text-sm text-ash animate-fade" aria-live="polite">
                    <span className="skeleton h-4 w-4 rounded-full" />
                    Consulting the reels…
                  </div>
                )}
                {failed && (
                  <div role="alert" className="rounded-lg border border-crimson/50 bg-coal p-4 text-sm animate-fade">
                    <p>{failed.message}</p>
                    <button
                      onClick={() => send(failed.text, { retry: true })}
                      className="mt-2 rounded-md border border-line px-4 py-1.5 text-xs transition hover:border-crimson"
                    >
                      Retry
                    </button>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-line px-4 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="mx-auto flex max-w-[760px] items-end gap-2"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Ask for a recommendation…"
              aria-label="Message the assistant"
              rows={1}
              maxLength={2000}
              className="max-h-32 flex-1 resize-none rounded-lg border border-line bg-coal px-4 py-2.5 text-sm placeholder:text-ash/60 focus:border-crimson focus:outline-none"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              aria-label="Send message"
              className="rounded-lg bg-crimson px-5 py-2.5 text-sm font-medium text-white transition hover:bg-crimson-deep disabled:opacity-50"
            >
              Send
            </button>
          </form>
          <p className="mx-auto mt-1 max-w-[760px] text-right text-[11px] text-ash">{input.length}/2000</p>
        </div>
      </div>
    </div>
  );
}

export function AssistantGuarded() {
  return <Assistant />;
}
