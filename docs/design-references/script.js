(() => {
    const card = document.querySelector('[data-card]');
    document.querySelectorAll('[data-switch]').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            card.dataset.mode = link.dataset.switch;
            document.querySelectorAll('[data-panel]').forEach((panel) => {
                panel.setAttribute('aria-hidden', String(panel.dataset.panel !== link.dataset.switch));
            });
        });
    });

    document.querySelectorAll('[data-password]').forEach((button) => {
        const input = document.getElementById(button.dataset.password);
        button.addEventListener('click', () => {
            const visible = input.type === 'password';
            input.type = visible ? 'text' : 'password';
            button.textContent = visible ? 'Hide' : 'Show';
            button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
        });
    });
})();
