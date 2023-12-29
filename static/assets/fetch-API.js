// Obtén una referencia al contenedor donde mostrarás los datos
const contenedorTestimonios = document.querySelector(".contenedor-testimonios-alumnos");

// URL de la API que deseas llamar
const apiUrl = "https://randomuser.me/api/?results=1";
const commentsPath = "/static/assets/opiniones.json"

// Realiza una solicitud a la API de comentarios
fetch(commentsPath)
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error en la solicitud de comentarios: ${response.status}`);
        }
        return response.json();
    })
    .then(commentsData => {
        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error en la solicitud de usuarios: ${response.status}`);
                }
                return response.json();
            })
            .then(userData => {
                const users = userData.results;
                const shuffledComments = shuffle(commentsData.comentarios);

                if (users && users.length > 0) {
                    users.forEach(user => {
                        const contenedorAlumno = document.querySelector(".contenedor-alumno");
                        const contenedorQuoteAlumno = contenedorTestimonios.querySelector(".contenedor-quote-alumno");
                        const contenedorQuoteText = contenedorQuoteAlumno.querySelector(".text-quote");                                                
                        

                        const userImage = document.createElement("img");
                        userImage.src = user.picture.large;
                        contenedorAlumno.appendChild(userImage); 

                        const quotesLeft = document.createElement("i");
                        quotesLeft.classList.add("fa-solid");
                        quotesLeft.classList.add("fa-quote-left");
                        contenedorQuoteText.appendChild(quotesLeft);

                        const alumnoTestimonio = document.createElement("span");
                        alumnoTestimonio.textContent = shuffledComments.pop();
                        contenedorQuoteText.appendChild(alumnoTestimonio);

                        const quotesRight = document.createElement("i");
                        quotesRight.classList.add("fa-solid");
                        quotesRight.classList.add("fa-quote-right");
                        contenedorQuoteText.appendChild(quotesRight);

                        const alumnoName = document.createElement("h4");
                        alumnoName.textContent = `— ${user.name.first} ${user.name.last}`;
                        contenedorQuoteAlumno.appendChild(alumnoName);

                        contenedorTestimonios.appendChild(contenedorAlumno);
                        contenedorTestimonios.appendChild(contenedorQuoteAlumno);
                    });
                } else {
                    testimoniosContenedor.textContent = "No se encontraron datos.";
                }
            })
            .catch(error => {
                console.log(error);
            });
    })
    .catch(error => {
        console.log(error);
    });

function shuffle(array) {
    let currentIndex = array.length, randomIndex, temporaryValue;
    while (currentIndex !== 0) {
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;
        temporaryValue = array[currentIndex];
        array[currentIndex] = array[randomIndex];
        array[randomIndex] = temporaryValue;
    }
    return array;
}