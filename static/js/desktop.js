(function () {
  try {
    if (!window.Desktop || !window.Desktop.isElectron) return;
    document.body.dataset.desktop = 'true';

    function bind(id, fn) {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fn();
      });
    }

    bind('winMinBtn', () => window.Desktop.minimize());
    bind('winMaxBtn', () => window.Desktop.toggleMaximize());
    bind('winCloseBtn', () => window.Desktop.close());
  } catch (e) {
    console.warn('desktop controls init failed', e);
  }
})();
