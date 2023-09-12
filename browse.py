"""
Display a document using Tkinter
-------------------------------------------------------------------------------
License: GNU GPL V3+
(c) 2018-2019 Jorj X. McKie

Usage
-----
python browse.py input.pdf

Description
-----------
Get filename and start displaying page 1. Please note that all file types
of MuPDF are supported (including EPUB e-books and HTML files for example).
Pages can be directly jumped to, or buttons can be used for paging.

This version contains enhancements:
* PIL no longer needed
* Zooming is now flexible: only one button serves as a toggle. Keyboard arrow keys can
  be used for moving through the window when zooming.

We also interpret keyboard events (PageDown / PageUp) and mouse wheel actions
to support paging as if a button was clicked. Similarly, we do not include
a 'Quit' button. Instead, the ESCAPE key can be used, or cancelling the form.
To improve paging performance, we are not directly creating pixmaps from
pages, but instead from the fitz.DisplayList of the page. Each display list
will be stored in a list and looked up by page number. This way, zooming
pixmaps and page re-visits will re-use a once-created display list.

Dependencies
------------
PyMuPDF v1.14.5+, PySimpleGUI, tkinter
"""

import sys
import fitz

#print(fitz.__doc__)

#if not tuple(map(int, fitz.VersionBind.split("."))) >= (1, 14, 5):
#    raise SystemExit("need PyMuPDF v1.14.5 for this script")

#if sys.platform == "win32":
#    import ctypes
#
#    ctypes.windll.shcore.SetProcessDpiAwareness(2)

import PySimpleGUI as sg
import tkinter as tk
import json
import os.path

# use config file if present in current directory
config_file_name = "./browse.config"

if os.path.isfile(config_file_name):
    with open(config_file_name, "r") as read_file:
        config = json.load(read_file)
else:
    config = {}


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
    )
    return fname

if "recent_file" in config:
    fname = config["recent_file"]["file_name"]
    cur_page = config["recent_file"]["page"]
elif len(sys.argv) == 1:
    fname = get_filename_from_GUI()
    cur_page = 0
else:
    fname = sys.argv[1]
    cur_page = 0

if not fname:
    sg.Popup("Cancelling:", "No filename supplied")
    sys.exit("Cancelled: no filename supplied")

doc = fitz.open(fname)
page_count = len(doc)

# allocate storage for page display lists
dlist_tab = [None] * page_count

title = "PyMuPDF display of '%s', pages: %i" % (fname, page_count)


# ------------------------------------------------------------------------------
# read the page data
# ------------------------------------------------------------------------------
def get_page(pno, zoom=False, max_size=None):
    """Return a tkinter.PhotoImage or a PNG image for a document page number.
    :arg int pno: 0-based page number
    :arg zoom: top-left of old clip rect, and one of -1, 0, +1 for dim. x or y
               to indicate the arrow key pressed
    :arg max_size: (width, height) of available image area
    :arg bool first: if True, we cannot use tkinter
    """
    dlist = dlist_tab[pno]  # get display list of page number
    if not dlist:  # create if not yet there
        dlist_tab[pno] = doc[pno].get_displaylist()
        dlist = dlist_tab[pno]
    r = dlist.rect  # the page rectangle
    clip = r
    # ensure image fits screen:
    # exploit, but do not exceed width or height
    zoom_0 = 1
    if max_size:
        zoom_0 = min(1, max_size[0] / r.width, max_size[1] / r.height)
        if zoom_0 == 1:
            zoom_0 = min(max_size[0] / r.width, max_size[1] / r.height)

    mat_0 = fitz.Matrix(zoom_0, zoom_0)

    if not zoom:  # show the total page
        pix = dlist.get_pixmap(matrix=mat_0, alpha=False)
    else:
        w2 = r.width / 2  # we need these ...
        h2 = r.height / 2  # a few times
        clip = r * 0.5  # clip rect size is a quarter page
        tl = zoom[0]  # old top-left
        tl.x += zoom[1] * (w2 / 2)  # adjust topl-left ...
        tl.x = max(0, tl.x)  # according to ...
        tl.x = min(w2, tl.x)  # arrow key ...
        tl.y += zoom[2] * (h2 / 2)  # provided, but ...
        tl.y = max(0, tl.y)  # stay within ...
        tl.y = min(h2, tl.y)  # the page rect
        clip = fitz.Rect(tl, tl.x + w2, tl.y + h2)
        # clip rect is ready, now fill it
        mat = mat_0 * fitz.Matrix(2, 2)  # zoom matrix
        pix = dlist.get_pixmap(alpha=False, matrix=mat, clip=clip)
    img = pix.tobytes("ppm")  # make PPM image from pixmap for tkinter
    return img, clip.tl  # return image, clip position


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# get physical screen dimension to determine the page image max size
# ------------------------------------------------------------------------------
root = tk.Tk()
max_width = root.winfo_screenwidth() - 20
max_height = root.winfo_screenheight() - 135
max_size = (max_width, max_height)
root.destroy()
del root
# ------------------------------------------------------------------------------

