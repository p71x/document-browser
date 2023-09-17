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
Get filename and start displaying page 1. If filename is saved in history,
then start with saved page number and zoom. Please note that all file types
of MuPDF are supported (PDF, EPUB, MOBI e-books and others).

We utilise keyboard events and mouse wheel actions to trigger actions.
There are no buttons.

Dependencies
------------
PyMuPDF > 1.14.5, PySimpleGUI (tkinter), json
"""

help_text = """Actions supported (action, key):
- Open file: o, O,
- Open file from history: f, F,
- Next page: Right, Up, PageDown
- Previous page: Left, Down, PageUp
- Go to page: g, G
- Switch colorspace (between Grayscale and RGB): c, C
- Zoom in: +
- Zoom out: -
- Zoom fit: f, F, *
- Zoom 100%: 0 (zero key) 
- Exit: q, Q, Esc,
- Help page: F1
"""

import sys
import fitz
import PySimpleGUI as sg
import json
import os.path

# print("PyMuPDF version: ", fitz.version)
# print(fitz.__doc__)

# use config file if present in current directory
config_file_name = "./browse.config"

class Configuration:
    """
    Application configuration store and persistency.
    """

    def __init__(self, path):
        self.path = path
        self._config = dict()

        if os.path.isfile(path):
            with open(path, "r") as read_file:
                self._config = json.load(read_file)

    def save(self):
        with open(self.path, "w") as write_file:
            json.dump(self._config, write_file, indent=2)

    def get_history(self):
        if 'history' in self._config:
            return self._config['history']
        else:
            return None

    def get_view_history(self, path):
        if 'history' in self._config:
            return next((x for x in self._config["history"] if x['file_name'] == path),
                        None)        

    def update_history(self, view_dictionary):
        if 'history' not in self._config:
            self._config['history'] = [view_dictionary, ]
        else:
            history = self._config["history"]
            history = [x for x in history if x['file_name'] != view_dictionary['file_name']]
            history.insert(0, view_dictionary)
            self._config["history"] = history
        
configuration = Configuration(config_file_name)

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
    dpi - display dpi
    """
    
    def __init__(self, file_name, page_index=0, max_size=None, colorspace=fitz.csRGB, zoom=1.0, dpi=94):
        self.file_name = file_name
        self.doc = fitz.open(file_name)
        self.doc_page_count = len(self.doc)
        self.page_index = page_index
        self.zoom = zoom
        self.cache = dict()
        self.max_size = max_size
        self.colorspace = colorspace
        self.dpi=dpi

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
        """
        Utility for mapping from colorspace designator to colorspace object.
        """
        map = {'DeviceGray': fitz.csGRAY,
               'DeviceRGB': fitz.csRGB,
               }
        return map[name]
    
    def config_dictionary(self):
        """
        Return dictionary for saving parameters in config file.
        """
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
        # correction of scale to display dpi (default for PyMuPDF 72 dpi)
        dpi_correction = self.dpi / 72 
        matrix = fitz.Matrix(self.zoom * dpi_correction, self.zoom * dpi_correction)
        pixmap = display_list.get_pixmap(matrix=matrix, #dpi=96,
                                         colorspace=self.colorspace,
                                         alpha=False)
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
        # correction of zoom to display dpi (default for PyMuPDF 72 dpi)
        dpi_correction = self.dpi / 72 
        zoom = zoom / dpi_correction
        return zoom

    def set_zoom(self, zoom):
        """
        Set zoom factor.
        """
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
            next_page -= self.doc_page_count
        self.page_index = next_page

    def go_to_page(self, index):
        """
        Go to page with given index (1-based) but check if not out of bounds.
        """
        page = index - 1
        if page >= self.doc_page_count:
            self.page_index = page_count - 1
        elif page < 0:
            self.page_index = 0
        else:
            self.page_index = page

    def toggle_colorspace(self):
        """
        Switch between Gray and RGB colorspaces.
        """
        if self.colorspace is fitz.csGRAY:
            self.colorspace = fitz.csRGB
        else:
            self.colorspace = fitz.csGRAY
            

# ------------------------------------------------------------------------------
# get physical screen dimension to determine the page image max size
# ------------------------------------------------------------------------------

# print("screen size = " + str(sg.Window.get_screen_size()))
w, h = sg.Window.get_screen_size()
max_width = w - 20
max_height = h - 55
max_size = (max_width, max_height)

# ------------------------------------------------------------------------------
# utilities and popups
# ------------------------------------------------------------------------------

def get_filename_from_open_GUI():
    fname = sg.popup_get_file(
        "Select file and filetype to open:",
        title="PyMuPDF Document Browser",
        file_types=(
            ("PDF Files", "*.pdf"),
            ("XPS Files", "*.*xps"),
            ("Epub Files", "*.epub"),
            ("Fiction Books", "*.fb2"),
            ("Comic Books", "*.cbz"),
            ("HTML", "*.htm*"),
            ("All", "*.*"),
            # add more document types here
        ),
        no_window=True,
    )
    return fname

def get_filename_from_history_GUI():
    values = configuration.get_history()
    # make list of history entries as human readable labels
    labels = [value['file_name'] for value in values]
    window = sg.Window(title = "Select file from history",
                       layout = [[sg.Listbox(labels,
                                             size=(80,10),
                                             select_mode = 'single',
                                             key='SELECTED')],
                                 [sg.OK(), sg.Cancel()]
                                ])
    event, choice = window.read()
    window.close()
    if event == 'OK' and bool(choice['SELECTED']):
        index = labels.index(choice['SELECTED'][0])
        return values[index]
    else:
        return None

