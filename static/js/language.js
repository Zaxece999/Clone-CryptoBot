document.addEventListener('DOMContentLoaded', () => {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();

  const languageCloseBtn = document.getElementById('language-close');
  const langList = document.getElementById('lang-list');

  if (window.TranslationManager) {
    window.TranslationManager.initLanguage();
  }

  function syncLanguageUI(){
    const cur = localStorage.getItem('language') || 'ru';
    langList?.querySelectorAll('.radio-btn').forEach(r => r.classList.remove('selected'));
    const sel = langList?.querySelector(`[data-lang="${cur}"] .radio-btn`);
    if (sel) sel.classList.add('selected');
  }

  langList?.querySelectorAll('.row').forEach(row => {
    row.addEventListener('click', () => {
      const code = row.getAttribute('data-lang') || 'ru';
      localStorage.setItem('language', code);

      if (window.TranslationManager) {
        window.TranslationManager.changeLanguage(code);
      }

      syncLanguageUI();
      window.navigateBack();
    });
  });

  languageCloseBtn.addEventListener('click', () => {
    window.navigateBack();
  });

  syncLanguageUI();

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.BackButton) {
    window.Telegram.WebApp.BackButton.show();
    window.Telegram.WebApp.BackButton.onClick(() => {
      if (typeof window.navigateBack === 'function') {
        window.navigateBack();
      } else if (window.parent && typeof window.parent.navigateBack === 'function') {
        window.parent.navigateBack();
      } else if (window.history && typeof window.history.back === 'function') {
        window.history.back();
      } else {
        window.location.href = '/';
      }
    });
  }
});
