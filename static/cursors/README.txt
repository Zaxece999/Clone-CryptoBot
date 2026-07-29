This directory is for storing custom cursor files for the Crypto Bot project.

Supported cursor formats:
- CUR (.cur) - Windows cursor format
- ANI (.ani) - Animated cursor format
- PNG (.png) - Can be used with CSS cursor property
- SVG (.svg) - Scalable vector cursors

Place your custom cursor files here such as:
- Crypto-themed cursors
- Loading/processing cursors
- Interactive element cursors
- Special effect cursors

Files in this directory will be accessible via:
http://localhost:5000/cursors/filename.extension

To use a custom cursor in CSS:
.custom-cursor {
    cursor: url('/cursors/your-cursor.cur'), auto;
}
