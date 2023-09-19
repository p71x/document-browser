# document-browser

Simple viewer for file formats supported by PyMuPDF library (PDF, EPUB, MOBI, ...) and utilising PySimpleGUI as GUI.

**Attention: It is early alpha stage project. All aspects are subject to changes without warning.**

## Usage

to open new file: `python browse.py input_file_name`

to prompt for file or open last viewed file (if config file present): `python browse.py` or `browse.bat`

## Description

Get filename and start displaying page 1. If filename is saved in history,
then start with saved page number, window position and zoom. If there is config file present, 
and no filename given at startup, then on start automatically opens last viewed document. 
You can open more windows with additional documents and close them indywidually. Application ends 
when last file is closed. 

Theoretically all file types supported by MuPDF are supported (PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG and some graphics 
formats: JPG/JPEG, PNG, BMP, GIF, TIFF, PNM, PGM, PBM, PPM, PAM, JXR, JPX/JP2),
but so far I test application only with PDF and EPUB files.

Application utilises mainly keyboard events (and some mouse wheel) to trigger actions.
There are no buttons or menus. 

Actions supported include (action: key, alternative key...):
- Help page: F1,
- Close single view: q, Q, 
- Exit application: Esc,
- Open file: o, O,
- Open file from history: h, H,
- Next page: Right, Up, PageDown, Mouse:ScrollDown
- Previous page: Left, Down, PageUp, Mouse:ScrollUp
- Go to page: g, G
- Go to first page: Home
- Switch colorspace (between Grayscale and RGB): c, C
- Zoom in: +
- Zoom out: -
- Zoom fit: f, F, *
- Zoom 100%: 0 (zero key) 

## License

AGPL because of PyMuPDF license – and it is viral :(
If You consider use of some code from this project and don't plan using PyMuPdf, 
then code can be dual licensed under more free license as MIT or BSD.
