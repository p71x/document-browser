# document-browser

Simple viewer for file formats supported by PyMuPDF library (PDF, EPUB, MOBI, ...) and utilising PySimpleGUI as GUI.

**Attention: It is early alpha stage project. All aspects are subject to changes without warning.**

## Usage

to open new file: `python browse.py input_file_name`

to prompt for file or open last viewed file (if config file present): `python browse.py` or `browse.bat`

## Description

Get filename and start displaying page 1. If filename is saved in history,
then start with saved page number and zoom. Please note that all file types
of MuPDF are supported (PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG and some graphics 
formats: JPG/JPEG, PNG, BMP, GIF, TIFF, PNM, PGM, PBM, PPM, PAM, JXR, JPX/JP2),
but I tested it only with PDF and EPUB.

We utilise keyboard events and mouse wheel actions to trigger actions.
There are no buttons. Actions supported (action: key, alternative key...):
- Help page: F1,
- Exit: q, Q, Esc,
- Open file: o, O,
- Open file from history: f, F,
- Next page: Right, Up, PageDown, Mouse:ScrollDown
- Previous page: Left, Down, PageUp, Mouse:ScrollUp
- Go to page: g, G
- Go to first page: Home
- Switch colorspace (between Grayscale and RGB): c, C
- Zoom in: +
- Zoom out: -
- Zoom fit: f, F, *
- Zoom 100%: 0 (zero key) 
