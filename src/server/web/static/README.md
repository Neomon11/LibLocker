# Static Files Directory

This directory is reserved for static web assets (CSS, JavaScript, images, etc.) for the LibLocker web interface.

Currently, all styles and scripts are embedded in the HTML template (`index.html`) for simplicity and single-file deployment.

## Future Use

If the web interface grows in complexity, static assets should be placed here:
- `/static/css/` - Stylesheets
- `/static/js/` - JavaScript files
- `/static/img/` - Images and icons
- `/static/fonts/` - Custom fonts

These files will be automatically served by the aiohttp web server.
