console.log('=== VERIFICATION JS LOADED ===');
console.log('Verification JavaScript file loaded!');
console.log('Current time:', new Date().toISOString());

if (window.Telegram && window.Telegram.WebApp) {
  console.log('Initializing Telegram WebApp...');
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  console.log('Telegram WebApp initialized');
} else {
  console.log('Telegram WebApp not available');
}

function getIconSVG(iconType) {
  const icons = {
    phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>',
    document: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14,2 14,8 20,8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10,9 9,9 8,9"></polyline>',
    location: '<path d="M18 10C18 16 12 20 12 20C12 20 6 16 6 10C6 6.68629 8.68629 4 12 4C15.3137 4 18 6.68629 18 10Z"></path><circle cx="12" cy="10" r="2"></circle>',
    video: '<path d="M23 7l-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>'
  };
  return icons[iconType] || icons.phone;
}

async function getUserVerificationStatus() {
  try {
    const userId = getCurrentUserId();
    const response = await fetch(`/api/verification/status/${userId}`);
    if (response.ok) {
      const payload = await response.json();
      return payload && payload.status ? payload.status : payload;
    }
  } catch (error) {
    console.error('Error getting verification status:', error);
  }

  return {
    phone_verified: false,
    documents_uploaded: false,
    address_verified: false,
    video_verified: false,
    verification_complete: false
  };
}

async function initializeVerificationItems() {
  console.log('=== INITIALIZING VERIFICATION ITEMS ===');

  const verificationList = document.querySelector('.list');
  console.log('Verification list element:', verificationList);

  if (!verificationList) {
    console.log('List not found, will try again on DOMContentLoaded');
    return false;
  }

  verificationList.innerHTML = '';

  const userVerificationStatus = await getUserVerificationStatus();
  console.log('User verification status:', userVerificationStatus);

  const verificationItems = [
    {
      id: 'phone-verification',
      title: 'Подтверждение номера телефона',
      description: 'Подтвердите ваш номер телефона через Telegram',
      icon: 'phone',
      modal: 'phone-verification-modal',
      status: userVerificationStatus.phone_verified ? 'completed' : 'available',
      class: userVerificationStatus.phone_verified ? 'completed' : ''
    },
    {
      id: 'document-verification',
      title: 'Загрузка документов',
      description: 'Загрузите фото документов для подтверждения личности',
      icon: 'document',
      modal: 'document-upload-modal',
      status: userVerificationStatus.documents_verified ? 'completed' :
              userVerificationStatus.documents_verification_pending ? 'pending' :
              userVerificationStatus.documents_uploaded ? 'completed' :
              userVerificationStatus.phone_verified ? 'available' : 'locked',
      class: userVerificationStatus.documents_verified ? 'completed' :
             userVerificationStatus.documents_verification_pending ? 'pending' :
             userVerificationStatus.documents_uploaded ? 'completed' : ''
    },
    {
      id: 'address-verification',
      title: 'Адрес проживания',
      description: 'Укажите ваш адрес проживания',
      icon: 'location',
      modal: 'address-verification-modal',
      status: userVerificationStatus.address_verified ? 'completed' :
              userVerificationStatus.documents_uploaded || userVerificationStatus.documents_verified ? 'available' : 'locked',
      class: userVerificationStatus.address_verified ? 'address-verified' : ''
    },
    {
      id: 'video-verification',
      title: 'Видеоверификация',
      description: 'Пройдите видеопроверку для завершения верификации',
      icon: 'video',
      modal: 'video-verification-modal',
      status: userVerificationStatus.video_verified ? 'completed' :
              userVerificationStatus.video_verification_pending ? 'pending' :
              userVerificationStatus.address_verified ? 'available' : 'locked',
      class: userVerificationStatus.video_verified ? 'completed' :
             userVerificationStatus.video_verification_pending ? 'pending' : ''
    }
  ];

  verificationItems.forEach((item, index) => {
    const listItem = document.createElement('li');
    listItem.className = `itemWrapper ${item.status} ${item.class}`;
    listItem.setAttribute('data-modal', item.modal);
    listItem.setAttribute('data-step', index);

    listItem.innerHTML = `
      <div class="itemIcon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          ${getIconSVG(item.icon)}
        </svg>
      </div>
      <div class="itemContent">
        <div class="itemTitle">${item.title}</div>
        <div class="itemDescription">${item.description}</div>
        <div class="progress-indicator"></div>
      </div>
      <div class="itemStatus">
        ${item.status === 'completed' ?
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20,6 9,17 4,12"></polyline></svg>' :
          item.status === 'pending' ?
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>' :
          item.status === 'locked' ?
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><circle cx="12" cy="16" r="1"></circle><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>' :
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9,18 15,12 9,6"></polyline></svg>'
        }
      </div>
    `;

    verificationList.appendChild(listItem);
  });

  verificationList.style.display = 'flex';
  verificationList.style.flexDirection = 'column';
  verificationList.style.gap = '8px';
  verificationList.style.listStyle = 'none';
  verificationList.style.margin = '0';
  verificationList.style.padding = '0';
  verificationList.style.background = 'transparent';
  verificationList.style.visibility = 'visible';
  verificationList.style.opacity = '1';

  console.log('Verification items created successfully. Count:', verificationList.children.length);

  const itemsCount = document.getElementById('items-count');
  if (itemsCount) {
    itemsCount.textContent = verificationList.children.length;
  }

  const listItems = verificationList.querySelectorAll('li');
  listItems.forEach((item, index) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();

      const itemTitle = item.querySelector('.itemTitle')?.textContent;
      const itemStatus = item.classList.contains('available') ? 'available' :
                        item.classList.contains('completed') ? 'completed' : 'locked';
      const modalId = item.getAttribute('data-modal');

      console.log(`Clicked verification item: ${itemTitle} (${itemStatus})`);

      item.style.transform = 'scale(0.98)';
      item.style.transition = 'transform 0.1s ease';

      setTimeout(() => {
        item.style.transform = '';
        item.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
      }, 100);

      if (itemStatus === 'available') {

        if (modalId) {
          openModal(modalId);
        }
      } else if (itemStatus === 'locked') {

        item.style.transform = 'scale(0.95)';
        setTimeout(() => {
          item.style.transform = '';
        }, 150);

        showToast('Вы не прошли предыдущие этапы верификации', 'warning');
      } else if (itemStatus === 'completed') {

        item.style.transform = 'scale(1.02)';
        setTimeout(() => {
          item.style.transform = '';
        }, 200);

        showToast(`${itemTitle} уже завершена`, 'success');
      }
    });

    item.addEventListener('mouseenter', () => {
      if (!item.classList.contains('available')) {
        item.style.cursor = 'not-allowed';
      }
    });

    item.addEventListener('mouseleave', () => {
      item.style.cursor = '';
    });
  });

  return true;
}

