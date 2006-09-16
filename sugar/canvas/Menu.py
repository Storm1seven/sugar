import gtk
import goocanvas
import gobject

from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem

class Menu(gtk.Window):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, grid, title, fill, stroke):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		self._width = 13
		self._grid = grid
		self._action_box = None

		self._canvas = CanvasView()
		self.add(self._canvas)
		self._canvas.show()

		model = goocanvas.CanvasModelSimple()
		self._root = model.get_root_item()

		self._rect = goocanvas.Rect(fill_color=fill,stroke_color=stroke,
							  		line_width=3)
		self._root.add_child(self._rect)

		text = goocanvas.Text(text=title, font="Sans bold 18",
							  fill_color='black', anchor=gtk.ANCHOR_SW)
		self._grid.set_constraints(text, 1, 3, self._width, 2)
		self._root.add_child(text)

		self._height = 4
		self._update_constraints()

		self._canvas.set_model(model)

	def _create_action_box(self):
		separator = goocanvas.Path(data='M 15 0 L 185 0', line_width=3,
								   fill_color='black')
		self._grid.set_constraints(separator, 0, 4)
		self._root.add_child(separator)

		box = CanvasBox(self._grid, CanvasBox.HORIZONTAL, 1)
		self._grid.set_constraints(box, 0, 5)

		return box

	def add_action(self, icon, action_id):
		if self._action_box == None:
			self._action_box = self._create_action_box()
			self._root.add_child(self._action_box)

			self._height = 10
			self._update_constraints()

		icon.connect('clicked', self._action_clicked_cb, action_id)
		self._action_box.set_constraints(icon, 3, 3)
		self._action_box.add_child(icon)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)

	def _update_constraints(self):
		self._grid.set_constraints(self._canvas, 0, 0,
								   self._width, self._height)				
		self._grid.set_constraints(self._rect, 0, 0,
								   self._width, self._height)

	def get_width(self):
		return self._width

	def get_height(self):
		return self._height
