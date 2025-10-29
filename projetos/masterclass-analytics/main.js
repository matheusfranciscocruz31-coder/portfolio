document.querySelectorAll('.faq__question').forEach((button) => {
    button.addEventListener('click', () => {
        const item = button.closest('.faq__item');
        item.classList.toggle('is-open');
    });
});
