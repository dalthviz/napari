from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt import QLabeledDoubleSlider

from napari._qt.dialogs.qt_modal import QtPopup
from napari._qt.widgets._slider_compat import QDoubleSlider
from napari.layers.base._base_constants import BLENDING_TRANSLATIONS, Blending
from napari.layers.base.base import Layer
from napari.utils.events import disconnect_events
from napari.utils.translations import trans

# opaque and minimum blending do not support changing alpha (opacity)
NO_OPACITY_BLENDING_MODES = {str(Blending.MINIMUM), str(Blending.OPAQUE)}


class QtScaleControl(QWidget):
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.layer.events.affine.connect(self._on_scale_change)

        self.setProperty('emphasized', True)
        self._sliders = []

        scaleLayout = QFormLayout()
        scaleLayout.setContentsMargins(0, 0, 0, 0)
        for idx, scale in enumerate(self.layer.affine.scale):
            scale_slider = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
            scale_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            scale_slider.setMinimum(0.1)
            scale_slider.setMaximum(10)
            scale_slider.setSingleStep(0.01)
            scale_slider.setValue(scale)
            scale_slider.valueChanged.connect(self.changeScale)
            self._sliders.append(scale_slider)
            scaleLayout.addRow(str(idx), scale_slider)
        self.setLayout(scaleLayout)

    def changeScale(self, value):
        with self.layer.events.blocker(self._on_scale_change):
            new_scale = []
            for scale in self._sliders:
                new_scale.append(scale.value())
            affine = self.layer.affine
            affine.scale = new_scale
            self.layer.affine = affine

    def _on_scale_change(self):
        with self.layer.events.affine.blocker():
            for idx, slider in enumerate(self._sliders):
                slider.setValue(self.layer.affine.scale[idx])

    def show_popup(self):
        scale_popup = QtScalePopup(self.layer, parent=self)
        scale_popup.move_to('top', min_length=650)
        scale_popup.show()

    def mousePressEvent(self, event):
        """Update the slider, or, on right-click, pop-up an expanded slider.

        The expanded slider provides finer control, directly editable values,
        and the ability to change the available range of the sliders.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        if event.button() == Qt.MouseButton.RightButton:
            self.show_popup()
        else:
            super().mousePressEvent(event)


class QtScaleDialog(QDialog):
    def __init__(self, layer: Layer, initial_affine, parent=None) -> None:
        super().__init__(parent=parent)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.layer = layer
        self._initial_affine = initial_affine
        # self._sliders = []
        layout = QVBoxLayout()
        # scaleLayout = QFormLayout()
        # scaleLayout.setContentsMargins(0, 0, 0, 0)

        # for idx, scale in enumerate(self.layer.affine.scale):
        #     scale_slider = QLabel(str(scale))
        #     # scale_slider.setValue(scale)
        #     # scale_slider.valueChanged.connect(self.changeScale)
        #     self._sliders.append(scale_slider)
        #     scaleLayout.addRow(str(idx), scale_slider)
        # layout.addLayout(scaleLayout)
        button_box = QDialogButtonBox(Qt.Vertical, parent=self)
        reset_scale_btn = QPushButton('reset scale')
        reset_scale_btn.setToolTip(trans._('Reset affine transform scale'))
        reset_scale_btn.clicked.connect(self.reset_scale)
        # layout.addWidget(reset_scale_btn)
        button_box.addButton(
            reset_scale_btn, QDialogButtonBox.ButtonRole.ActionRole
        )

        reset_rotate_btn = QPushButton('reset rotate')
        reset_rotate_btn.setToolTip(trans._('Reset affine transform rotate'))
        reset_rotate_btn.clicked.connect(self.reset_rotate)
        # layout.addWidget(reset_rotate_btn)
        button_box.addButton(
            reset_rotate_btn, QDialogButtonBox.ButtonRole.ActionRole
        )

        reset_translate_btn = QPushButton('reset translate')
        reset_translate_btn.setToolTip(
            trans._('Reset affine transform translate')
        )
        reset_translate_btn.clicked.connect(self.reset_translate)
        # layout.addWidget(reset_translate_btn)
        button_box.addButton(
            reset_translate_btn, QDialogButtonBox.ButtonRole.ActionRole
        )

        reset_btn = QPushButton('reset all')
        reset_btn.setToolTip(trans._('Reset affine transform'))
        # reset_btn.setFixedWidth(45)
        reset_btn.clicked.connect(self.reset)
        button_box.addButton(reset_btn, QDialogButtonBox.ButtonRole.ResetRole)
        # layout.addWidget(reset_btn)
        layout.addWidget(button_box)
        self.setLayout(layout)

        # self.frame.setLayout(layout)

    # def changeScale(self, value):
    #     new_scale = []
    #     for scale in self._sliders:
    #         new_scale.append(scale.value())
    #         affine = self.layer.affine
    #         affine.scale = new_scale
    #         self.layer.affine = affine

    def reset_scale(self):
        new_affine = self.layer.affine
        new_affine.scale = self._initial_affine.scale
        self.layer.affine = new_affine

    def reset_rotate(self):
        new_affine = self.layer.affine
        new_affine.rotate = self._initial_affine.rotate
        self.layer.affine = new_affine

    def reset_translate(self):
        new_affine = self.layer.affine
        new_affine.translate = self._initial_affine.translate
        self.layer.affine = new_affine

    def reset(self):
        self.layer.affine = self._initial_affine


class QtScalePopup(QtPopup):
    def __init__(self, layer: Layer, initial_affine, parent=None) -> None:
        super().__init__(parent)

        self.layer = layer
        self._initial_affine = initial_affine
        # self._sliders = []
        layout = QVBoxLayout()
        # scaleLayout = QFormLayout()
        # scaleLayout.setContentsMargins(0, 0, 0, 0)

        # for idx, scale in enumerate(self.layer.affine.scale):
        #     scale_slider = QLabel(str(scale))
        #     # scale_slider.setValue(scale)
        #     # scale_slider.valueChanged.connect(self.changeScale)
        #     self._sliders.append(scale_slider)
        #     scaleLayout.addRow(str(idx), scale_slider)
        # layout.addLayout(scaleLayout)

        reset_scale_btn = QPushButton('reset scale')
        reset_scale_btn.setToolTip(trans._('Reset affine transform scale'))
        reset_scale_btn.clicked.connect(self.reset_scale)
        layout.addWidget(reset_scale_btn)

        reset_rotate_btn = QPushButton('reset rotate')
        reset_rotate_btn.setToolTip(trans._('Reset affine transform rotate'))
        reset_rotate_btn.clicked.connect(self.reset_rotate)
        layout.addWidget(reset_rotate_btn)

        reset_translate_btn = QPushButton('reset translate')
        reset_translate_btn.setToolTip(
            trans._('Reset affine transform translate')
        )
        reset_translate_btn.clicked.connect(self.reset_translate)
        layout.addWidget(reset_translate_btn)

        reset_btn = QPushButton('reset all')
        reset_btn.setToolTip(trans._('Reset affine transform'))
        # reset_btn.setFixedWidth(45)
        reset_btn.clicked.connect(self.reset)
        layout.addWidget(reset_btn)

        self.frame.setLayout(layout)

    # def changeScale(self, value):
    #     new_scale = []
    #     for scale in self._sliders:
    #         new_scale.append(scale.value())
    #         affine = self.layer.affine
    #         affine.scale = new_scale
    #         self.layer.affine = affine

    def reset_scale(self):
        new_affine = self.layer.affine
        new_affine.scale = self._initial_affine.scale
        self.layer.affine = new_affine

    def reset_rotate(self):
        new_affine = self.layer.affine
        new_affine.rotate = self._initial_affine.rotate
        self.layer.affine = new_affine

    def reset_translate(self):
        new_affine = self.layer.affine
        new_affine.translate = self._initial_affine.translate
        self.layer.affine = new_affine

    def reset(self):
        self.layer.affine = self._initial_affine


class LayerFormLayout(QFormLayout):
    """Reusable form layout for subwidgets in each QtLayerControls class"""

    def __init__(self, QWidget=None) -> None:
        super().__init__(QWidget)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)
        self.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)


class QtLayerControls(QFrame):
    """Superclass for all the other LayerControl classes.

    This class is never directly instantiated anywhere.

    Parameters
    ----------
    layer : napari.layers.Layer
        An instance of a napari layer.

    Attributes
    ----------
    blendComboBox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    layer : napari.layers.Layer
        An instance of a napari layer.
    opacitySlider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    opacityLabel : qtpy.QtWidgets.QLabel
        Label for the opacity slider widget.
    """

    def __init__(self, layer: Layer) -> None:
        super().__init__()

        self._ndisplay: int = 2

        self.layer = layer
        self.layer.events.blending.connect(self._on_blending_change)
        self.layer.events.opacity.connect(self._on_opacity_change)

        self.setObjectName('layer')
        self.setMouseTracking(True)

        self.setLayout(LayerFormLayout(self))

        sld = QDoubleSlider(Qt.Orientation.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(1)
        sld.setSingleStep(0.01)
        sld.valueChanged.connect(self.changeOpacity)
        self.opacitySlider = sld
        self.opacityLabel = QLabel(trans._('opacity:'))

        self._on_opacity_change()

        blend_comboBox = QComboBox(self)
        for index, (data, text) in enumerate(BLENDING_TRANSLATIONS.items()):
            data = data.value
            blend_comboBox.addItem(text, data)
            if data == self.layer.blending:
                blend_comboBox.setCurrentIndex(index)

        blend_comboBox.currentTextChanged.connect(self.changeBlending)
        self.blendComboBox = blend_comboBox
        # opaque and minimum blending do not support changing alpha
        self.opacitySlider.setEnabled(
            self.layer.blending not in NO_OPACITY_BLENDING_MODES
        )
        self.opacityLabel.setEnabled(
            self.layer.blending not in NO_OPACITY_BLENDING_MODES
        )

        # scale widget
        self.scaleLabel = QLabel(trans._('scale:'))
        # self.scaleControl = QtScaleControl(layer, self)

    def changeOpacity(self, value):
        """Change opacity value on the layer model.

        Parameters
        ----------
        value : float
            Opacity value for shapes.
            Input range 0 - 100 (transparent to fully opaque).
        """
        with self.layer.events.blocker(self._on_opacity_change):
            self.layer.opacity = value

    def changeBlending(self, text):
        """Change blending mode on the layer model.

        Parameters
        ----------
        text : str
            Name of blending mode, eg: 'translucent', 'additive', 'opaque'.
        """
        self.layer.blending = self.blendComboBox.currentData()
        # opaque and minimum blending do not support changing alpha
        self.opacitySlider.setEnabled(
            self.layer.blending not in NO_OPACITY_BLENDING_MODES
        )
        self.opacityLabel.setEnabled(
            self.layer.blending not in NO_OPACITY_BLENDING_MODES
        )

        blending_tooltip = ''
        if self.layer.blending == str(Blending.MINIMUM):
            blending_tooltip = trans._(
                '`minimum` blending mode works best with inverted colormaps with a white background.',
            )
        self.blendComboBox.setToolTip(blending_tooltip)
        self.layer.help = blending_tooltip

    def _on_opacity_change(self):
        """Receive layer model opacity change event and update opacity slider."""
        with self.layer.events.opacity.blocker():
            self.opacitySlider.setValue(self.layer.opacity)

    def _on_blending_change(self):
        """Receive layer model blending mode change event and update slider."""
        with self.layer.events.blending.blocker():
            self.blendComboBox.setCurrentIndex(
                self.blendComboBox.findData(self.layer.blending)
            )

    @property
    def ndisplay(self) -> int:
        """The number of dimensions displayed in the canvas."""
        return self._ndisplay

    @ndisplay.setter
    def ndisplay(self, ndisplay: int) -> None:
        self._ndisplay = ndisplay
        self._on_ndisplay_changed()

    def _on_ndisplay_changed(self) -> None:
        """Respond to a change to the number of dimensions displayed in the viewer.

        This is needed because some layer controls may have options that are specific
        to 2D or 3D visualization only.
        """

    def deleteLater(self):
        disconnect_events(self.layer.events, self)
        super().deleteLater()

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.events, self)
        for child in self.children():
            close_method = getattr(child, 'close', None)
            if close_method is not None:
                close_method()
        return super().close()