if (document.readyState === 'loading') {
  console.log('Document still loading, will wait for DOMContentLoaded');
} else {
  console.log('Document already loaded, initializing immediately');
  initializeVerificationItems().catch(console.error);
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('=== VERIFICATION PAGE DEBUG ===');
  console.log('Verification page DOM loaded');
  console.log('Document body:', document.body);
  console.log('Document head:', document.head);
  console.log('Current URL:', window.location.href);
  console.log('Telegram WebApp available:', !!(window.Telegram && window.Telegram.WebApp));
  console.log('Verification list element exists:', !!document.querySelector('.list'));
  console.log('All elements in body:', document.body.innerHTML.length);

  initializeVerificationItems().then(initialized => {
    console.log('Verification items initialized:', initialized);
  }).catch(error => {
    console.error('Error initializing verification items:', error);
  });

  const debugInfo = document.getElementById('debug-info');
  const listStatus = document.getElementById('list-status');
  const itemsCount = document.getElementById('items-count');
  const listElement = document.querySelector('.list');

  if (debugInfo) {
    debugInfo.style.display = 'block';
  }
  if (listStatus) {
    listStatus.textContent = listElement ? 'YES' : 'NO';
  }
  if (itemsCount) {
    itemsCount.textContent = listElement ? listElement.children.length : '0';
  }

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {

      const bgColor = tg.backgroundColor || '#ffffff';
      const textColor = tg.textColor || '#000000';

      document.body.style.background = bgColor;
      document.body.style.color = textColor;

      const verificationPage = document.querySelector('.verification-page');
      if (verificationPage) {
        verificationPage.style.background = bgColor;
        verificationPage.style.color = textColor;
      }

      document.documentElement.style.setProperty('--bg-color', bgColor);
      document.documentElement.style.setProperty('--text-primary-color', textColor);

      const isDark = bgColor === '#222729' || bgColor === '#000000' ||
                     (bgColor.startsWith('#') && parseInt(bgColor.slice(1), 16) < 0x808080);

      if (isDark) {
        document.body.classList.add('telegram', 'dark');
        if (verificationPage) {
          verificationPage.classList.add('telegram', 'dark');
        }
      } else {
        document.body.classList.add('telegram', 'light');
        if (verificationPage) {
          verificationPage.classList.add('telegram', 'light');
        }
      }

      console.log('Applied Telegram theme:', { bgColor, textColor, isDark });
    } catch (e) {
      console.warn('Failed to apply Telegram theme:', e);
    }
  }

  const existingCSS = document.querySelector('link[href*="verification.css"]');
  if (!existingCSS) {
    console.log('Loading verification.css...');
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/css/verification.css';
    document.head.appendChild(link);
  }

  const existingBaseCSS = document.querySelector('link[href*="style.css"]');
  if (!existingBaseCSS) {
    console.log('Loading style.css...');
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/css/style.css';
    document.head.appendChild(link);
  }

