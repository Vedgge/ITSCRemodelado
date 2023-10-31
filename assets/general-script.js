document.addEventListener('DOMContentLoaded', function () {
    const acordeones = document.querySelectorAll('.acordeon');

    acordeones.forEach((acordeon) => {
        const button = acordeon.querySelector('.acordeon-button'),
        content = acordeon.querySelector('.acordeon-content');
    
        button.addEventListener('click', () => {
            acordeones.forEach((otherAcordeon) => {
                if (otherAcordeon !== acordeon) {
                    otherAcordeon.classList.remove('active');
                    otherAcordeon.querySelector('.acordeon-content').style.maxHeight = '0';
                }
            });

            acordeon.classList.toggle('active');
            if (acordeon.classList.contains('active')) {
                content.style.maxHeight = content.scrollHeight + 'px';
            } else {
                content.style.maxHeight = '0';
            }
        });
    });
   
    const carrusels = document.querySelectorAll(".carrusel");

// If a user hasn't opted in for recuded motion, then we add the animation
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  addAnimation();
}

function addAnimation() {
  carrusels.forEach((carrusel) => {
    // add data-animated="true" to every `.carrusel` on the page
    carrusel.setAttribute("data-animated", true);

    // Make an array from the elements within `.carrusel-inner`
    const carruselInner = carrusel.querySelector(".carrusel-inner");
    const carruselContent = Array.from(carruselInner.children);

    // For each item in the array, clone it
    // add aria-hidden to it
    // add it into the `.carrusel-inner`
    carruselContent.forEach((item) => {
      const duplicatedItem = item.cloneNode(true);
      duplicatedItem.setAttribute("aria-hidden", true);
      carruselInner.appendChild(duplicatedItem);
    });
  });
}

});