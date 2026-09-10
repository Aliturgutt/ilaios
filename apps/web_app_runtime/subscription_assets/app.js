(function () {
  'use strict';
  const root = document.documentElement;
  const tr = root.lang === 'tr';
  const copy = (en, turkish) => tr ? turkish : en;
  const themeButton = document.getElementById('subscription-theme');
  function theme(value) {
    const dark = value === 'dark';
    root.dataset.theme = dark ? 'dark' : 'light';
    themeButton.setAttribute('aria-pressed', String(dark));
    themeButton.textContent = dark ? copy('Light theme', 'Açık tema') : copy('Dark theme', 'Koyu tema');
  }
  try { theme(localStorage.getItem('ilaios-theme')); } catch (_) { theme('light'); }
  themeButton.addEventListener('click', () => {
    theme(root.dataset.theme === 'dark' ? 'light' : 'dark');
    try { localStorage.setItem('ilaios-theme', root.dataset.theme); } catch (_) { /* optional preference */ }
  });
  const dialog = document.getElementById('checkout');
  for (const button of document.querySelectorAll('[data-plan]')) {
    button.addEventListener('click', () => {
      document.getElementById('selected-plan').textContent = button.dataset.plan;
      document.getElementById('selected-price').textContent = button.dataset.price;
      dialog.showModal();
    });
  }
  document.getElementById('close-checkout').addEventListener('click', () => dialog.close());
  const state = document.getElementById('current-plan');
  const unavailable = () => { state.textContent = copy('Subscription information unavailable', 'Abonelik bilgisi alınamadı'); };
  fetch('/api/subscription?lang=' + root.lang, {credentials: 'same-origin', cache: 'no-store'})
    .then(async response => {
      if (response.status === 401 || response.status === 403) {
        state.textContent = copy('Sign in to view your plan', 'Planınızı görmek için giriş yapın');
        return;
      }
      if (!response.ok) { unavailable(); return; }
      const payload = await response.json();
      const current = payload.current_plan;
      if (!current || typeof current !== 'object') { unavailable(); return; }
      document.getElementById('sign-in').hidden = true;
      const states = {
        ACTIVE: copy('Active', 'Aktif'), SUSPENDED: copy('Suspended', 'Askıda'),
        CANCELLED: copy('Cancelled', 'İptal edildi'), EXPIRED: copy('Expired', 'Süresi doldu')
      };
      if (typeof current.plan_id !== 'string' || !states[current.status]) { unavailable(); return; }
      state.textContent = current.plan_id + ' · ' + states[current.status];
      const date = current.valid_until ? new Date(current.valid_until) : null;
      if (date && Number.isFinite(date.getTime())) {
        document.getElementById('period').textContent = copy('Period end: ', 'Dönem sonu: ') + date.toLocaleDateString(tr ? 'tr-TR' : 'en-US');
      }
    }).catch(unavailable);
})();