function setupBackButton() {
  console.log('Setting up BackButton...');
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.BackButton) {
      try {
        window.Telegram.WebApp.BackButton.show();
        window.Telegram.WebApp.BackButton.onClick(() => {
        console.log('BackButton clicked');
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
      console.log('BackButton setup complete');
      } catch (error) {
      console.warn('BackButton setup failed:', error);
    }
  } else {
    console.warn('BackButton not available');
  }
}

  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
    setupBackButton();
  }

  const verificationList = document.querySelector('.list');
  console.log('Final verification list check:', verificationList);
  if (verificationList) {
    console.log('List items count:', verificationList.children.length);
    console.log('List styles:', verificationList.style.cssText);
  }

  const listItems = document.querySelectorAll('.list li');
  listItems.forEach((item, index) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();

      const itemTitle = item.querySelector('.itemTitle')?.textContent;
      const itemStatus = item.classList.contains('available') ? 'available' :
                        item.classList.contains('completed') ? 'completed' : 'locked';
      const modalId = item.getAttribute('data-modal');

      console.log(`Clicked verification item: ${itemTitle} (${itemStatus})`);

      item.style.transform = 'scale(0.98)';
      item.style.transition = 'transform 0.1s ease';

      setTimeout(() => {
        item.style.transform = '';
        item.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
      }, 100);

      if (itemStatus === 'available') {

        if (modalId) {
          openModal(modalId);
        }
      } else if (itemStatus === 'locked') {

        item.style.transform = 'scale(0.95)';
        setTimeout(() => {
          item.style.transform = '';
        }, 150);

        showToast('Вы не прошли предыдущие этапы верификации', 'warning');
      } else if (itemStatus === 'completed') {

        item.style.transform = 'scale(1.02)';
        setTimeout(() => {
          item.style.transform = '';
        }, 200);

        showToast(`${itemTitle} уже завершена`, 'success');
      }
    });

    item.addEventListener('mouseenter', () => {
      if (!item.classList.contains('available')) {
        item.style.cursor = 'not-allowed';
      }
    });

    item.addEventListener('mouseleave', () => {
      item.style.cursor = '';
    });
  });

  function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      top: '12px',
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      zIndex: '9999',
      pointerEvents: 'none',
      width: 'min(92%, 480px)'
    });
    document.body.appendChild(container);
  }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
  const bg = type === 'success' ? 'var(--color-good)'
           : type === 'warning' ? 'var(--color-warning)'
           : type === 'error'   ? 'var(--color-bad)'
           : 'var(--color-primary)';

    Object.assign(toast.style, {
    background: bg,
      color: 'white',
    padding: '10px 14px',
    borderRadius: '10px',
      fontSize: '14px',
      fontWeight: '500',
    boxShadow: '0 6px 18px rgba(0, 0, 0, 0.25)',
      opacity: '0',
    transform: 'translateY(-10px)',
    transition: 'opacity 200ms ease, transform 200ms ease',
    textAlign: 'center',
    pointerEvents: 'auto'
  });

  while (container.children.length >= 4) {
    container.removeChild(container.firstElementChild);
  }

  container.appendChild(toast);

  requestAnimationFrame(() => {
      toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  const ttl = type === 'error' ? 4000 : type === 'warning' ? 3500 : 3000;
  const close = () => {
      toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.parentNode && toast.parentNode.removeChild(toast), 220);
  };
  const t = setTimeout(close, ttl);
  toast.addEventListener('click', () => { clearTimeout(t); close(); });
  }

  const stars = document.querySelectorAll('.star');
  stars.forEach((star, index) => {
    star.addEventListener('click', () => {
      console.log(`Star ${index + 1} clicked`);
      star.style.transform = 'scale(1.5)';
      setTimeout(() => {
        star.style.transform = '';
      }, 300);
    });
  });

  console.log('Verification page initialized successfully');

  setTimeout(() => {
    const listItems = document.querySelectorAll('.list li');
    console.log('Fallback check - list items count:', listItems.length);

    if (listItems.length === 0) {
      console.log('No items found, trying fallback creation...');
      createVerificationItemsFallback();
    }
  }, 1000);
});

