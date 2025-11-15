/**
 * Unwind Africa Notification System
 * Beautiful, accessible toast notifications and modals
 */

class UnwindNotifications {
    constructor() {
        this.toastContainer = null;
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('unwind-toast-container')) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'unwind-toast-container';
            this.toastContainer.className = 'unwind-toast-container';
            document.body.appendChild(this.toastContainer);
        } else {
            this.toastContainer = document.getElementById('unwind-toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {number} duration - How long to show (ms), 0 for permanent
     */
    toast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `unwind-toast unwind-toast-${type}`;
        
        const icon = this.getIcon(type);
        
        toast.innerHTML = `
            <div class="unwind-toast-content">
                <div class="unwind-toast-icon">${icon}</div>
                <div class="unwind-toast-message">${message}</div>
                <button class="unwind-toast-close" aria-label="Close">&times;</button>
            </div>
        `;

        this.toastContainer.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('unwind-toast-show'), 10);

        // Close button
        const closeBtn = toast.querySelector('.unwind-toast-close');
        closeBtn.onclick = () => this.removeToast(toast);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.removeToast(toast), duration);
        }

        return toast;
    }

    removeToast(toast) {
        toast.classList.remove('unwind-toast-show');
        setTimeout(() => toast.remove(), 300);
    }

    success(message, duration = 5000) {
        return this.toast(message, 'success', duration);
    }

    error(message, duration = 7000) {
        return this.toast(message, 'error', duration);
    }

    warning(message, duration = 6000) {
        return this.toast(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.toast(message, 'info', duration);
    }

    /**
     * Show a loading toast
     * @param {string} message 
     * @returns {object} Toast element with update method
     */
    loading(message = 'Loading...') {
        const toast = this.toast(message, 'loading', 0);
        toast.classList.add('unwind-toast-loading');
        
        return {
            element: toast,
            update: (newMessage) => {
                toast.querySelector('.unwind-toast-message').textContent = newMessage;
            },
            success: (message) => {
                this.removeToast(toast);
                this.success(message);
            },
            error: (message) => {
                this.removeToast(toast);
                this.error(message);
            },
            close: () => {
                this.removeToast(toast);
            }
        };
    }

    /**
     * Show a confirmation dialog
     * @param {object} options - Dialog options
     * @returns {Promise} Resolves with true/false
     */
    confirm(options = {}) {
        const defaults = {
            title: 'Confirm Action',
            message: 'Are you sure?',
            confirmText: 'Confirm',
            cancelText: 'Cancel',
            confirmClass: 'danger', // 'primary', 'danger', 'success'
            onConfirm: null,
            onCancel: null
        };

        const config = { ...defaults, ...options };

        return new Promise((resolve) => {
            const modal = this.createModal({
                title: config.title,
                content: `<p style="font-size: 1rem; line-height: 1.6; color: #555;">${config.message}</p>`,
                buttons: [
                    {
                        text: config.cancelText,
                        class: 'secondary',
                        onClick: () => {
                            if (config.onCancel) config.onCancel();
                            resolve(false);
                        }
                    },
                    {
                        text: config.confirmText,
                        class: config.confirmClass,
                        onClick: () => {
                            if (config.onConfirm) config.onConfirm();
                            resolve(true);
                        }
                    }
                ]
            });
        });
    }

    /**
     * Show a custom modal dialog
     * @param {object} options - Modal options
     */
    createModal(options = {}) {
        const defaults = {
            title: '',
            content: '',
            buttons: [],
            size: 'medium', // 'small', 'medium', 'large'
            closeOnOverlay: true,
            showCloseButton: true
        };

        const config = { ...defaults, ...options };

        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'unwind-modal-overlay';
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = `unwind-modal unwind-modal-${config.size}`;
        
        let buttonsHtml = '';
        if (config.buttons.length > 0) {
            buttonsHtml = '<div class="unwind-modal-footer">';
            config.buttons.forEach(btn => {
                buttonsHtml += `<button class="unwind-btn unwind-btn-${btn.class || 'primary'}" data-action="${btn.text}">${btn.text}</button>`;
            });
            buttonsHtml += '</div>';
        }

        modal.innerHTML = `
            <div class="unwind-modal-header">
                <h3 class="unwind-modal-title">${config.title}</h3>
                ${config.showCloseButton ? '<button class="unwind-modal-close" aria-label="Close">&times;</button>' : ''}
            </div>
            <div class="unwind-modal-body">
                ${config.content}
            </div>
            ${buttonsHtml}
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Animate in
        setTimeout(() => {
            overlay.classList.add('unwind-modal-show');
        }, 10);

        // Close function
        const closeModal = () => {
            overlay.classList.remove('unwind-modal-show');
            setTimeout(() => overlay.remove(), 300);
        };

        // Close button
        if (config.showCloseButton) {
            modal.querySelector('.unwind-modal-close').onclick = closeModal;
        }

        // Overlay click
        if (config.closeOnOverlay) {
            overlay.onclick = (e) => {
                if (e.target === overlay) closeModal();
            };
        }

        // Button clicks
        config.buttons.forEach((btn, index) => {
            const btnElement = modal.querySelectorAll('[data-action]')[index];
            btnElement.onclick = () => {
                if (btn.onClick) btn.onClick();
                closeModal();
            };
        });

        return {
            element: modal,
            close: closeModal
        };
    }

    /**
     * Show an alert dialog
     * @param {string} message 
     * @param {string} type 
     * @param {string} title 
     */
    alert(message, type = 'info', title = '') {
        const titles = {
            success: title || 'Success!',
            error: title || 'Error',
            warning: title || 'Warning',
            info: title || 'Information'
        };

        return this.createModal({
            title: titles[type],
            content: `
                <div style="text-align: center; padding: 1rem 0;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">${this.getIcon(type)}</div>
                    <p style="font-size: 1rem; line-height: 1.6; color: #555;">${message}</p>
                </div>
            `,
            buttons: [
                {
                    text: 'OK',
                    class: 'primary',
                    onClick: () => {}
                }
            ]
        });
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
            loading: '<div class="unwind-spinner"></div>'
        };
        return icons[type] || icons.info;
    }
}

// Create global instance
window.notify = new UnwindNotifications();

// Shorthand methods
window.showToast = (msg, type, duration) => window.notify.toast(msg, type, duration);
window.showSuccess = (msg) => window.notify.success(msg);
window.showError = (msg) => window.notify.error(msg);
window.showWarning = (msg) => window.notify.warning(msg);
window.showInfo = (msg) => window.notify.info(msg);
window.showLoading = (msg) => window.notify.loading(msg);
window.showConfirm = (options) => window.notify.confirm(options);
window.showAlert = (msg, type, title) => window.notify.alert(msg, type, title);
