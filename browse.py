"""
Display a document using PyMuPDF and PySimpleGui
-------------------------------------------------------------------------------
License: GNU GPL V3+
(c) 2018-2019 Jorj X. McKie, 2023 Piotr Chamera

Usage
-----
python browse.py input_file_name

or

python browse.py

Description
-----------
Get filename and start displaying page 1. Please note that all file types
of MuPDF are supported (including EPUB e-books and HTML files for example).


We interpret keyboard events and mouse wheel actions
to support paging as if a button was clicked. Similarly, we do not include
a 'Quit' button. Instead, the ESCAPE or Q key can be used, or cancelling the form.
To improve paging performance, we are not directly creating pixmaps from
pages, but instead from the fitz.DisplayList of the page. Each display list
will be stored in a list and looked up by page number. This way, zooming
pixmaps and page re-visits will re-use a once-created display list.

Dependencies
------------
PyMuPDF, PySimpleGUI, tkinter, json
"""

import sys
import fitz
import PySimpleGUI as sg
import json
import os.path

# use config file if present in current directory
config_file_name = "./browse.config"

if os.path.isfile(config_file_name):
    with open(config_file_name, "r") as read_file:
        config = json.load(read_file)
else:
    config = {}


# ------------------------------------------------------------------------------
# ViewDoc class
# ------------------------------------------------------------------------------

class DocumentView:
    """
    Encapsulate view of document

    file_name = file name of viewed document
    doc = fitz (PyMuPDF) document instance bound to the view
    doc_page_count = page count of document
    page_index = 0 # currently viewed page index (0 based)
    zoom = scale factor – 1 is natural size (screen calibrated to physical size of document)
    cache = dict; cache of viewed pages (as pixmaps)
    max_size = maximal dimensions of viewed page, tuple (width, height)
    colorspace = fitz.csRGB # colorspace of page rendering
    """
    
    def __init__(self, file_name, page_index=0, max_size=None, colorspace=fitz.csRGB, zoom=1.0 ):
        self.file_name = file_name
        self.doc = fitz.open(file_name)
        self.doc_page_count = len(self.doc)
        self.page_index = page_index
        self.zoom = zoom
        self.cache = dict()
        self.max_size = max_size
        self.colorspace = colorspace

    @classmethod
    def from_config(cls, config_dictionary, max_size=None):
        """
        Construct view from data saved in config file.
        """
        d = config_dictionary
        return cls(d['file_name'],
                   page_index=d['page'],
                   zoom=d['zoom'],
                   colorspace=cls._colorspace_from_name(d['colorspace']),
                   max_size=max_size,
                   )

    @classmethod
    def _colorspace_from_name(cls, name):
        map = {'DeviceGRAY': fitz.csGRAY,
               'DeviceRGB': fitz.csRGB,
               }
        return map[name]
    
    def config_dictionary(self):
        return {"file_name": self.file_name,
                "page": self.page_index,
                "zoom": self.zoom,
                "colorspace": self.colorspace.name,
                }

    def get_display_list(self):
        """
        Return display list of current page (maybe from cache).
        """
        cache_key = self.page_index
        if cache_key in self.cache:
            return self.cache[cache_key]
        else:
            display_list = self.doc[self.page_index].get_displaylist()
            self.cache[cache_key] = display_list
            return display_list
        
    def get_page_image(self):
        """
        Return a tkinter.PhotoImage for a document page index (0-based)
        """
        display_list = self.get_display_list()
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pixmap = display_list.get_pixmap(matrix=matrix, colorspace=self.colorspace, alpha=False)
        return pixmap.tobytes("ppm")  # make PPM image from pixmap for tkinter, requires PyMuPDF version > 1.14.5

    def get_fit_zoom(self, fit_size=None):
        """
        Return zoom that fits page to available space (self.max_size).
        """
        max_size = fit_size or self.max_size
        rect = self.get_display_list().rect  # the page rectangle
        zoom = self.zoom
        if max_size:
            max_width, max_height = max_size
            fit_width_zoom = max_width / rect.width
            fit_height_zoom = max_height / rect.height
            zoom = min(1, fit_width_zoom, fit_height_zoom)
            if zoom == 1:
                zoom = min(fit_width_zoom, fit_height_zoom)
        return zoom

    def set_zoom(self, zoom):
        self.zoom = zoom
        
    def get_view_title(self):
        """
        Compose string for view window title.
        """
        return "Page %i of %i from file %s; zoom = %f" % (self.page_index + 1, self.doc_page_count, self.file_name, self.zoom)

    def previous_page(self):
        """
        Decrement or wrap around current page index.
        """
        previous_page = self.page_index - 1
        if previous_page < 0:
            previous_page += self.doc_page_count
        self.page_index = previous_page

    def next_page(self):
        """
        Increment or wrap around current page index.
        """
        next_page = self.page_index + 1
        if next_page >= self.doc_page_count:
            next_page -= page_count
        self.page_index = next_page
   