function createVerificationItemsFallback() {
  console.log('=== FALLBACK VERIFICATION ITEMS CREATION ===');

  const container = document.querySelector('.container');
  if (!container) {
    console.error('Container not found in fallback');
    return;
  }

  const existingList = container.querySelector('.list');
  if (existingList) {
    existingList.remove();
  }

  const list = document.createElement('ul');
  list.className = 'list hideDivider';
  list.style.display = 'flex';
  list.style.flexDirection = 'column';
  list.style.gap = '8px';
  list.style.listStyle = 'none';
  list.style.margin = '0';
  list.style.padding = '0';

  const items = [
    {
      title: 'Подтверждение номера телефона',
      description: 'Подтвердите ваш номер телефона через Telegram',
      status: 'available'
    },
    {
      title: 'Загрузка документов',
      description: 'Загрузите фото документов для подтверждения личности',
      status: 'locked'
    },
    {
      title: 'Адрес проживания',
      description: 'Укажите ваш адрес проживания',
      status: 'locked'
    },
    {
      title: 'Видеоверификация',
      description: 'Пройдите видеопроверку для завершения верификации',
      status: 'locked'
    }
  ];

  items.forEach((item, index) => {
    const li = document.createElement('li');
    li.className = `itemWrapper ${item.status}`;
    li.style.display = 'flex';
    li.style.alignItems = 'center';
    li.style.padding = '16px';
    li.style.background = 'rgba(255, 255, 255, 0.05)';
    li.style.borderRadius = '12px';
    li.style.border = '1px solid rgba(255, 255, 255, 0.1)';
    li.style.cursor = 'pointer';
    li.style.marginBottom = '8px';

    li.innerHTML = `
      <div style="width: 40px; height: 40px; background: #44a3dd; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
        <span style="color: white; font-weight: bold;">${index + 1}</span>
      </div>
      <div style="flex: 1;">
        <div style="font-weight: 600; color: white; margin-bottom: 4px;">${item.title}</div>
        <div style="font-size: 14px; color: rgba(255, 255, 255, 0.7);">${item.description}</div>
      </div>
      <div style="color: ${item.status === 'available' ? '#44a3dd' : '#666'};">
        ${item.status === 'available' ? '→' : '🔒'}
      </div>
    `;

    li.addEventListener('click', () => {
      if (item.status === 'available') {
        alert(`Открываем: ${item.title}`);
      } else {
        alert('Вы не прошли предыдущие этапы верификации');
      }
    });

    list.appendChild(li);
  });

  container.appendChild(list);
  console.log('Fallback items created successfully');

  const itemsCount = document.getElementById('items-count');
  if (itemsCount) {
    itemsCount.textContent = list.children.length;
  }
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {

    const openModals = document.querySelectorAll('.modal.show');
    openModals.forEach(openModal => {
      if (openModal.id !== modalId) {
        closeModal(openModal.id);
      }
    });

    modal.style.display = 'flex';
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';

    const firstInput = modal.querySelector('input, button, textarea, select');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }

    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        closeModal(modalId);
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);

    console.log(`Modal ${modalId} opened`);

    if (modalId === 'phone-verification-modal') {
      try {
        updateVerificationStatus('phone_verification_pending', {});
      } catch (e) {
        console.warn('Failed to set phone_verification_pending:', e);
      }
    }

    if (modalId === 'document-upload-modal') {
      setTimeout(() => {
        setupDocumentUpload();
      }, 100);
    }
  } else {
    console.error(`Modal with id ${modalId} not found`);
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('show');

    const form = modal.querySelector('form');
    if (form) {
      form.reset();
    }

    const fileInputs = modal.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
      input.value = '';
    });

    const uploadAreas = modal.querySelectorAll('.upload-area');
    uploadAreas.forEach(area => {
      area.classList.remove('has-file');
      const placeholder = area.querySelector('.upload-placeholder p');
      const hint = area.querySelector('.upload-hint');
      if (placeholder && hint) {
        placeholder.textContent = placeholder.getAttribute('data-original-text') || 'Документ спереди';
        hint.textContent = 'Нажмите для загрузки';
      }
    });

    const submitBtns = modal.querySelectorAll('button[type="submit"], .btn-primary');
    submitBtns.forEach(btn => {
      if (btn.id === 'submit-documents-btn') {
        btn.disabled = true;
      }
    });

    setTimeout(() => {
      modal.style.display = 'none';
      document.body.style.overflow = '';
      console.log(`Modal ${modalId} closed`);
    }, 300);
  } else {
    console.error(`Modal with id ${modalId} not found`);
  }
}