form = sg.FlexForm(
    title, return_keyboard_events=True, location=(0, 0), use_default_focus=False
)

data, clip_pos = get_page(
    cur_page,  # read first page
    zoom=False,  # not zooming yet
    max_size=max_size,  # image max dim
)

image_elem = sg.Image(data=data)  # make image element

goto = sg.InputText(
    str(cur_page + 1), size=(5, 1), do_not_clear=True, key="PageNumber"
)  # for display & input

layout = [  # the form layout
    [
        sg.ReadFormButton("Next"),
        sg.ReadFormButton("Prior"),
        sg.Text("Page:"),
        goto,
        sg.Text("(%i)" % page_count),
        sg.ReadFormButton("Zoom"),
        sg.Text("(toggle on/off, use arrows to navigate while zooming)"),
    ],
    [image_elem],
]

form.Layout(layout)  # define the form


# define the buttons / events we want to handle
def is_Enter(btn):
    return btn.startswith("Return:") or btn == chr(13)


def is_Quit(btn):
    return btn == chr(27) or btn.startswith("Escape:")


def is_Next(btn):
    return btn.startswith("Next") or btn == "MouseWheel:Down" or btn.startswith("Up:") or btn.startswith("Right:")


def is_Prior(btn):
    return btn.startswith("Prior") or btn == "MouseWheel:Up" or btn.startswith("Down:") or btn.startswith("Left:")


def is_Up(btn):
    return btn.startswith("Up:")


def is_Down(btn):
    return btn.startswith("Down:")


def is_Left(btn):
    return btn.startswith("Left:")


def is_Right(btn):
    return btn.startswith("Right:")


def is_Zoom(btn):
    return btn.startswith("Zoom")


def is_MyKeys(btn):
    return any((is_Enter(btn), is_Next(btn), is_Prior(btn), is_Zoom(btn)))


# old page store and zoom toggle
old_page = 0
old_zoom = False
zoom_active = False

while True:
    btn, value = form.Read()
    if btn is None and (value is None or value["PageNumber"] is None):
        break
    if is_Quit(btn):
        with open(config_file_name, "w") as write_file:
            config["recent_file"] = {"file_name": fname, "page": cur_page}
            json.dump(config, write_file)
        break
    zoom_pressed = False
    zoom = False

    if is_Enter(btn):
        try:
            cur_page = int(value["PageNumber"]) - 1  # check if valid
        except:
            cur_page = 0  # this guy's trying to fool me

    elif is_Next(btn):
        cur_page += 1
    elif is_Prior(btn):
        cur_page -= 1
    elif is_Up(btn) and zoom_active:
        zoom = (clip_pos, 0, -1)
    elif is_Down(btn) and zoom_active:
        zoom = (clip_pos, 0, 1)
    elif is_Left(btn) and zoom_active:
        zoom = (clip_pos, -1, 0)
    elif is_Right(btn) and zoom_active:
        zoom = (clip_pos, 1, 0)
    elif is_Zoom(btn):
        zoom_pressed = True
        if not zoom_active:
            zoom = (clip_pos, 0, 0)

    # sanitize page number
    while cur_page >= page_count:  # wrap around
        cur_page -= page_count
    while cur_page < 0:  # pages < 0 are valid but look bad
        cur_page += page_count

    if zoom_pressed and zoom_active:
        zoom = zoom_pressed = zoom_active = False

    data, clip_pos = get_page(cur_page, zoom=zoom, max_size=max_size)
    image_elem.Update(data=data)
    old_page = cur_page
    old_zoom = zoom
    zoom_active = zoom_pressed or zoom

    # update page number field
    if is_MyKeys(btn):
        goto.Update(str(cur_page + 1))
