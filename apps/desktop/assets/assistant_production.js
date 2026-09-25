'use strict';
// Authenticated, server-authoritative Assistant. No prototype state or actions.
(() => {
  const pending = new Map();
  let counter = 0, generation = 0, active = null, history = [], busy = false;
  let pendingMessageId = null;
  const $ = id => document.getElementById(id);
  const status = text => { $('status').textContent = text; };
  const buttonState = () => {
    $('send').disabled = busy;
    $('new-chat').disabled = busy;
    $('message').disabled = busy;
    document.querySelectorAll('[data-conversation]').forEach(b => b.disabled = busy);
  };
  function call(operation, args = {}) {
    const id = String(++counter);
    return new Promise((resolve, reject) => {
      pending.set(id, {resolve, reject});
      window.chrome.webview.postMessage(JSON.stringify({id, operation, args}));
    });
  }
  window.chrome.webview.addEventListener('message', event => {
    let reply;
    try { reply = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; }
    catch (_) { status('Invalid Assistant response'); return; }
    if (!reply || typeof reply.id !== 'string') return;
    const waiting = pending.get(reply.id);
    if (!waiting) return;
    pending.delete(reply.id);
    if (reply.ok) waiting.resolve(reply.data);
    else waiting.reject(Error('Assistant request failed. Retry or sign in again.'));
  });
  function renderHistory() {
    $('history').replaceChildren();
    history.forEach((item, index) => {
      if (typeof item.conversation_id !== 'string') return;
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.conversation = item.conversation_id;
      button.textContent = 'Conversation ' + (history.length - index);
      button.setAttribute('aria-current', active?.conversation_id === item.conversation_id ? 'true' : 'false');
      button.disabled = busy;
      button.addEventListener('click', () => select(item.conversation_id));
      $('history').append(button);
    });
  }
  function renderConversation() {
    $('messages').replaceChildren();
    const messages = Array.isArray(active?.messages) ? active.messages : [];
    for (const message of messages) {
      const item = document.createElement('div');
      item.className = 'feature-bubble';
      const heading = document.createElement('b');
      heading.textContent = message.role === 'user' ? 'You' : 'Assistant';
      const body = document.createElement('p');
      body.textContent = typeof message.text === 'string' ? message.text : 'Unverified message';
      item.append(heading, body);
      $('messages').append(item);
    }
  }
  async function refresh() {
    const result = await call('list');
    if (!Array.isArray(result.conversations)) throw Error('Invalid history');
    history = result.conversations;
    renderHistory();
  }
  async function select(id) {
    if (busy) return;
    busy = true; buttonState();
    const current = ++generation;
    try {
      const result = await call(id ? 'get' : 'create', id ? {conversation_id: id} : {});
      if (current !== generation) return;
      if (!result.conversation || typeof result.conversation.conversation_id !== 'string') throw Error('Invalid conversation');
      active = result.conversation;
      pendingMessageId = null;
      $('message').value = '';
      renderConversation();
      await refresh();
      status('Authenticated conversation');
    } catch (error) { status(error.message); }
    finally {busy = false; buttonState();}
  }
  $('new-chat').addEventListener('click', () => select(null));
  $('composer').addEventListener('submit', async event => {
    event.preventDefault();
    const text = $('message').value.trim();
    if (busy || !text) return;
    busy = true; buttonState();
    try {
      if (!active) {
        const created = await call('create');
        active = created.conversation;
      }
      pendingMessageId ||= window.crypto.randomUUID();
      const result = await call('send', {
        conversation_id: active.conversation_id, version: active.version,
        text, message_id: pendingMessageId, locale: document.documentElement.lang === 'en' ? 'en' : 'tr'
      });
      if (!result.conversation || result.conversation.conversation_id !== active.conversation_id) throw Error('Invalid response');
      active = result.conversation;
      pendingMessageId = null;
      $('message').value = '';
      renderConversation();
      await refresh();
      status('Message saved by Assistant');
    } catch (error) {status(error.message + ' Your draft is retained.');}
    finally {busy = false; buttonState();}
  });
  (async () => {
    busy = true; buttonState();
    try {
      await refresh();
      if (history.length) {
        const first = await call('get', {conversation_id: history[0].conversation_id});
        active = first.conversation;
        renderConversation();
      }
      status('Authenticated Assistant ready');
    } catch (error) {status(error.message);}
    finally {busy = false; buttonState();}
  })();
})();

