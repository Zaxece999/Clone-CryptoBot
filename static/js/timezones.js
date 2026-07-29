document.addEventListener('DOMContentLoaded', () => {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();

  const timezonesCloseBtn = document.getElementById('timezones-close');
  const tzSearch = document.getElementById('tz-search');
  const tzList = document.getElementById('tz-list');

  if (window.TranslationManager) {
    window.TranslationManager.initLanguage();
  }

  function getTimezones(){
    const zones = (Intl.supportedValuesOf ? Intl.supportedValuesOf('timeZone') : []) || [];
    return zones.length ? zones : [ 'UTC' ];
  }

  function tzOffsetString(tz){
    try{
      const dt = new Date();
      const fmt = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour12:false, hour:'2-digit', minute:'2-digit' });
      const parts = fmt.formatToParts(dt);
      const utc = new Date(dt.toLocaleString('en-US', { timeZone:'UTC' }));
      const local = new Date(dt.toLocaleString('en-US', { timeZone: tz }));
      const diffMin = Math.round((local.getTime() - utc.getTime())/60000);
      const sign = diffMin>=0 ? '+' : '-';
      const abs = Math.abs(diffMin);
      const hh = String(Math.floor(abs/60)).padStart(2,'0');
      const mm = String(abs%60).padStart(2,'0');
      return `GMT${sign}${hh}:${mm}`;
    }catch(e){ return 'GMT+00:00'; }
  }

  function renderTimezones(filter=''){
    if (!tzList) return;
    tzList.innerHTML = '';
    const zones = getTimezones().filter(z => z.toLowerCase().includes(filter.toLowerCase()));
    zones.slice(0, 600).forEach(z => {
      const li = document.createElement('li');
      li.className = 'row';
      li.setAttribute('data-tz', z);
      const off = tzOffsetString(z);
      li.innerHTML = `<div class="left"><div class="labels"><div class="sym">${off}</div><div class="sub">${z}</div></div></div><div class="chev">○</div>`;
      li.addEventListener('click', () => {
        localStorage.setItem('timezone', z);

        window.navigateBack();
      });
      tzList.appendChild(li);
    });
  }

  timezonesCloseBtn.addEventListener('click', () => {
    window.navigateBack();
  });

  tzSearch.addEventListener('input', () => renderTimezones(tzSearch.value));

  renderTimezones();

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
