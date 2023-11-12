document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.querySelector(".contact-form");

    formulario.addEventListener("submit", function (event) {
        if (!validarFormulario()) {
            event.preventDefault(); // Evitar que se envíe el formulario si no es válido
        }
    });

    function validarFormulario() {
        const asunto = document.getElementById("asuntoFormContacto").value;
        const nombre = document.getElementById("nombre").value;
        const email = document.getElementById("emailFormContacto").value;
        const telefono = document.getElementById("telefono").value;
        const motivoContacto = document.querySelector('input[name="select"]:checked');
        const mensaje = document.getElementById("mensaje").value;

        let esValido = true;

        if (asunto.trim() === "") {
            mostrarError("textFormContacto", "Por favor, ingrese el asunto.");
            esValido = false;
        } else {
            ocultarError("textFormContacto");
        }

        if (nombre.trim() === "") {
            mostrarError("nombreError", "Por favor, ingrese su nombre.");
            esValido = false;
        } else {
            ocultarError("nombreError");
        }

        if (email.trim() === "") {
            mostrarError("emailFormErrorContacto", "Por favor, ingrese su email.");
            esValido = false;
        } else if (!isValidEmail(email)) {
            mostrarError("emailFormErrorContacto", "Por favor, ingrese un email valido.");
            esValido = false;
        } else {
            ocultarError("emailFormErrorContacto");
        }

        if (telefono.trim() === "") {
            mostrarError("telefonoError", "Por favor, ingrese su teléfono.");
            esValido = false;
        } else if (!/^\+?\d{6,}$/.test(telefono)) {
            mostrarError("telefonoError", "Por favor, ingrese un teléfono válido.");
            esValido = false;
        } else {
            ocultarError("telefonoError");
        }

        if (mensaje.trim() === "") {
            mostrarError("mensajeError", "Por favor, ingrese su mensaje.");
            esValido = false;
        } else if (mensaje.trim().length < 15) {
            mostrarError("mensajeError", "Por favor, ingrese al menos 15 caracteres.");
            esValido = false;
        } else {
            ocultarError("mensajeError");
        }

        return esValido;
    }

    function mostrarError(elementId, mensaje) {
        const elementoError = document.getElementById(elementId);
        elementoError.textContent = mensaje;
    }

    function ocultarError(elementId) {
        const elementoError = document.getElementById(elementId);
        elementoError.textContent = "";
    }

    function isValidEmail(email) {
        const emailRegex = /^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$/;
        return emailRegex.test(email);
    }
});