# ------------------------------------------------------------------------------
# get physical screen dimension to determine the page image max size
# ------------------------------------------------------------------------------

# print("screen size = " + str(sg.Window.get_screen_size()))
w, h = sg.Window.get_screen_size()
max_width = w - 20
max_height = h - 55
max_size = (max_width, max_height)

# ------------------------------------------------------------------------------
# startup sequence - determine document to open
# ------------------------------------------------------------------------------

def get_filename_from_GUI():
    fname = sg.PopupGetFile(
        "Select file and filetype to open:",
        title="PyMuPDF Document Browser",
        file_types=(
            ("PDF Files", "*.pdf"),
            ("XPS Files", "*.*xps"),
            ("Epub Files", "*.epub"),
            ("Fiction Books", "*.fb2"),
            ("Comic Books", "*.cbz"),
            ("HTML", "*.htm*"),
            # add more document types here
        ),
        no_window=True,
    )
    return fname

if "recent_file" in config:
    view = DocumentView.from_config(config["recent_file"], max_size=max_size)
elif len(sys.argv) == 1:
    view = DocumentView(get_filename_from_GUI(), page_index=0, max_size=max_size)
elif len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
    view = DocumentView(sys.argv[1], page_index=0, max_size=max_size)
else:
    sg.Popup("Cancelling:", "No file to view")
    sys.exit("Cancelled: no file to view supplied")


image_elem = sg.Image(data=view.get_page_image())  # make image element

##goto = sg.InputText(
##    str(cur_page + 1), size=(5, 1), do_not_clear=True, key="PageNumber"
##)  # for display & input

layout = [  # the form layout
    [image_elem],
]

form = sg.Window(
    title=view.get_view_title(),
    layout=layout,
    return_keyboard_events=True,
    location=(0, 0),
    use_default_focus=False,
    finalize=True,
)

# define keybindings not known to PySimpleGUI (key with modifier)
form.bind('<Control-KeyPress-q>', "key-CTRL-Q")
form.bind('<KeyPress-q>', "key-q")
form.bind('<Shift-KeyPress-q>', "key-Q")
form.bind('<Alt-KeyPress-q>', "key-ALT-q") # this is needed to suppress 'ALT-q' to act as 'q' (exit application)


# define the events we want to handle

def is_Quit(btn):
    return btn == sg.WIN_CLOSED or btn.startswith("Escape:") or btn in (chr(27), 'key-q', 'key-SHIFT-Q', "key-CTRL-Q")


def is_Next(btn):
    return btn.startswith("Next") or btn == "MouseWheel:Down" or btn.startswith("Up:") or btn.startswith("Right:")


def is_Prior(btn):
    return btn.startswith("Prior") or btn == "MouseWheel:Up" or btn.startswith("Down:") or btn.startswith("Left:")

def is_Open(btn):
    return btn in ('o', 'O')

def is_Up(btn):
    return btn.startswith("Up:")


def is_Down(btn):
    return btn.startswith("Down:")


def is_Left(btn):
    return btn.startswith("Left:")


def is_Right(btn):
    return btn.startswith("Right:")


def is_ZoomIn(btn):
    return btn == '+'

def is_ZoomOut(btn):
    return btn == '-'

def is_ZoomFit(btn):
    return btn in ('f', 'F', '*')

def is_Zoom100(btn):
    return btn in ('0',) 

def is_MyKeys(btn):
    return any((is_Next(btn), is_Prior(btn), is_ZoomIn(btn), is_ZoomOut(btn), is_Open(btn)))


# old page store and zoom toggle
old_page = 0

while True:
    btn, value = form.Read()

    if is_Quit(btn):
        with open(config_file_name, "w") as write_file:
            config["recent_file"] = view.config_dictionary()
            json.dump(config, write_file)
        break

    if is_Open(btn):
        fname = get_filename_from_GUI()
        if not fname:
            sg.Popup("Cancelling:", "No filename supplied")
            sys.exit("Cancelled: no filename supplied")
        view = DocumentView(fname, page_index=0, max_size=max_size)
    
    elif is_Next(btn):
        view.next_page()
    elif is_Prior(btn):
        view.previous_page()
    elif is_ZoomIn(btn):
        view.zoom *= 1.25
    elif is_ZoomOut(btn):
        view.zoom /= 1.25
    elif is_ZoomFit(btn):
        view.zoom = view.get_fit_zoom()
    elif is_Zoom100(btn):
        view.zoom = 1.0

    # update view
    image_elem.Update(data=view.get_page_image())

    # update page number field
    if is_MyKeys(btn):
        form.set_title(view.get_view_title())

form.close()
