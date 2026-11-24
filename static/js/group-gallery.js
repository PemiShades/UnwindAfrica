document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-gallery]').forEach((gallery) => {
    const rail = gallery.querySelector('[data-gallery-rail]');
    if (!rail) return;

    const slides = [...rail.querySelectorAll('.group-gallery__slide')];
    const dots = [...gallery.querySelectorAll('[data-gallery-dot]')];
    const previous = gallery.querySelector('[data-gallery-prev]');
    const next = gallery.querySelector('[data-gallery-next]');
    if (!slides.length || !previous || !next) return;

    let ticking = false;
    const activeIndex = () => {
      const railLeft = rail.getBoundingClientRect().left;
      return slides.reduce((best, slide, index) => {
        const slideLeft = Math.abs(slide.getBoundingClientRect().left - railLeft);
        const bestLeft = Math.abs(slides[best].getBoundingClientRect().left - railLeft);
        return slideLeft < bestLeft ? index : best;
      }, 0);
    };

    const update = () => {
      const index = activeIndex();
      dots.forEach((dot, dotIndex) => {
        dot.setAttribute('aria-current', String(index === dotIndex));
      });
      previous.disabled = index === 0;
      next.disabled = index === slides.length - 1;
      ticking = false;
    };

    const goTo = (index) => {
      slides[index].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
    };

    rail.addEventListener('scroll', () => {
      if (ticking) return;
      window.requestAnimationFrame(update);
      ticking = true;
    }, { passive: true });
    previous.addEventListener('click', () => goTo(Math.max(0, activeIndex() - 1)));
    next.addEventListener('click', () => goTo(Math.min(slides.length - 1, activeIndex() + 1)));
    dots.forEach((dot, index) => dot.addEventListener('click', () => goTo(index)));
    update();
  });
});
