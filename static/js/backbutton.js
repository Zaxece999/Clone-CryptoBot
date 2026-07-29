function setupUniversalBackButton() {
  console.log('Setting up universal BackButton...');

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.BackButton) {
    try {
      window.Telegram.WebApp.BackButton.show();
      window.Telegram.WebApp.BackButton.onClick(() => {
        console.log('Universal BackButton clicked');

        if (typeof window.navigateBack === 'function') {
          window.navigateBack();
        } else if (window.parent && typeof window.parent.navigateBack === 'function') {
          window.parent.navigateBack();
        } else if (window.history && typeof window.history.back === 'function') {
          window.history.back();
        } else if (window.parent && typeof window.parent.showMainPage === 'function') {
          window.parent.showMainPage();
        } else if (typeof window.showMainPage === 'function') {
          window.showMainPage();
        } else {

          window.location.href = '/';
        }
      });
      console.log('Universal BackButton setup complete');
    } catch (error) {
      console.warn('Universal BackButton setup failed:', error);
    }
  } else {
    console.warn('Universal BackButton not available');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupUniversalBackButton);
} else {
  setupUniversalBackButton();
}