def get_page_number_from_GUI():
    try:
        index = int(sg.popup_get_text('Enter page number',
                                      no_titlebar=True,
                                      grab_anywhere=True,
                                      keep_on_top=True,
                                      modal=False,
                                      )
                    )
        return index
    except:
        return None

def show_help_page_GUI():
    text = help_text
    window = sg.Window(title = "Available actions",
                       layout = [[sg.Text(text,
                                          size=(50,15),)],
                                 [sg.OK(focus = True)],
                                ],
                       finalize = True)
    event, value = window.read()
    window.close()
    return None

# ------------------------------------------------------------------------------
# startup sequence - determine document to open
# ------------------------------------------------------------------------------

if configuration.get_history():
    view = DocumentView.from_config(configuration.get_history()[0], max_size=max_size)
elif len(sys.argv) == 1:
    view = DocumentView(get_filename_from_GUI(), page_index=0, max_size=max_size)
elif len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
    view = DocumentView(sys.argv[1], page_index=0, max_size=max_size)
else:
    sg.Popup("Cancelling:", "No file to view")
    sys.exit("Cancelled: no file to view supplied")


image_elem = sg.Image(data=view.get_page_image())  # make image element

layout = [  # the form layout
    [image_elem],
]

form = sg.Window(
    title=view.get_view_title(),
    layout=layout,
    resizable=True,
    return_keyboard_events=True,
    location=(0, 0),
    use_default_focus=False,
    finalize=True,
)

# center window at startup
form.move_to_center()

# define keybindings not known to PySimpleGUI (key with modifier)
form.bind('<Control-KeyPress-q>', "key-CTRL-Q")
form.bind('<KeyPress-q>', "key-q")
form.bind('<Shift-KeyPress-q>', "key-Q")
form.bind('<Alt-KeyPress-q>', "key-ALT-q") # this is needed to suppress 'ALT-q' to act as 'q' (exit application)
form.bind('<KeyPress-Home>', "key-Home")
form.bind('<KeyPress-F1>', "key-F1")


# define the events we want to handle

def is_Quit(btn):
    return btn == sg.WIN_CLOSED or btn.startswith("Escape:") or btn in (chr(27), 'key-q', 'key-SHIFT-Q', "key-CTRL-Q")

def is_Next(btn):
    return btn.startswith("Next") or btn == "MouseWheel:Down" or btn.startswith("Up:") or btn.startswith("Right:")

def is_Prior(btn):
    return btn.startswith("Prior") or btn == "MouseWheel:Up" or btn.startswith("Down:") or btn.startswith("Left:")

def is_Goto(btn):
    return btn in ('g', 'G')
    
def is_GotoFirstPage(btn):
    return btn in ('key-Home',)
    
def is_Open(btn):
    return btn in ('o', 'O')

def is_OpenFromHistory(btn):
    return btn in ('h', 'H')

def is_ZoomIn(btn):
    return btn == '+'

def is_ZoomOut(btn):
    return btn == '-'

def is_ZoomFit(btn):
    return btn in ('f', 'F', '*')

def is_Zoom100(btn):
    return btn in ('0',) 

def is_ToggleColorspace(btn):
    return btn in ('c', 'C') 

def is_ShowHelpPage(btn):
    return btn in ('key-F1')

##def is_Redraw(btn):
##    return any((is_Next(btn), is_Prior(btn), is_Goto(btn), is_GotoFirstPage(btn),
##                is_ZoomIn(btn), is_ZoomOut(btn), is_ZoomFit(btn), is_Zoom100(btn),
##                is_Open(btn), is_ToggleColorspace(btn)))

# ------------------------------------------------------------------------------
# main event loop
# ------------------------------------------------------------------------------

while True:
    btn, value = form.Read()

    if is_Quit(btn):
        configuration.update_history(view.config_dictionary())
        configuration.save()
        break

    if is_Open(btn):
        fname = get_filename_from_open_GUI()
        if fname:
            configuration.update_history(view.config_dictionary())
            configuration.save()
            view_history = configuration.get_view_history(fname)
            if view_history:
                view = DocumentView.from_config(view_history, max_size=max_size)
            else:
                view = DocumentView(fname, page_index=0, max_size=max_size)
    
    if is_OpenFromHistory(btn):
        view_history = get_filename_from_history_GUI()
        configuration.update_history(view.config_dictionary())
        configuration.save()
        if view_history and os.path.isfile(view_history['file_name']):
            view = DocumentView.from_config(view_history, max_size=max_size)

    elif is_Next(btn):
        view.next_page()
    elif is_Prior(btn):
        view.previous_page()
    elif is_Goto(btn):
        index = get_page_number_from_GUI()
        if index:
            view.go_to_page(index)
    elif is_GotoFirstPage(btn):
        view.go_to_page(0)
    elif is_ZoomIn(btn):
        view.zoom *= 1.25
    elif is_ZoomOut(btn):
        view.zoom /= 1.25
    elif is_ZoomFit(btn):
        view.zoom = view.get_fit_zoom()
    elif is_Zoom100(btn):
        view.zoom = 1.0
    elif is_ToggleColorspace(btn):
        view.toggle_colorspace()
    elif is_ShowHelpPage(btn):
        show_help_page_GUI()

    # update view
    image_elem.Update(data=view.get_page_image())

    # update form title
    #if is_Redraw(btn):
    form.set_title(view.get_view_title())

form.close()
