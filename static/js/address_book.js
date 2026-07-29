document.addEventListener('DOMContentLoaded', () => {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();

  const addressCloseBtn = document.getElementById('address-close');

  addressCloseBtn.addEventListener('click', () => {
    window.navigateBack();
  });

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
