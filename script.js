// Load site includes (header/footer)
async function loadInclude(id, path) {
  const el = document.getElementById(id);
  if (!el) return;
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error('Failed to load ' + path);
    el.innerHTML = await res.text();
    // After insert: wire up menu button and active link highlighting
    wireNavBehavior();
    highlightActiveNav();
  } catch (e) {
    console.warn('Include load failed:', e);
  }
}

// Wire nav behaviors that expect DOM elements inside the include
function wireNavBehavior() {
  const menuBtn = document.getElementById('menu-button');
  if (menuBtn) {
    menuBtn.addEventListener('click', toggleFunction);
  }
  // Ensure mobile nav closes after clicking a link
  document.querySelectorAll('#navDemo a').forEach(a => {
    a.addEventListener('click', () => {
      const nav = document.getElementById('navDemo');
      if (nav && nav.className.indexOf('w3-show') !== -1) nav.className = nav.className.replace(' w3-show', '');
    });
  });
}

// highlight current page in nav by matching location
function highlightActiveNav() {
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('[data-link]').forEach(el => {
    if (el.getAttribute('data-link') === path) {
      el.classList.add('w3-dark-grey');
    } else {
      el.classList.remove('w3-dark-grey');
    }
  });
}

// Modal Image Gallery (keeps existing behavior)
function onClick(element) {
  var img = document.getElementById("img01");
  var captionText = document.getElementById("caption");
  if (!img || !captionText) return;
  img.src = element.src;
  captionText.innerHTML = element.alt || "";
  var modal = document.getElementById("modal01");
  if (modal) modal.style.display = "block";
}

// Change style of navbar on scroll
window.onscroll = function () { myFunction(); };

function myFunction() {
  var navbar = document.getElementById("myNavbar");
  if (!navbar) return;
  if (document.body.scrollTop > 100 || document.documentElement.scrollTop > 100) {
    navbar.className = "w3-bar w3-card w3-animate-top w3-white";
  } else {
    navbar.className = "w3-bar";
  }
}

// Toggle mobile nav
function toggleFunction() {
  var x = document.getElementById("navDemo");
  if (!x) return;
  if (x.className.indexOf("w3-show") == -1) {
    x.className += " w3-show";
    x.setAttribute('aria-hidden', 'false');
  } else {
    x.className = x.className.replace(" w3-show", "");
    x.setAttribute('aria-hidden', 'true');
  }
}

// DOM ready: load includes
document.addEventListener('DOMContentLoaded', function () {
  loadInclude('site-header', '/inc/header.html');
  loadInclude('site-footer', '/inc/footer.html');
});