function confirmPhoneVerification() {
  if (window.Telegram && window.Telegram.WebApp) {

    window.Telegram.WebApp.requestContact((contact) => {
      if (contact) {

        updateVerificationStatus('phone_verified', { phone_number: contact.phone_number })
          .then(() => {
            closeModal('phone-verification-modal');
            completeVerificationStep(0);
            showToast('Номер телефона подтвержден!', 'success');

            setTimeout(() => {
              updateVerificationStatus('documents_verification_pending', {});
              initializeVerificationItems();
            }, 300);
          })
          .catch((error) => {
            console.error('Error updating phone verification:', error);
            showToast('Ошибка при подтверждении номера', 'error');
          });
      }
    });
  } else {

    const phoneNumber = prompt('Введите ваш номер телефона:');
    if (phoneNumber) {
      updateVerificationStatus('phone_verified', { phone_number: phoneNumber })
        .then(() => {
          closeModal('phone-verification-modal');
          completeVerificationStep(0);
          showToast('Номер телефона подтвержден!', 'success');
          setTimeout(() => {
            updateVerificationStatus('documents_verification_pending', {});
            initializeVerificationItems();
          }, 300);
        })
        .catch((error) => {
          console.error('Error updating phone verification:', error);
          showToast('Ошибка при подтверждении номера', 'error');
        });
    }
  }
}

function setupDocumentUpload() {
  console.log('Setting up document upload...');

  const frontUpload = document.getElementById('front-document-upload');
  const backUpload = document.getElementById('back-document-upload');
  const frontInput = document.getElementById('front-document');
  const backInput = document.getElementById('back-document');
  const submitBtn = document.getElementById('submit-documents-btn');

  console.log('Document upload elements:', {
    frontUpload: !!frontUpload,
    backUpload: !!backUpload,
    frontInput: !!frontInput,
    backInput: !!backInput,
    submitBtn: !!submitBtn
  });

  if (!frontUpload || !backUpload || !frontInput || !backInput || !submitBtn) {
    console.error('Document upload elements not found');
    return;
  }

  function updateSubmitState() {
    const hasFront = !!frontInput.files && !!frontInput.files[0];
    const hasBack = !!backInput.files && !!backInput.files[0];
    submitBtn.disabled = !(hasFront && hasBack);
    console.log('updateSubmitState:', { hasFront, hasBack, disabled: submitBtn.disabled });
  }

  const frontPlaceholder = frontUpload.querySelector('.upload-placeholder p');
  if (frontPlaceholder && !frontPlaceholder.getAttribute('data-original-text')) {
    frontPlaceholder.setAttribute('data-original-text', frontPlaceholder.textContent);
  }
  const backPlaceholder = backUpload.querySelector('.upload-placeholder p');
  if (backPlaceholder && !backPlaceholder.getAttribute('data-original-text')) {
    backPlaceholder.setAttribute('data-original-text', backPlaceholder.textContent);
  }

  const newFrontUpload = frontUpload.cloneNode(true);
  const newBackUpload = backUpload.cloneNode(true);
  frontUpload.parentNode.replaceChild(newFrontUpload, frontUpload);
  backUpload.parentNode.replaceChild(newBackUpload, backUpload);

  newFrontUpload.addEventListener('click', () => frontInput.click());
  newBackUpload.addEventListener('click', () => backInput.click());

  function handleFileUpload(event, uploadArea) {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      updateSubmitState();
      return;
    }

    if (!file.type || !file.type.startsWith('image/')) {
      showToast('Пожалуйста, выберите изображение', 'warning');
      event.target.value = '';
      updateSubmitState();
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showToast('Размер файла не должен превышать 5MB', 'warning');
      event.target.value = '';
      updateSubmitState();
      return;
    }

    uploadArea.classList.add('has-file');
    const ph = uploadArea.querySelector('.upload-placeholder p');
    const hint = uploadArea.querySelector('.upload-hint');
    if (ph) ph.textContent = file.name;
    if (hint) hint.textContent = 'Файл загружен';

    updateSubmitState();

    if (!submitBtn.disabled) {
      showToast('Оба документа загружены. Можно отправить.', 'success');
    }
  }

  frontInput.addEventListener('change', (e) => handleFileUpload(e, newFrontUpload));
  backInput.addEventListener('change', (e) => handleFileUpload(e, newBackUpload));

  frontInput.addEventListener('input', updateSubmitState);
  backInput.addEventListener('input', updateSubmitState);

  updateSubmitState();

  console.log('Document upload setup complete');
}

