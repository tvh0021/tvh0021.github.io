// Opens research figures full size in a dialog. Links still work without JS.
(() => {
  const box = document.querySelector('.lightbox');
  const img = box.querySelector('img');
  document.querySelectorAll('.zoom').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    const thumb = a.querySelector('img');
    img.src = a.href; img.alt = thumb.alt;
    // dark figures keep their dark ground; the rest sit on the light mat
    img.style.background = a.closest('.ember') ? '#1d0904' : '';
    box.showModal();
  }));
  box.addEventListener('click', () => box.close());  // click anywhere, including the image, to close
  box.addEventListener('close', () => img.removeAttribute('src'));
})();
