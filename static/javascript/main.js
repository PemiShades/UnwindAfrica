// const slides = document.querySelectorAll('.carousel-slide');
const prevBtn = document.querySelector('.carousel-button.prev');
const nextBtn = document.querySelector('.carousel-button.next');
const dotContainer = document.getElementById('carousel-dots');
const hamburgerBtn = document.querySelector('.hamburger-btn') || document.querySelector('.hamburger-btn-dark');
const hamburgerCloseBtn = document.querySelector('.hamburger_close_btn');
const hamburgerMenu = document.querySelector('.hamburger-menu');


const navImg = document.querySelector('.mid_nav_img');
const menuLinks = document.querySelectorAll('.hamburger-menu a');
// const closeBtn = document.querySelector('.hamburger_close_btn');




// modal for home page

function openModal(img, title, desc) {
    document.getElementById("modalImage").src = "{% static 'images/home/marquee_section/' %}" + img;
    document.getElementById("modalTitle").innerText = title;
    document.getElementById("modalDesc").innerText = desc;
    document.getElementById("cardModal").classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

function closeModal() {
  document.getElementById("cardModal").classList.add("hidden");
  document.body.style.overflow = "auto";
}

// end of modal for home page








// Close on link click
  const iconWrappers = document.querySelectorAll("#package-icons-container .icon-wrapper");
  // Now, we select ALL elements with the 'package-content-pane' class.
  // This will include both the text description divs AND the image divs.
  const allContentPanes = document.querySelectorAll(".package-content-pane");

  function showPackage(targetId) {
     // Hide all content panes (both text and image)
     allContentPanes.forEach((pane) => {
        pane.classList.remove("active", "block", "opacity-100", "flex"); // Remove 'flex' too for images
        pane.classList.add("hidden", "opacity-0");
     });

     // Show the target content panes (both text and image)
     const targetTextPane = document.getElementById(targetId);
     const targetImagePane = document.getElementById(targetId + "-image"); // Find the corresponding image pane

     if (targetTextPane) {
        targetTextPane.classList.remove("hidden", "opacity-0");
        targetTextPane.classList.add("active", "block", "opacity-100");
     }
     if (targetImagePane) {
        // Image panes use 'flex' for alignment, not 'block'
        targetImagePane.classList.remove("hidden", "opacity-0");
        targetImagePane.classList.add("active", "flex", "opacity-100");
     }
  }

  function setActiveIcon(clickedIconWrapper) {
     // Remove 'active' class from all icon wrappers
     iconWrappers.forEach((iconWrapper) => {
        iconWrapper.classList.remove("active", "bg-white/5");
        // Small icon images remain static, no src change here.
     });

     // Add 'active' class to the clicked icon
     clickedIconWrapper.classList.add("active", "bg-white/5");
  }

  // Add click event listener to each icon wrapper
  iconWrappers.forEach((iconWrapper) => {
     iconWrapper.addEventListener("click", function () {
        const targetId = this.dataset.target; // Get the target ID (e.g., 'package-sunflower')

        setActiveIcon(this); // Update active icon style
        showPackage(targetId); // Show corresponding content panes (text and image)
     });
  });

  // Initialize: Ensure the correct icon states and content are set on page load
  const initialActiveIcon = document.querySelector("#package-icons-container .icon-wrapper.active");
  if (initialActiveIcon) {
     // Set the active style for the initial icon (already done by HTML 'active' class)
     // No need to change small icon image src as they are static

     // Ensure the main content and images are loaded for the initial active package
     const initialTargetId = initialActiveIcon.dataset.target;
     showPackage(initialTargetId); // Call this to load initial text and image panes
  }
// hamburgerCloseBtn.addEventListener('click',()=>{
//   hamburgerMenu.style.visibility = 'hidden';
// })
// hamburgerBtn.addEventListener('click',()=>{
//   hamburgerMenu.style.visibility = 'visible';
// })
// menuLinks.forEach(link => {
//   link.addEventListener('click', () => {
//     hamburgerMenu.classList.remove('show');
//   });
// });
// let currentIndex = 0;
// const totalSlides = slides.length;

// // Create dots
// for (let i = 0; i < totalSlides; i++) {
//   const dot = document.createElement('button');
//   dot.classList.add('carousel-dot');
//   if (i === 0) dot.classList.add('active');
//   dot.addEventListener('click', () => goToSlide(i));
//   dotContainer.appendChild(dot);
// }

// // const dots = document.querySelectorAll('.carousel-dot');

// goToSlide(0);
// function goToSlide(index) {
//   slides[currentIndex].classList.remove('active');
//   dots[currentIndex].classList.remove('active');
//   currentIndex = index;
//   slides[currentIndex].classList.add('active');
//   dots[currentIndex].classList.add('active');
// }

// function showNextSlide() {
//   let nextIndex = (currentIndex + 1) % totalSlides;
//   goToSlide(nextIndex);
// }

// function showPrevSlide() {
//   let prevIndex = (currentIndex - 1 + totalSlides) % totalSlides;
//   goToSlide(prevIndex);
// }

// // nextBtn.addEventListener('click', showNextSlide);
// // prevBtn.addEventListener('click', showPrevSlide);

// setInterval(showNextSlide, 5000); // Auto-slide every 5s

// // Swipe support
// let startX = 0;
// const carousel = document.getElementById('carousel');

// carousel.addEventListener('touchstart', (e) => {
//   startX = e.touches[0].clientX;
// });

// carousel.addEventListener('touchend', (e) => {
//   const endX = e.changedTouches[0].clientX;
//   if (startX - endX > 50) {
//     showNextSlide();
//   } else if (endX - startX > 50) {
//     showPrevSlide();
//   }
// });

document.addEventListener("DOMContentLoaded", function () {
});