function submitDocuments() {
  const frontFile = document.getElementById('front-document').files[0];
  const backFile = document.getElementById('back-document').files[0];

  if (!frontFile || !backFile) {
    showToast('Пожалуйста, загрузите оба документа', 'warning');
    return;
  }

  const userId = getCurrentUserId();
  const formData = new FormData();
  formData.append('user_id', userId);
  formData.append('front_document', frontFile);
  formData.append('back_document', backFile);

  showToast('Загружаем документы...', 'info');

  fetch('/api/verification/upload-documents', {
    method: 'POST',
    body: formData
  })
    .then(async (res) => {
      if (!res.ok) throw new Error('Upload failed');
      return res.json();
    })
    .then(() => {
      closeModal('document-upload-modal');
      completeVerificationStep(1);
      showToast('Документы загружены! Ожидайте проверки администратором.', 'success');

      setTimeout(() => {
        updateVerificationStatus('documents_verification_pending', {});
        initializeVerificationItems();
      }, 1000);
    })
    .catch((error) => {
      console.error('Error uploading documents:', error);
      showToast('Ошибка при загрузке документов', 'error');
    });
}

function submitAddress() {
  const country = document.getElementById('country').value;
  const city = document.getElementById('city').value;
  const address = document.getElementById('address').value;
  const postalCode = document.getElementById('postal-code').value;

  if (!country || !city || !address) {
    showToast('Пожалуйста, заполните все обязательные поля', 'warning');
    return;
  }

  const addressData = {
    country,
    city,
    address,
    postal_code: postalCode
  };

  updateVerificationStatus('address_verified', addressData)
    .then(() => {
      closeModal('address-verification-modal');
      completeVerificationStep(2);
      showToast('Адрес подтвержден! Ожидайте проверки.', 'success');
      setTimeout(() => {
        initializeVerificationItems();
      }, 1000);
    })
    .catch((error) => {
      console.error('Error updating address:', error);
      showToast('Ошибка при подтверждении адреса', 'error');
    });
}

if (typeof mediaRecorder === 'undefined') {
    var mediaRecorder;
}
if (typeof recordedChunks === 'undefined') {
    var recordedChunks = [];
}

function startVideoVerification() {
  navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then((stream) => {
      const video = document.getElementById('video-preview');
      const startBtn = document.querySelector('button[onclick="startVideoVerification()"]');
      const stopBtn = document.getElementById('stop-video-btn');

      video.srcObject = stream;
      video.style.display = 'block';

      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        submitVideoVerification(blob);
      };

      mediaRecorder.start();

      startBtn.style.display = 'none';
      stopBtn.style.display = 'inline-block';

      showToast('Запись началась. Следуйте инструкциям на экране.', 'info');
    })
    .catch((error) => {
      console.error('Error accessing camera:', error);
      showToast('Ошибка доступа к камере', 'error');
    });
}

