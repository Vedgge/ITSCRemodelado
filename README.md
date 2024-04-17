# ITSC Remodeled

This repository contains an experiment of remodeling ITSC's website, which looks at least 20 years old. It was initiated around early October. It's a passion project through which I aim to strengthen my knowledge in both Front-End and Back-End.

## Objective

Remodel a website of an academic institution to be attractive, functional, and user-friendly.

- Develop a website that:
    - Is responsive and functional on different devices.
    - Includes a contact form that is easy to use and collects relevant information from site visitors.
    - Incorporates all CRUD operations developed in a Python Back-End.
    - Utilizes public APIs.
    - Contains CSS and JS animations and styles.

## Features

- Uses HTML5, CSS3, and JavaScript (JQuery) for page structure, design, and functionalities.
- Utilizes Python (with OOP), Flask, MySQL, XAMPP, and JSON for back-end design and REST API implementation.
- Includes Google Fonts' Lato typography and embedded Google Maps.
- Incorporates usage of a public API for generating random users.
- Utilizes FontAwesome icons for visual elements.
- Includes a custom favicon.
- Contains carousels, validated forms, and a fully functional CRUD for creating, displaying/listing, modifying, and deleting objects stored in the MySQL DB.

## Usage Instructions

- Via Github:
    1. Download all files from this repository.
    2. Open the "main.py" file and execute it with a XAMPP server (Apache and MySQL) previously started.
    3. Enter the IP link shown in the console after executing "main.py".
    4. Once on the homepage, you can access the CRUD page by scrolling down and clicking the "Ver todas las novedades" button.
    5. Within "novedades," you can edit, delete, and upload news to the database. Remember that if no image is uploaded, the "imagen-predeterminada-novedad.png" will be automatically used.

- Via pythonanywhere, by opening [Instituto Técnico Superior de Córdoba](https://facusav.pythonanywhere.com/) *Currently, there is an error with uploading images to the DB which does not occur when executed locally.

## File Structure

The repository contains the following files and folders:

- `index.html`: Main page of the website is fully responsive.
- `assets/`: Folder containing CSS style files and JavaScript scripts used.
- `img/`: Folder containing images used on the page.
- `imgagenes-novedades/`: Folder containing images uploaded by the CRUD to the DB.
- `templates/`: Folder containing HTML documents with Jinja2.

## Future Developments and Potential Improvements

- Structuring and styling of other HTML documents.
- Possible registration of ADMIN users.

## Final Notes

I hope you enjoyed browsing this academic institution and found the perfect career!

## Check List

[x] Develop and implement the DELETE method of the CRUD in the "admin-novedades.html" HTML document.

[o] Finalize the development of other HTML documents that contain only Front-End capabilities (e.g., contacto.html).

[o] Implement a fully responsive design in at least 4 HTML documents.

[x] Develop and implement the CREATE (POST) method of the CRUD in the "admin-novedades.html" HTML document.

[x] Develop and implement the READ (GET) method of the CRUD in the "admin-novedades.html" HTML document.

[x] Develop and implement the DELETE method of the CRUD in the "admin-novedades.html" HTML document.

[x] Develop and implement the UPDATE (PUT) method of the CRUD in the "admin-novedades.html" and "editar-novedad.html" HTML documents.

[ ] Add a search engine that displays desired news for subsequent editing or deletion.

[o] Upload the project to a hosting site.

### Check List Notes
- "x" Completed
- "o" In progress
