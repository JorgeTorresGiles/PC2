// Comportamiento de interfaz sencillo (semana 2: DOM y eventos)
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert-close').forEach(button => {
    button.addEventListener('click', () => button.closest('.alert')?.remove());
  });
  document.querySelectorAll('[data-toggle-password]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  const menu = document.getElementById('menuToggle');
  menu?.addEventListener('click', () => document.getElementById('sidebar')?.classList.toggle('open'));
});
