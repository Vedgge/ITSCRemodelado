document.addEventListener('btnDeleteCreated', function () {
    const btnMostrarModal = document.querySelectorAll('.btn-delete');
    const modalDelete = document.querySelectorAll('.modal-delete');
    const btnCerrarModal = document.querySelectorAll('.cancelar-delete');
    const btnConfirmarDelete = document.querySelectorAll('.confirm-eliminar');

    console.log('btnMostrarModal:', btnMostrarModal);
    console.log('modalDelete:', modalDelete);
    console.log('btnCerrarModal:', btnCerrarModal);
    console.log('btnConfirmarDelete', btnConfirmarDelete);

    btnMostrarModal.forEach(function (btn) {
        btn.addEventListener("click", () => {
            modalDelete.forEach(function (modal) {
                modal.classList.add('active');
                if (modal.classList.contains('active')) {
                    modal.style.display = "flex";
                } else {
                    modal.style.display = "none";
                }
            });
        });
    });

    btnCerrarModal.forEach(function (Cerrar) {
        Cerrar.addEventListener('click', () => {
            modalDelete.forEach(function (modal) {
                modal.classList.remove('active');
                modal.style.display = "none";
            });
        });
    });

    btnConfirmarDelete.forEach(function(Confirmar) {
        Confirmar.addEventListener('click', () => {
            modalDelete.forEach(function(modal) {
                modal.classList.remove('active');
                modal.style.display = "none";
            });
        });
    });
});
