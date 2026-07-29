class UserManager {
    constructor() {
        this.userId = null;
        this.init();
    }

    init() {

        this.userId = this.getUserId();
        console.log('UserManager initialized with user_id:', this.userId);
    }

    getUserId() {

        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
            const tgUser = window.Telegram.WebApp.initDataUnsafe.user;
            if (tgUser && tgUser.id) {
                console.log('Got user_id from Telegram WebApp:', tgUser.id);
                return tgUser.id.toString();
            }
        }

        const urlParams = new URLSearchParams(window.location.search);
        const urlUserId = urlParams.get('user_id');
        if (urlUserId) {
            console.log('Got user_id from URL params:', urlUserId);
            return urlUserId;
        }

        const localUserId = localStorage.getItem('user_id');
        if (localUserId) {
            console.log('Got user_id from localStorage:', localUserId);
            return localUserId;
        }

        const sessionUserId = sessionStorage.getItem('user_id');
        if (sessionUserId) {
            console.log('Got user_id from sessionStorage:', sessionUserId);
            return sessionUserId;
        }

        const bodyUserId = document.body.getAttribute('data-user-id');
        if (bodyUserId) {
            console.log('Got user_id from body data attribute:', bodyUserId);
            return bodyUserId;
        }

        const htmlUserId = document.documentElement.getAttribute('data-user-id');
        if (htmlUserId) {
            console.log('Got user_id from html data attribute:', htmlUserId);
            return htmlUserId;
        }

        const metaUserId = document.querySelector('meta[name="user-id"]');
        if (metaUserId && metaUserId.content) {
            console.log('Got user_id from meta tag:', metaUserId.content);
            return metaUserId.content;
        }

        const fallbackUserId = '1';
        console.log('Using fallback user_id:', fallbackUserId);
        return fallbackUserId;
    }

    getUserId() {
        return this.userId;
    }

    setUserId(userId) {
        this.userId = userId;

        localStorage.setItem('user_id', userId);
        console.log('User ID set to:', userId);
    }

    getUserData() {
        return {
            user_id: this.userId,
            timestamp: Date.now()
        };
    }

    async makeApiCall(endpoint, data = {}) {
        const requestData = {
            ...data,
            ...this.getUserData()
        };

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

window.userManager = new UserManager();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserManager;
}
