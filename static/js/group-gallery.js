document.addEventListener('DOMContentLoaded', () => {
  const lightbox = document.createElement('dialog');
  lightbox.className = 'group-gallery-lightbox';
  lightbox.setAttribute('aria-label', 'Expanded getaway photo');
  lightbox.innerHTML = '<button class="group-gallery-lightbox__close" type="button" aria-label="Close expanded photo">&times;</button><img class="group-gallery-lightbox__image" alt="">';
  document.body.append(lightbox);
  const lightboxImage = lightbox.querySelector('img');
  const closeLightbox = lightbox.querySelector('button');
  closeLightbox.addEventListener('click', () => lightbox.close());
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) lightbox.close();
  });

  document.querySelectorAll('[data-gallery]').forEach((gallery) => {
    const rail = gallery.querySelector('[data-gallery-rail]');
    if (!rail) return;

    const slides = [...rail.querySelectorAll('.group-gallery__slide')];
    const images = [...rail.querySelectorAll('img')];
    const dots = [...gallery.querySelectorAll('[data-gallery-dot]')];
    const previous = gallery.querySelector('[data-gallery-prev]');
    const next = gallery.querySelector('[data-gallery-next]');
    if (!slides.length || !previous || !next) return;

    const openImage = (image) => {
      lightboxImage.src = image.currentSrc || image.src;
      lightboxImage.alt = image.alt;
      lightbox.showModal();
    };
    images.forEach((image) => {
      image.addEventListener('click', () => openImage(image));
      image.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openImage(image);
        }
      });
    });

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
