const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const code = readFileSync(join(__dirname, '../subscription_assets/app.js'), 'utf8');
const styles = readFileSync(join(__dirname, '../subscription_assets/styles.css'), 'utf8');

async function render({lang = 'tr', response, fail = false, storageFails = false} = {}) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      textContent: '', hidden: false, dataset: {}, attributes: {}, events: {},
      setAttribute(name, value) { this.attributes[name] = value; },
      addEventListener(name, callback) { this.events[name] = callback; },
      showModal() { this.open = true; }, close() { this.open = false; },
    });
    return elements.get(id);
  }
  const plan = element('plan');
  plan.dataset = {plan: 'PRO', price: '$49 / month'};
  const root = {lang, dataset: {}};
  let request;
  vm.runInNewContext(code, {
    document: {documentElement: root, getElementById: element, querySelectorAll: () => [plan]},
    localStorage: {
      getItem: () => { if (storageFails) throw Error('denied'); return null; },
      setItem: () => { if (storageFails) throw Error('denied'); },
    },
    fetch: async (url, options) => {
      request = {url, options};
      if (fail) throw Error('offline');
      return response || {status: 403};
    },
  });
  await new Promise(resolve => setImmediate(resolve));
  return {element, root, request};
}

test('TR defaults light, EN labels and same-origin session reads', async () => {
  for (const lang of ['tr', 'en']) {
    const view = await render({lang, storageFails: true});
    assert.equal(view.root.dataset.theme, 'light');
    assert.equal(view.request.options.credentials, 'same-origin');
    assert.equal(view.request.options.cache, 'no-store');
    assert.equal(view.element('current-plan').textContent, lang === 'tr' ? 'Planınızı görmek için giriş yapın' : 'Sign in to view your plan');
    const visibleLabel = lang === 'tr' ? 'Tema' : 'Theme';
    assert.equal(view.element('theme-label').textContent, visibleLabel);
    view.element('subscription-theme').events.click();
    assert.equal(view.root.dataset.theme, 'dark');
    assert.equal(view.element('subscription-theme').attributes['aria-pressed'], 'true');
    assert.equal(view.element('theme-label').textContent, visibleLabel);
  }
});

test('canonical website theme and language control geometry is locked', () => {
  assert.match(styles, /\.preferences\{display:flex;align-items:center;gap:7px\}/);
  assert.match(styles, /\.theme-control\{box-sizing:border-box;[^}]*gap:7px;[^}]*min-height:36px;[^}]*padding:6px 10px;[^}]*border:1px solid var\(--line\);[^}]*border-radius:999px/);
  assert.match(styles, /\.theme-icon\{font-size:\.95rem/);
  assert.match(styles, /\.theme-label\{font-size:\.78rem/);
  assert.match(styles, /\.language-control\{box-sizing:border-box;[^}]*min-height:36px;[^}]*border:1px solid var\(--line\);[^}]*border-radius:999px/);
  assert.match(styles, /@media\(max-width:660px\)\{[^}]*\.theme-control\{width:36px;min-width:36px;min-height:36px;padding:5px;justify-content:center\}\.theme-label\{display:none\}/);
});

test('account action cards stay proportionate on desktop and release forced height on smaller layouts', () => {
  assert.match(styles, /\.account-actions-grid\{display:grid;[^}]*align-items:stretch/);
  assert.match(styles, /\.account-actions-grid \.current,\.account-actions-grid \.management\{margin:0;height:100%;min-height:220px\}/);
  assert.match(styles, /\.management\{display:flex;flex-direction:column;/);
  assert.match(styles, /\.management \.muted\{margin-bottom:auto\}/);
  assert.match(styles, /@media\(max-width:1050px\)\{[^}]*\.account-actions-grid\{grid-template-columns:1fr\}\.account-actions-grid \.current,\.account-actions-grid \.management\{min-height:0\}/);
});

test('dark brand raster blends its black field into the dark header', () => {
  assert.match(styles, /html\[data-theme=dark\] \.page-header \.brand-image-dark\{display:block;mix-blend-mode:screen\}/);
  assert.doesNotMatch(styles, /gradient/i);
});

test('unknown, malformed and offline states never claim an active plan', async () => {
  for (const options of [
    {fail: true}, {response: {status: 503}},
    {response: {status: 200, ok: true, json: async () => ({})}},
    {response: {status: 200, ok: true, json: async () => ({current_plan: {status: 'UNKNOWN'}})}},
  ]) {
    const view = await render(options);
    assert.equal(view.element('current-plan').textContent, 'Abonelik bilgisi alınamadı');
  }
});

test('verified projection uses text nodes, never HTML execution', async () => {
  const view = await render({lang: 'en', response: {status: 200, ok: true, json: async () => ({
    current_plan: {plan_id: '<img src=x onerror=alert(1)>', status: 'ACTIVE', valid_until: '2026-10-01T00:00:00Z'},
  })}});
  assert.equal(view.element('current-plan').textContent, '<img src=x onerror=alert(1)> · Active');
  assert.equal(view.element('sign-in').hidden, true);
  assert.match(view.element('period').textContent, /Period end:/);
});

test('plan selection opens only a summary, with no payment request', async () => {
  const view = await render();
  const originalRequest = view.request;
  view.element('plan').events.click();
  assert.equal(view.element('checkout').open, true);
  assert.equal(view.element('selected-plan').textContent, 'PRO');
  assert.equal(view.request, originalRequest);
  view.element('close-checkout').events.click();
  assert.equal(view.element('checkout').open, false);
});
