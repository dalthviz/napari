import typing

from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from superqt import QCollapsible

from napari._qt.qt_resources import QColoredSVGIcon
from napari._qt.widgets._slider_compat import QDoubleSlider
from napari.layers.base._base_constants import BLENDING_TRANSLATIONS, Blending
from napari.layers.base.base import Layer
from napari.settings import get_settings
from napari.utils.events import disconnect_events
from napari.utils.translations import trans

# opaque and minimum blending do not support changing alpha (opacity)
NO_OPACITY_BLENDING_MODES = {str(Blending.MINIMUM), str(Blending.OPAQUE)}


class LayerButtonsFlowLayout(QLayout):
    """
    Layout to enable dynamic space allocation for QtLayerControls buttons.

    Taken from https://forum.qt.io/post/565703
    TODO: Requires BSD Copyright note
    """

    def __init__(
        self,
        parent: QWidget = None,
        margin: int = -1,
        hSpacing: int = -1,
        vSpacing: int = -1,
    ):
        super().__init__(parent)

        self.itemList = []
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing

        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        # copied for consistency, not sure this is needed or ever called
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self.itemList.append(item)

    def horizontalSpacing(self) -> int:
        if self.m_hSpace >= 0:
            return self.m_hSpace
        return self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:
        if self.m_vSpace >= 0:
            return self.m_vSpace
        return self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def count(self) -> int:
        return len(self.itemList)

    def itemAt(self, index: int) -> typing.Union[QLayoutItem, None]:
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index: int) -> typing.Union[QLayoutItem, None]:
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(), margins.top() + margins.bottom()
        )
        return size

    def smartSpacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if not parent:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        return parent.spacing()

    def doLayout(self, rect: QRect, testOnly: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = wid.style().layoutSpacing(
                    QSizePolicy.PushButton,
                    QSizePolicy.PushButton,
                    Qt.Horizontal,
                )
            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = wid.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
                )

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom


class LayerFormLayout(QFormLayout):
    """Reusable form layout for subwidgets in each QtLayerControls class"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(4)
        self.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.setLabelAlignment(Qt.AlignmentFlag.AlignRight)


class QtCollapsibleLayerControlsSection(QCollapsible):
    """
    Customization of the QCollapsible class to set default icons and style.

    Uses a `LayerFormLayout` internally to organize added widgets to create
    layer controls collapsible sections. See `addRowToSection`
    """

    def __init__(self, title="", parent=None):
        # TODO: How to handle theme change with the icons?
        theme = get_settings().appearance.theme
        coll_icon = QColoredSVGIcon.from_resources('right_arrow').colored(
            theme=theme
        )
        exp_icon = QColoredSVGIcon.from_resources('down_arrow').colored(
            theme=theme
        )
        super().__init__(
            title=title,
            parent=parent,
            collapsedIcon=coll_icon,
            expandedIcon=exp_icon,
        )
        self.content().layout().setContentsMargins(0, 0, 0, 0)
        self.setProperty('emphasized', True)

        form_widget = QWidget()
        form_widget.setProperty('emphasized', True)

        self._internal_layout = LayerFormLayout()
        form_widget.setLayout(self._internal_layout)

        self.addWidget(form_widget)
        self.expand()

    def addRowToSection(self, *args):
        self._internal_layout.addRow(*args)


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
        self.layer.events.name.connect(self._on_name_change)

        self.setObjectName('layer')
        self.setMouseTracking(True)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        titleLayout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setProperty('layer_type_icon_label', True)
        icon_label.setObjectName(f'{self.layer._basename()}')
        titleLayout.addWidget(icon_label)
        self.name_label = QLabel(self.layer.name)
        self.name_label.setObjectName('layer_name')
        titleLayout.addWidget(self.name_label)
        titleLayout.addStretch(1)
        self.layout().addLayout(titleLayout)

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

        self.baseSection = QtCollapsibleLayerControlsSection("annotation")
        self.baseSection.addRowToSection(
            trans._('blending:'), self.blendComboBox
        )
        self.baseSection.addRowToSection(self.opacityLabel, self.opacitySlider)

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

    def _on_name_change(self):
        """Receive layer model name change event and update name label."""
        self.name_label.setText(self.layer.name)

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