function stopVideoVerification() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();

    const video = document.getElementById('video-preview');
    if (video.srcObject) {
      video.srcObject.getTracks().forEach(track => track.stop());
    }

    showToast('Обрабатываем видео...', 'info');
  }
}

function submitVideoVerification(videoBlob) {
  const formData = new FormData();
  formData.append('video', videoBlob, 'verification-video.webm');

  updateVerificationStatus('video_verified', { video_file: 'verification-video.webm' })
    .then(() => {
      closeModal('video-verification-modal');
      completeVerificationStep(3);
      showToast('Видеоверфикация завершена! Ожидайте проверки.', 'success');
      checkAllVerificationComplete();
      setTimeout(() => {
        initializeVerificationItems();
      }, 1000);
    })
    .catch((error) => {
      console.error('Error submitting video:', error);
      showToast('Ошибка при обработке видео', 'error');
    });
}

function updateVerificationStatus(status, data = {}) {
  return fetch('/api/verification/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      status,
      data,
      user_id: getCurrentUserId()
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  });
}

async function updateVerificationStatus(status, data = {}) {
  try {
    const userId = getCurrentUserId();
    const response = await fetch('/api/verification/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        status: status,
        data: data
      })
    });

    if (response.ok) {
      const result = await response.json();
      console.log('Verification status updated:', result);
      return true;
    } else {
      const error = await response.json();
      console.error('Failed to update verification status:', error);
      return false;
    }
  } catch (error) {
    console.error('Error updating verification status:', error);
    return false;
  }
}

function getCurrentUserId() {

  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
    return window.Telegram.WebApp.initDataUnsafe.user?.id;
  }
  return localStorage.getItem('user_id') || 'demo_user';
}

function completeVerificationStep(stepIndex) {
  const listItems = document.querySelectorAll('.list li');
  const currentItem = listItems[stepIndex];

  if (currentItem) {
    currentItem.classList.remove('available', 'loading');
    currentItem.classList.add('completed');

    const progressIndicator = currentItem.querySelector('.progress-indicator');
    if (progressIndicator) {
      progressIndicator.style.width = '100%';
      progressIndicator.style.transition = 'width 1s cubic-bezier(0.4, 0, 0.2, 1)';
    }

    const nextItem = currentItem.nextElementSibling;
    if (nextItem && nextItem.classList.contains('locked')) {
      setTimeout(() => {
        nextItem.classList.remove('locked');
        nextItem.classList.add('available');
        const nextProgressIndicator = nextItem.querySelector('.progress-indicator');
        if (nextProgressIndicator) {
          nextProgressIndicator.style.width = '0%';
        }
        showToast('Следующий этап верификации разблокирован!', 'info');
      }, 1000);
    }
  }
}

function checkAllVerificationComplete() {
  const completedItems = document.querySelectorAll('.itemWrapper.completed');
  const totalItems = document.querySelectorAll('.itemWrapper').length;

  if (completedItems.length === totalItems) {
    const subtitle = document.getElementById('verification-subtitle');
    if (subtitle) {
      subtitle.textContent = 'Вы верифицированы!';
      subtitle.style.color = 'var(--color-good)';
      subtitle.style.fontWeight = 'var(--font-weight-semibold)';
    }
    showToast('Поздравляем! Верификация полностью завершена!', 'success');
  }
}

document.addEventListener('DOMContentLoaded', function() {

  setTimeout(() => {
  setupDocumentUpload();
  }, 500);

  document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
      closeModal(event.target.id);
    }
  });

  document.addEventListener('click', function(event) {
    if (event.target.closest('.modal-content')) {
      event.stopPropagation();
    }
  });

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      const openModal = document.querySelector('.modal.show');
      if (openModal) {
        closeModal(openModal.id);
      }
    }
  });
});

window.verificationPage = {
  init: function() {
    console.log('Verification page external init');
  },

  showBenefits: function() {
    const list = document.querySelector('.list');
    if (list) {
      list.style.display = 'flex';
    }
  },

  hideBenefits: function() {
    const list = document.querySelector('.list');
    if (list) {
      list.style.display = 'none';
    }
  },

  openModal: openModal,
  closeModal: closeModal
};
