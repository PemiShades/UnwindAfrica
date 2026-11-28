document.addEventListener('DOMContentLoaded', () => {
  const panel = document.getElementById('package-booking');
  const select = document.querySelector('[data-open-booking]');
  if (!panel || !select) return;

  select.addEventListener('click', (event) => {
    event.preventDefault();
    panel.open = true;
    panel.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
});
