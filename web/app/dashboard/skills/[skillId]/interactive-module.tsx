'use client';

// Client island: streaming chat against the AI mentor for an INTERACTIVE section.
// Consumes the SSE proxy exposed by the Core API at POST /chat/stream.

import { useState } from 'react';

type Msg = { role: 'user' | 'assistant'; content: string };

export function InteractiveModule({
  sectionId,
  skillId,
}: {
  sectionId: string;
  skillId: string;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);

  async function send() {
    if (!draft.trim() || streaming) return;
    const history = messages;
    const userMsg: Msg = { role: 'user', content: draft };
    setMessages((m) => [...m, userMsg, { role: 'assistant', content: '' }]);
    setDraft('');
    setStreaming(true);

    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        sessionId: `${skillId}:${sectionId}`,
        sectionId,
        message: userMsg.content,
        history,
      }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value).split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') continue;
        const evt = JSON.parse(payload);
        if (evt.delta) {
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1].content += evt.delta;
            return next;
          });
        }
      }
    }
    setStreaming(false);
  }

  return (
    <section className="mt-8 rounded-lg border p-4">
      <div className="space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            <span className="inline-block whitespace-pre-wrap rounded bg-muted px-3 py-2">
              {m.content || (streaming && i === messages.length - 1 ? '…' : '')}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask your mentor…"
          disabled={streaming}
        />
        <button className="rounded bg-black px-4 py-2 text-white" onClick={send} disabled={streaming}>
          Send
        </button>
      </div>
    </section>
  );
}
