(() => {
  const initStorySliders = () => {
    document.querySelectorAll('[data-story-slider]').forEach((slider) => {
      const viewport = slider.querySelector('[data-story-viewport]');
      const slides = Array.from(slider.querySelectorAll('[data-story-slide]'));
      const dots = Array.from(slider.querySelectorAll('[data-story-dot]'));
      const count = slider.querySelector('[data-story-count]');
      const previous = slider.querySelector('[data-story-prev]');
      const next = slider.querySelector('[data-story-next]');
      if (!viewport || slides.length < 2) return;

      let activeIndex = 0;
      let timer;
      let touchStart;
      const interval = 8000;

      const setActive = (index) => {
        activeIndex = (index + slides.length) % slides.length;
        slides.forEach((slide, slideIndex) => {
          const isActive = slideIndex === activeIndex;
          slide.toggleAttribute('inert', !isActive);
          if (isActive) slide.removeAttribute('aria-hidden');
          else slide.setAttribute('aria-hidden', 'true');
        });
        dots.forEach((dot, dotIndex) => {
          if (dotIndex === activeIndex) dot.setAttribute('aria-current', 'true');
          else dot.removeAttribute('aria-current');
        });
        if (count) {
          const current = String(activeIndex + 1).padStart(2, '0');
          const total = String(slides.length).padStart(2, '0');
          count.innerHTML = `${current} <span>/ ${total}</span>`;
        }
      };

      const goTo = (index, restartAuto = true) => {
        setActive(index);
        if (restartAuto) startAuto();
      };

      const startAuto = () => {
        window.clearInterval(timer);
        if (!document.hidden && !slider.matches(':hover') && !slider.contains(document.activeElement)) {
          timer = window.setInterval(() => setActive(activeIndex + 1), interval);
        }
      };

      const stopAuto = () => window.clearInterval(timer);

      dots.forEach((dot, index) => dot.addEventListener('click', () => goTo(index)));
      previous?.addEventListener('click', () => goTo(activeIndex - 1));
      next?.addEventListener('click', () => goTo(activeIndex + 1));

      viewport.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          goTo(activeIndex - 1);
        } else if (event.key === 'ArrowRight') {
          event.preventDefault();
          goTo(activeIndex + 1);
        }
      });

      viewport.addEventListener('pointerdown', (event) => {
        stopAuto();
        touchStart = { x: event.clientX, y: event.clientY };
      }, { passive: true });
      viewport.addEventListener('pointerup', (event) => {
        if (!touchStart) {
          startAuto();
          return;
        }
        const deltaX = event.clientX - touchStart.x;
        const deltaY = event.clientY - touchStart.y;
        touchStart = null;
        if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY)) {
          goTo(activeIndex + (deltaX < 0 ? 1 : -1));
        } else startAuto();
      }, { passive: true });
      viewport.addEventListener('pointercancel', () => { touchStart = null; startAuto(); }, { passive: true });

      slider.addEventListener('mouseenter', stopAuto);
      slider.addEventListener('mouseleave', startAuto);
      slider.addEventListener('focusin', stopAuto);
      slider.addEventListener('focusout', (event) => {
        if (!slider.contains(event.relatedTarget)) startAuto();
      });
      document.addEventListener('visibilitychange', () => document.hidden ? stopAuto() : startAuto());

      setActive(0);
      startAuto();
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initStorySliders);
  else initStorySliders();
})();
