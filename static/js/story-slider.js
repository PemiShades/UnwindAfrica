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
      let frame = 0;

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

      const goTo = (index) => {
        const target = slides[(index + slides.length) % slides.length];
        const left = target.getBoundingClientRect().left - viewport.getBoundingClientRect().left + viewport.scrollLeft;
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        viewport.scrollTo({ left, behavior: reduceMotion ? 'auto' : 'smooth' });
        setActive((index + slides.length) % slides.length);
      };

      const syncActiveToScroll = () => {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          const viewportLeft = viewport.getBoundingClientRect().left;
          let closestIndex = 0;
          let closestDistance = Infinity;
          slides.forEach((slide, index) => {
            const distance = Math.abs(slide.getBoundingClientRect().left - viewportLeft);
            if (distance < closestDistance) {
              closestDistance = distance;
              closestIndex = index;
            }
          });
          if (closestIndex !== activeIndex) setActive(closestIndex);
        });
      };

      dots.forEach((dot, index) => dot.addEventListener('click', () => goTo(index)));
      previous?.addEventListener('click', () => goTo(activeIndex - 1));
      next?.addEventListener('click', () => goTo(activeIndex + 1));
      viewport.addEventListener('scroll', syncActiveToScroll, { passive: true });
      viewport.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          goTo(activeIndex - 1);
        } else if (event.key === 'ArrowRight') {
          event.preventDefault();
          goTo(activeIndex + 1);
        }
      });
      window.addEventListener('resize', () => goTo(activeIndex), { passive: true });
      setActive(0);
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initStorySliders);
  else initStorySliders();
})();
