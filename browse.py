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
print(fitz.__doc__)
print('PySimpleGUI version: ', sg.version)

# ------------------------------------------------------------------------------
# Configuration - app configuration storage
# ------------------------------------------------------------------------------

class Configuration:
    """
    Application configuration store and persistency.
    Default is storage is „browse.config” file in current directory.
    """

    def __init__(self, path="./browse.config"):
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
        # persist changes
        self.save()

        
# ------------------------------------------------------------------------------
# Document class
# ------------------------------------------------------------------------------

##class Document():
##    """
##    Encapsulate open document data.
##    """
##
##    def __init__(self):
##        pass
##
##class PyMuPDFDocument(Document):
##    """
##    Encapsulate open document data.
##    
##    file_name = file name of viewed document
##    doc = fitz (PyMuPDF) document instance bound to the view
##    doc_page_count = page count of document
##    """
##
##    def __init__(self, file_name):
##        pass

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
    
    def __init__(self, file_name, page_index=0, max_size=None,
                 colorspace=fitz.csRGB, zoom=1.0, dpi=94, location=(0,0)):
        # initialize document
        self.file_name = file_name
        self.doc = fitz.open(file_name)
        self.doc_page_count = len(self.doc)
        self.cache = dict()
        self.page_index = page_index
        self.zoom = zoom
        self.colorspace = colorspace
        self.dpi=dpi
        # get physical screen dimension to determine the page image max size
        # print("screen size = " sg.Window.get_screen_size())
        if not max_size:
            w, h = sg.Window.get_screen_size()
            max_width = w - 20
            max_height = h - 55
            self.max_size = (max_width, max_height)
        # initialize view
        self.image_elem = sg.Image(data=self.get_page_image())  # make image element
        layout = [ [self.image_elem] ]
        self.form = sg.Window(title=self.get_view_title(),
                              layout=layout,
                              resizable=True,
                              return_keyboard_events=True,
                              location=location,
                              use_default_focus=False,
                              finalize=True,
                              enable_close_attempted_event=True,
                              )
        self.form.TKroot.focus_force()

        # define keybindings not known to PySimpleGUI (key with modifier)
        self.form.bind('<Control-KeyPress-q>', "key-CTRL-Q")
        self.form.bind('<KeyPress-q>', "key-q")
        self.form.bind('<Shift-KeyPress-q>', "key-Q")
        self.form.bind('<Alt-KeyPress-q>', "key-ALT-q") # this is needed to suppress 'ALT-q' to act as 'q' (exit application)
        self.form.bind('<KeyPress-Home>', "key-Home")
        self.form.bind('<KeyPress-F1>', "key-F1")

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
                   location=d['location'] if 'location' in d else (0,0),
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
        location = self.get_location()
        if not location or not location[0] or not location[1]:
            location = (0,0)
        return {"file_name": self.file_name,
                "page": self.page_index,
                "zoom": self.zoom,
                "colorspace": self.colorspace.name,
                "location": location,
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

    def update(self):
        # update view
        self.image_elem.Update(data=view.get_page_image())
        # update form title
        self.form.set_title(self.get_view_title())
        self.get_location()

    def get_location(self):
        loc = self.form.current_location()
        #print('location: ', loc)
        return loc

    def get_size(self):
        return self.form.current_size_accurate()

    def center_window_on_screen(self):
        self.form.move_to_center()

    def close(self):
        self.form.close()

class DocumentBrowser():
    """
    Application main class.
    """

    def __init__(self):
        self.configuration = Configuration()
        # self.documents = [] # for future multiple documents app
        # self.views = [] # for future multiple views app
        self.view = None # active view

    def start(self, argv):
        if self.configuration.get_history():
            self.view = DocumentView.from_config(self.configuration.get_history()[0])
        elif len(argv) == 1:
            self.view = DocumentView(get_filename_from_open_GUI(), page_index=0)
            #self.view.center_window_on_screen()
        elif len(argv) == 2 and os.path.isfile(sys.argv[1]):
            self.view = DocumentView(argv[1], page_index=0)
            #self.view.center_window_on_screen()
        else:
            sg.Popup("Cancelling:", "No file to view")
            sys.exit("Cancelled: no file to view supplied")
        #self.views.push(self.view)

    def close(self):
        self.view.close()

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

def get_filename_from_history_GUI(app):
    values = app.configuration.get_history()
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





# define the events we want to handle

def is_Quit(event):
    #return event == sg.WIN_CLOSED or event.startswith("Escape:") or event in (chr(27), 'key-q', 'key-SHIFT-Q', "key-CTRL-Q")
    return event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT or event.startswith("Escape:") or event in (chr(27), 'key-q', 'key-SHIFT-Q', "key-CTRL-Q")

def is_Next(event):
    return event.startswith("Next") or event == "MouseWheel:Down" or event.startswith("Up:") or event.startswith("Right:")

def is_Prior(event):
    return event.startswith("Prior") or event == "MouseWheel:Up" or event.startswith("Down:") or event.startswith("Left:")

def is_Goto(event):
    return event in ('g', 'G')
    
def is_GotoFirstPage(event):
    return event in ('key-Home',)
    
def is_Open(event):
    return event in ('o', 'O')

def is_OpenFromHistory(event):
    return event in ('h', 'H')

def is_ZoomIn(event):
    return event == '+'

def is_ZoomOut(event):
    return event == '-'

def is_ZoomFit(event):
    return event in ('f', 'F', '*')

def is_Zoom100(event):
    return event in ('0',) 

def is_ToggleColorspace(event):
    return event in ('c', 'C') 

def is_ShowHelpPage(event):
    return event in ('key-F1')

# ------------------------------------------------------------------------------
# Application life cycle
# ------------------------------------------------------------------------------

app = DocumentBrowser()

app.start(sys.argv)

view = app.view

# main event loop

while True:
    event, value = view.form.Read()

    if is_Quit(event):
        app.configuration.update_history(view.config_dictionary())
        break

    if is_Open(event):
        fname = get_filename_from_open_GUI()
        if fname:
            app.configuration.update_history(view.config_dictionary())
            view_history = app.configuration.get_view_history(fname)
            if view_history:
                view.close()
                view = DocumentView.from_config(view_history)
            else:
                view.close()
                view = DocumentView(fname, page_index=0)
                view.center_window_on_screen()
    
    if is_OpenFromHistory(event):
        view_history = get_filename_from_history_GUI(app)
        app.configuration.update_history(view.config_dictionary())
        if view_history and os.path.isfile(view_history['file_name']):
            view.close()
            view = DocumentView.from_config(view_history)

    elif is_Next(event):
        view.next_page()
    elif is_Prior(event):
        view.previous_page()
    elif is_Goto(event):
        index = get_page_number_from_GUI()
        if index:
            view.go_to_page(index)
    elif is_GotoFirstPage(event):
        view.go_to_page(0)
    elif is_ZoomIn(event):
        view.zoom *= 1.25
    elif is_ZoomOut(event):
        view.zoom /= 1.25
    elif is_ZoomFit(event):
        view.zoom = view.get_fit_zoom()
    elif is_Zoom100(event):
        view.zoom = 1.0
    elif is_ToggleColorspace(event):
        view.toggle_colorspace()
    elif is_ShowHelpPage(event):
        show_help_page_GUI()

    view.update()

app.close()
