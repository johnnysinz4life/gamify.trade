// Simple ripple effect for .btn / button elements
document.addEventListener('click', function(e){
  const btn = e.target.closest('button, .btn');
  if(!btn) return;
  const ripple = document.createElement('span');
  ripple.className = 'gb-ripple';
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.2;
  ripple.style.width = ripple.style.height = size + 'px';
  ripple.style.left = (e.clientX - rect.left - size/2) + 'px';
  ripple.style.top = (e.clientY - rect.top - size/2) + 'px';
  btn.appendChild(ripple);
  setTimeout(()=> ripple.remove(), 700);
});

// Add keyboard-accessible activation effect
document.addEventListener('keydown', function(e){
  if(e.key === 'Enter' || e.key === ' ') {
    const el = document.activeElement;
    if(el && (el.matches('button') || el.classList.contains('btn'))) {
      const evt = new MouseEvent('click', {bubbles:true, clientX: el.getBoundingClientRect().left + 5, clientY: el.getBoundingClientRect().top + 5});
      el.dispatchEvent(evt);
    }
  }
});
