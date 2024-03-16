# ITSCRemodelado
Este repositorio contiene un experimetno de remodelado de ITSC que tiene un website que parece al menos 20 años viejo. Su fecha de inicio fue alrededor de los primeros días de Octubre. Es un proyecto pasional mediante el cuál tengo como objetivo afianzar mis conocimientos tanto de Front-End como Back-End.

## Objetivo

Remodelar un sitio web de una institución académica que sea atractivo, funcional y fácil de usar.
&emsp; 

    Desarrollar un sitio web que
        - Sea responsive y sea funcional en diferentes dispositivos.
        - Incluya un formulario de contacto que sea fácil de usar y que recopile información pertinente de los visitantes del sitio.
        - Incluya todas las operaciones CRUD desarrolladas en un Back-End con Python.
        - Incluya el uso de APIs públicas.
        - Contenga animaciones y estilos en CSS y JS.

## Características

- Utiliza HTML5, CSS3 y JavaScript (JQuery) para la estructura, diseño y funcionalidades de la página.
- Utiliza Python (con POO), Flask, MySQL, XAMPP y JSON para el diseño del back-end y REST API y su implementación.
- Incluye tipografía Lato de Google Fonts y el uso de mapas embedidos de Google Maps.
- Incluye el uso de una API pública de generación de usuarios aleatorios.
- Utiliza iconos de FontAwesome para los elementos visuales.
- Incluye un favicon personalizado.
- Contiene carruseles, form validados y un CRUD totalmente funcional del cual se puede crear, mostrar/listar, modificar y eliminar objetos guardados en la DB MySQL.

## Instrucciones de uso

- Vía Github:
    1. Descarga todos los archivos de este repositorio.
    2. Abre el archivo "main.py" y ejecutalo con un servidor de XAMP (Apache y MySQL) previamente iniciado.
    3. Entra link ip mostrado en la consola luego de la ejecución de "main.py"
    4. Una vez en la página de inicio podrá acceder al CRUD de la página bajando y clickeando el botón "Ver todas las novedades"
    5. Dentro de "novedades" podrá editar, eliminar y subir novedades a la base de datos.

- Vía Netlify, abriendo ----

## Estructura de archivos

El repositorio contiene los siguientes archivos y carpetas:

- `index.html`: Página principal de la web es completamente responsiva.
- `assets/`: Carpeta que contiene los archivos de estilo CSS y los scripts JavaScript utilizados.
- `img/`: Carpeta que contiene las imágenes utilizadas en la página.
- `imgagenes-novedades/`: Carpeta que contiene las imágenes subidas por el CRUD a la DB.
- `templates/`: Carpeta que contiene documentos HTML con Jinja2.

## Desarrollos Futuros y Mejoras Potenciales

- Estructurado y estilizado de los demás documentos HTML.
- Posible registro de usuarios ADMIN.

## Notas finales

¡Espero que hayas disfrutado navegar por esta institución académica y hayas podido encontrar la carrera idonea!

## Check List

[x] Desarrollar e implementar el método DELETE del CRUD en el documento HTML "admin-novedades.html".

[o] Finalizar el desarrollo de otros documentos HTML que contengan únicamente capacidades de Front-End (Ej.: contacto.html)

[o] Implementar un diseño completamente responsivo en al menos 4 documentos HTML.

[x] Desarrollar e implementar el método CREATE (POST) del CRUD en el documento HTML "admin-novedades.html".

[x] Desarrollar e implementar el método READ (GET) del CRUD en el documento HTML "admin-novedades.html".

[x] Desarrollar e implementar el método DELETE del CRUD en el documento HTML "admin-novedades.html".

[x] Desarrollar e implementar el método UPDATE (PUT) del CRUD en el documento HTML "admin-novedades.html" y "editar-novedad.html".

[ ] Agregar un motor de busqueda que despliegue las novedades deseadas para su posterior edición o eliminación.

[o] Subir el proyecto a un sitio de hosting similar a Netlify.

### Notas Check List
- "x" Completado 
- "o" En desarrollo
