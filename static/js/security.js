document.addEventListener('DOMContentLoaded', () => {
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

  if (tg) {
    tg.ready();
    tg.expand();

    if (tg.BackButton) {
      tg.BackButton.show();
      tg.BackButton.onClick(() => {
        if (window.parent && window.parent.showMainPage) {
          window.parent.showMainPage();
        } else if (window.showMainPage) {
          window.showMainPage();
        } else {
          window.history.back();
        }
      });
    }
  }

  const securityCloseBtn = document.getElementById('security-close');
  if (securityCloseBtn) {
    securityCloseBtn.addEventListener('click', () => {
      if (window.parent && window.parent.showMainPage) {
        window.parent.showMainPage();
      } else if (window.showMainPage) {
        window.showMainPage();
      } else {
        window.history.back();
      }
    });
  }

  const backupEmailRow = document.getElementById('backup-email-row');
  if (backupEmailRow) {
    backupEmailRow.addEventListener('click', () => {
      console.log('Edit backup email clicked');

      alert('Функция редактирования резервной почты будет реализована');
    });
  }

  const changePasscodeRow = document.getElementById('change-passcode-row');
  if (changePasscodeRow) {
    changePasscodeRow.addEventListener('click', () => {
      console.log('Change passcode clicked');

      alert('Функция изменения кода-пароля будет реализована');
    });
  }

  const deletePasscodeRow = document.getElementById('delete-passcode-row');
  if (deletePasscodeRow) {
    deletePasscodeRow.addEventListener('click', () => {
      console.log('Delete passcode clicked');
      const confirmed = confirm('Вы уверены, что хотите удалить код-пароль?');
      if (confirmed) {

        alert('Код-пароль удален');
      }
    });
  }

  const endSessionsRow = document.getElementById('end-sessions-row');
  if (endSessionsRow) {
    endSessionsRow.addEventListener('click', () => {
      console.log('End all sessions clicked');
      const confirmed = confirm('Вы уверены, что хотите завершить все сеансы?');
      if (confirmed) {

        alert('Все сеансы завершены');
      }
    });
  }
});
