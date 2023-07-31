from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QComboBox,
)

from napari._qt.layer_controls.qt_image_controls_base import (
    QtBaseImageControls,
)
from napari.layers.surface._surface_constants import SHADING_TRANSLATION
from napari.utils.translations import trans

if TYPE_CHECKING:
    import napari.layers


class QtSurfaceControls(QtBaseImageControls):
    """Qt view and controls for the napari Surface layer.

    Parameters
    ----------
    layer : napari.layers.Surface
        An instance of a napari Surface layer.

    Attributes
    ----------
    layer : napari.layers.Surface
        An instance of a napari Surface layer.

    """

    layer: 'napari.layers.Surface'

    def __init__(self, layer) -> None:
        super().__init__(layer)

        # colormap_layout = QHBoxLayout()
        # colormap_layout.addWidget(self.colorbarLabel)
        # colormap_layout.addWidget(self.colormapComboBox)
        # colormap_layout.addStretch(1)

        shading_comboBox = QComboBox(self)
        for display_name, shading in SHADING_TRANSLATION.items():
            shading_comboBox.addItem(display_name, shading)
        index = shading_comboBox.findData(
            SHADING_TRANSLATION[self.layer.shading]
        )
        shading_comboBox.setCurrentIndex(index)
        shading_comboBox.currentTextChanged.connect(self.changeShading)
        self.shadingComboBox = shading_comboBox

        # self.layout().addRow(self.opacityLabel, self.opacitySlider)
        self.imagesSection.setText("surfaces")
        # self.layout().addRow(self.opacityLabel, self.opacitySlider)
        # self.surfaceSection.addRowToSection(
        #     trans._('contrast limits:'), self.contrastLimitsSlider
        # )
        # self.surfaceSection.addRowToSection(
        #     trans._('auto-contrast:'), self.autoScaleBar
        # )
        # self.surfaceSection.addRowToSection(
        #     trans._('gamma:'), self.gammaSlider
        # )
        # self.surfaceSection.addRowToSection(trans._('colormap:'), colormap_layout)
        # self.layout().addRow(trans._('blending:'), self.blendComboBox)
        self.imagesSection.addRowToSection(
            trans._('shading:'), self.shadingComboBox
        )

        # # TODO: Probably this should go inside the base class and a
        # # `addControlsSection(widget: QtCollapsibleLayerControlsSection`
        # # method should be added
        # controls_scroll = QScrollArea()
        # controls_scroll.setWidgetResizable(True)
        # controls_scroll.setHorizontalScrollBarPolicy(
        #     Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        # )
        # controls_widget = QWidget()
        # controls_layout = QVBoxLayout()
        # controls_layout.addWidget(self.baseSection)
        # controls_layout.addWidget(self.surfaceSection)
        # controls_layout.addStretch(1)
        # controls_widget.setLayout(controls_layout)
        # controls_scroll.setWidget(controls_widget)

        # # TODO: Probably this should go inside the base class too if
        # # methods to add buttons and sections are available
        # self.layout().addWidget(controls_scroll)

    def changeShading(self, text):
        """Change shading value on the surface layer.
        Parameters
        ----------
        text : str
            Name of shading mode, eg: 'flat', 'smooth', 'none'.
        """
        self.layer.shading = self.shadingComboBox.currentData()
