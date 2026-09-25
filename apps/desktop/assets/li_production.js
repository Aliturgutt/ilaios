'use strict';
// Li production: server-authoritative, no demo records or local persisted secrets.
(() => {
 const $ = id => document.getElementById(id);
 const pending = new Map(); let counter = 0, busy = false, active = null;
 let history = [], pendingMessageId = null, generation = 0;
 const status = value => { $('status').textContent = value; };
 const lock = value => { busy = value; for (const id of ['send','new-chat','remember','show-memory']) $(id).disabled = value; };
 const call = (operation, args = {}) => new Promise((resolve, reject) => {
   const id = String(++counter); pending.set(id, {resolve,reject});
   window.chrome.webview.postMessage(JSON.stringify({id,operation,args}));
 });
 window.chrome.webview.addEventListener('message', event => {
   let reply; try { reply = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; }
   catch (_) { status('Invalid Li response'); return; }
   const waiting = pending.get(reply?.id); if (!waiting) return;
   pending.delete(reply.id);
   if (reply.ok) waiting.resolve(reply.data); else waiting.reject(Error('Li request failed; retry or sign in again'));
 });
 const renderHistory = () => {
   $('history').replaceChildren();
   history.forEach((item, index) => {
     const button = document.createElement('button'); button.type = 'button';
     button.textContent = 'Conversation ' + (history.length-index);
     button.disabled = busy;
     button.addEventListener('click', () => select(item.conversation_id));
     $('history').append(button);
   });
 };
 const renderConversation = () => {
   $('memories').hidden = true; $('memory-form').hidden = true; $('messages').hidden = false;
   $('messages').replaceChildren();
   for (const message of active?.messages || []) {
     const card = document.createElement('div'); card.className = 'li-card';
     const heading = document.createElement('strong'); heading.textContent = message.role === 'user' ? 'You' : 'Li';
     const body = document.createElement('p'); body.textContent = typeof message.text === 'string' ? message.text : 'Unverified message';
     card.append(heading,body); $('messages').append(card);
   }
 };
 async function refresh() { const result = await call('list'); history = result.conversations; renderHistory(); }
 async function select(id) {
   if (busy) return; lock(true); const current = ++generation;
   try {
     const result = await call(id ? 'get' : 'create', id ? {conversation_id:id} : {});
     if (current !== generation) return;
     active = result.conversation; pendingMessageId = null; $('message').value = '';
     renderConversation(); await refresh(); status('Authenticated Li conversation');
   } catch (error) {status(error.message);} finally {lock(false);}
 }
 $('new-chat').addEventListener('click', () => select(null));
 $('composer').addEventListener('submit', async event => {
   event.preventDefault(); const text = $('message').value.trim(); if (busy || !text) return;
   lock(true);
   try {
     if (!active) active = (await call('create')).conversation;
     pendingMessageId ||= window.crypto.randomUUID();
     const result = await call('send', {conversation_id:active.conversation_id,
       version:active.version,text,message_id:pendingMessageId,
       locale:document.documentElement.lang === 'en' ? 'en' : 'tr'});
     active = result.conversation; pendingMessageId = null; $('message').value = '';
     renderConversation(); await refresh(); status('Li message saved');
   } catch(error) {status(error.message + '; draft retained');} finally {lock(false);}
 });
 $('show-memory').addEventListener('click', async () => {
   if (busy) return; lock(true);
   try {
     const result = await call('memories'); $('memories').replaceChildren();
     for (const memory of result.memories) {
       const card = document.createElement('div'); card.className = 'li-card';
       const title = document.createElement('strong'); title.textContent = memory.kind + ' · ' + memory.source;
       const content = document.createElement('p'); content.textContent = memory.content;
       card.append(title,content); $('memories').append(card);
     }
     $('messages').hidden = true; $('memories').hidden = false; $('memory-form').hidden = false;
     status('Founder memory');
   } catch(error) {status(error.message);} finally {lock(false);}
 });
 $('memory-form').addEventListener('submit', async event => {
   event.preventDefault(); if (busy) return;
   const content = $('memory-content').value.trim(); if (!content) return;
   lock(true);
   try {
     await call('remember',{kind:$('memory-kind').value,content});
     $('memory-content').value = ''; const result = await call('memories');
     $('memories').replaceChildren();
     for (const memory of result.memories) {
       const card = document.createElement('div'); card.className = 'li-card';
       const title = document.createElement('strong'); title.textContent = memory.kind + ' · ' + memory.source;
       const body = document.createElement('p'); body.textContent = memory.content;
       card.append(title,body); $('memories').append(card);
     }
     status('Memory saved by Li service');
   } catch(error) {status(error.message + '; draft retained');} finally {lock(false);}
 });
 (async () => {lock(true); try {
   await refresh(); if (history.length) {
     active = (await call('get',{conversation_id:history[0].conversation_id})).conversation;
     renderConversation();
   } status('Authenticated founder session');
 } catch(error) {status(error.message);} finally {lock(false);}})();
})();