document.addEventListener('DOMContentLoaded', function () {
  const acordeones = document.querySelectorAll('.acordeon');

  acordeones.forEach((acordeon) => {
    const button = acordeon.querySelector('.acordeon-button'),
      content = acordeon.querySelector('.acordeon-content');

    button.addEventListener('click', () => {
      acordeon.classList.toggle('active');
      if (acordeon.classList.contains('active')) {
        content.style.maxHeight = content.scrollHeight + 'px';
      } else {
        content.style.maxHeight = '0';
      }

      acordeones.forEach((otroAcordeon) => {
        if (otroAcordeon !== acordeon) {
          otroAcordeon.classList.remove('active');
          otroAcordeon.querySelector('.acordeon-content').style.maxHeight = '0';
        }
      });

    });
  });

  const carrusels = document.querySelectorAll(".carrusel");
  // Si el usuario no opto por recuded motion, agregamos la animación
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    agregarAnimacion();
  }
  function agregarAnimacion() {
    carrusels.forEach((carrusel) => {
      // Agregar data-animated="true" a  c/.carrusel en la pag
      carrusel.setAttribute("data-animated", true);

      // Hacer un array de todos los elementos dentro de `.carrusel-inner`
      const carruselInner = carrusel.querySelector(".carrusel-inner"),
        carruselContenido = Array.from(carruselInner.children);

      // Por cada item en el array, lo clonamos
      // agrega aria-hidden al item
      // lo agrega al .carrusel-inner
      carruselContenido.forEach((item) => {
        const duplicatedItem = item.cloneNode(true);
        duplicatedItem.setAttribute("aria-hidden", true);
        carruselInner.appendChild(duplicatedItem);
      });
    });
  }

    //ANIMACIÓN SCROLL SLIDE ABAJO -> CENTRO
    const observador = new IntersectionObserver((entries) => { //Creo una clase llamada IntersectionObserver que toma una función callback en su constructor, observa varias entrys
      entries.forEach((entry) => { //Loop sobre los multiples entrys (elementos escondidos)
        if (entry.isIntersecting) { //Condicional para saber si esta intersectando el viewport, si es así le agregamos la clase mostrar
          entry.target.classList.add('mostrar');
        }
      });
    });
  
    const elEscondidos = document.querySelectorAll('.escondido'); //Selecciono todos los elemtnos que tengan la clase escondido
    elEscondidos.forEach((elemento) => observador.observe(elemento)); //Acá le decimos que observar al observador, loopea sobre todos los elementos escondidos

    const observador2 = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        entry.target.classList.add('mostrar-blur')
      });
    });
    const elEscondidos2 = document.querySelectorAll('.escondido-blur');
    elEscondidos2.forEach((elemento) => observador2.observe(elemento));
});