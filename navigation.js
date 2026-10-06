const navigationMenus = document.querySelectorAll('.nav-menu, .mobile-nav');

const normalizePath = (path) => {
  const normalized = path.replace(/\/+$/, '');
  return normalized || '/';
};

const currentPath = normalizePath(window.location.pathname);
const currentLink = [...document.querySelectorAll('[data-nav-path]')].find(
  (link) => normalizePath(new URL(link.href, window.location.href).pathname) === currentPath
);

if (currentLink) {
  currentLink.setAttribute('aria-current', 'page');
  currentLink.classList.add('is-active');
  const section = currentLink.dataset.navSection;
  if (section) {
    document.querySelectorAll(`[data-nav-menu="${section}"]`).forEach((menu) => {
      menu.classList.add('is-active');
    });
  }
}

document.querySelectorAll('.nav-menu').forEach((menu) => {
  menu.addEventListener('toggle', () => {
    if (!menu.open) return;
    document.querySelectorAll('.nav-menu').forEach((other) => {
      if (other !== menu) other.open = false;
    });
  });
});

document.addEventListener('click', (event) => {
  document.querySelectorAll('.nav-menu[open], .mobile-nav[open]').forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  navigationMenus.forEach((menu) => {
    if (!menu.open) return;
    menu.open = false;
    menu.querySelector(':scope > summary')?.focus();
  });
});

document.querySelectorAll('.nav-dropdown a, .mobile-panel a').forEach((link) => {
  link.addEventListener('click', () => {
    link.closest('details')?.removeAttribute('open');
  });
});

window.addEventListener('resize', () => {
  navigationMenus.forEach((menu) => { menu.open = false; });
});
