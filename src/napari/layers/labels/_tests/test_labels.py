import copy
import itertools
import time
from collections import defaultdict
from dataclasses import dataclass
from importlib.metadata import version

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
import xarray as xr
import zarr
from packaging.version import parse as parse_version
from skimage import data as sk_data

from napari._tests.utils import check_layer_world_data_extent
from napari.components import ViewerModel
from napari.components.dims import Dims
from napari.layers import Labels
from napari.layers.labels._labels_constants import LabelsRendering
from napari.layers.labels._labels_utils import get_contours
from napari.utils import Colormap
from napari.utils._test_utils import (
    validate_all_params_in_docstring,
    validate_kwargs_sorted,
)
from napari.utils.colormaps import (
    CyclicLabelColormap,
    DirectLabelColormap,
    label_colormap,
)


@pytest.fixture
def direct_colormap():
    """Return a DirectLabelColormap."""
    return DirectLabelColormap(
        color_dict={
            0: [0, 0, 0, 0],
            1: [1, 0, 0, 1],
            2: [0, 1, 0, 1],
            None: [0, 0, 1, 1],
        }
    )


@pytest.fixture
def random_colormap():
    """Return a LabelColormap."""
    return label_colormap(50)


def test_random_labels():
    """Test instantiating Labels layer with random 2D data."""
    shape = (10, 15)
    np.random.seed(0)
    data = np.random.randint(20, size=shape)
    layer = Labels(data)
    np.testing.assert_array_equal(layer.data, data)
    assert layer.ndim == len(shape)
    np.testing.assert_array_equal(layer.extent.data[1], [s - 1 for s in shape])
    assert layer._data_view.shape == shape[-2:]
    assert layer.editable is True


def test_all_zeros_labels():
    """Test instantiating Labels layer with all zeros data."""
    shape = (10, 15)
    data = np.zeros(shape, dtype=int)
    layer = Labels(data)
    np.testing.assert_array_equal(layer.data, data)
    assert layer.ndim == len(shape)
    np.testing.assert_array_equal(layer.extent.data[1], [s - 1 for s in shape])
    assert layer._data_view.shape == shape[-2:]


def test_3D_labels():
    """Test instantiating Labels layer with random 3D data."""
    shape = (6, 10, 15)
    np.random.seed(0)
    data = np.random.randint(20, size=shape)
    layer = Labels(data)
    np.testing.assert_array_equal(layer.data, data)
    assert layer.ndim == len(shape)
    np.testing.assert_array_equal(layer.extent.data[1], [s - 1 for s in shape])
    assert layer._data_view.shape == shape[-2:]
    assert layer.editable is True

    layer._slice_dims(Dims(ndim=3, ndisplay=3))
    assert layer.editable is True
    assert layer.mode == 'pan_zoom'


def test_float_labels():
    """Test instantiating labels layer with floats"""
    np.random.seed(0)
    data = np.random.uniform(0, 20, size=(10, 10))
    with pytest.raises(TypeError):
        Labels(data)

    data0 = np.random.uniform(20, size=(20, 20))
    data1 = data0[::2, ::2].astype(np.int32)
    data = [data0, data1]
    with pytest.raises(TypeError):
        Labels(data)


def test_bool_labels():
    """Test instantiating labels layer with bools"""
    data = np.zeros((10, 10), dtype=bool)
    layer = Labels(data)
    assert np.issubdtype(layer.data.dtype, np.integer)

    data0 = np.zeros((20, 20), dtype=bool)
    data1 = data0[::2, ::2].astype(np.int32)
    data = [data0, data1]
    layer = Labels(data)
    assert all(np.issubdtype(d.dtype, np.integer) for d in layer.data)


def test_editing_bool_labels():
    # make random data, mostly 0s
    data = np.random.random((10, 10)) > 0.7
    # create layer, which may convert bool to uint8 *as a view*
    layer = Labels(data)
    # paint the whole layer with 1
    layer.paint_polygon(
        points=[[-1, -1], [-1, 11], [11, 11], [11, -1]],
        new_label=1,
    )
    # check that the original data has been correspondingly modified
    assert np.all(data)


def test_changing_labels():
    """Test changing Labels data."""
    shape_a = (10, 15)
    shape_b = (20, 12)
    shape_c = (10, 10)
    np.random.seed(0)
    data_a = np.random.randint(20, size=shape_a)
    data_b = np.random.randint(20, size=shape_b)
    layer = Labels(data_a)
    layer.data = data_b
    np.testing.assert_array_equal(layer.data, data_b)
    assert layer.ndim == len(shape_b)
    np.testing.assert_array_equal(
        layer.extent.data[1], [s - 1 for s in shape_b]
    )
    assert layer._data_view.shape == shape_b[-2:]

    data_c = np.zeros(shape_c, dtype=bool)
    layer.data = data_c
    assert np.issubdtype(layer.data.dtype, np.integer)

    data_c = data_c.astype(np.float32)
    with pytest.raises(TypeError):
        layer.data = data_c


def test_changing_labels_dims():
    """Test changing Labels data including dimensionality."""
    shape_a = (10, 15)
    shape_b = (20, 12, 6)
    np.random.seed(0)
    data_a = np.random.randint(20, size=shape_a)
    data_b = np.random.randint(20, size=shape_b)
    layer = Labels(data_a)

    layer.data = data_b
    np.testing.assert_array_equal(layer.data, data_b)
    assert layer.ndim == len(shape_b)
    np.testing.assert_array_equal(
        layer.extent.data[1], [s - 1 for s in shape_b]
    )
    assert layer._data_view.shape == shape_b[-2:]


def test_changing_modes():
    """Test changing modes."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.mode == 'pan_zoom'
    assert layer.mouse_pan is True

    layer.mode = 'fill'
    assert layer.mode == 'fill'
    assert layer.mouse_pan is False

    layer.mode = 'paint'
    assert layer.mode == 'paint'
    assert layer.mouse_pan is False

    layer.mode = 'pick'
    assert layer.mode == 'pick'
    assert layer.mouse_pan is False

    layer.mode = 'polygon'
    assert layer.mode == 'polygon'
    assert layer.mouse_pan is False

    layer.mode = 'pan_zoom'
    assert layer.mode == 'pan_zoom'
    assert layer.mouse_pan is True

    layer.mode = 'paint'
    assert layer.mode == 'paint'
    layer.editable = False
    assert layer.mode == 'pan_zoom'
    assert layer.editable is False


def test_name():
    """Test setting layer name."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.name == 'Labels'

    layer = Labels(data, name='random')
    assert layer.name == 'random'

    layer.name = 'lbls'
    assert layer.name == 'lbls'


def test_visiblity():
    """Test setting layer visibility."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.visible is True

    layer.visible = False
    assert layer.visible is False

    layer = Labels(data, visible=False)
    assert layer.visible is False

    layer.visible = True
    assert layer.visible is True


def test_opacity():
    """Test setting layer opacity."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.opacity == 0.7

    layer.opacity = 0.5
    assert layer.opacity == 0.5

    layer = Labels(data, opacity=0.6)
    assert layer.opacity == 0.6

    layer.opacity = 0.3
    assert layer.opacity == 0.3


def test_blending():
    """Test setting layer blending."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.blending == 'translucent'

    layer.blending = 'additive'
    assert layer.blending == 'additive'

    layer = Labels(data, blending='additive')
    assert layer.blending == 'additive'

    layer.blending = 'opaque'
    assert layer.blending == 'opaque'


@pytest.mark.filterwarnings('ignore:.*seed is deprecated.*')
def test_properties():
    """Test adding labels with properties."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))

    layer = Labels(data)
    assert isinstance(layer.properties, dict)
    assert len(layer.properties) == 0

    properties = {
        'class': np.array(['Background'] + [f'Class {i}' for i in range(20)])
    }
    label_index = {i: i for i in range(len(properties['class']))}
    layer = Labels(data, properties=properties)
    assert isinstance(layer.properties, dict)
    np.testing.assert_equal(layer.properties, properties)
    assert layer._label_index == label_index
    layer = Labels(data)
    layer.properties = properties
    assert isinstance(layer.properties, dict)
    np.testing.assert_equal(layer.properties, properties)
    assert layer._label_index == label_index

    current_label = layer.get_value((0, 0))
    layer_message = layer.get_status((0, 0))
    assert layer_message['coordinates'].endswith(f'Class {current_label - 1}')

    properties = {'class': ['Background']}
    layer = Labels(data, properties=properties)
    layer_message = layer.get_status((0, 0))
    assert layer_message['coordinates'].endswith('[No Properties]')

    properties = {'class': ['Background', 'Class 12'], 'index': [0, 12]}
    label_index = {0: 0, 12: 1}
    layer = Labels(data, properties=properties)
    layer_message = layer.get_status((0, 0))
    assert layer._label_index == label_index
    assert layer_message['coordinates'].endswith('Class 12')

    layer = Labels(data)
    layer.properties = properties
    layer_message = layer.get_status((0, 0))
    assert layer._label_index == label_index
    assert layer_message['coordinates'].endswith('Class 12')

    layer = Labels(data)
    layer.properties = pd.DataFrame(properties)
    layer_message = layer.get_status((0, 0))
    assert layer._label_index == label_index
    assert layer_message['coordinates'].endswith('Class 12')


def test_default_properties_assignment():
    """Test that the default properties value can be assigned to properties
    see https://github.com/napari/napari/issues/2477
    """
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))

    layer = Labels(data)
    layer.properties = {}
    assert layer.properties == {}


def test_multiscale_properties():
    """Test adding labels with multiscale properties."""
    np.random.seed(0)
    data0 = np.random.randint(20, size=(10, 15))
    data1 = data0[::2, ::2]
    data = [data0, data1]

    layer = Labels(data)
    assert isinstance(layer.properties, dict)
    assert len(layer.properties) == 0

    properties = {
        'class': np.array(['Background'] + [f'Class {i}' for i in range(20)])
    }
    label_index = {i: i for i in range(len(properties['class']))}
    layer = Labels(data, properties=properties)
    assert isinstance(layer.properties, dict)
    np.testing.assert_equal(layer.properties, properties)
    assert layer._label_index == label_index

    current_label = layer.get_value((0, 0))[1]
    layer_message = layer.get_status((0, 0))
    assert layer_message['coordinates'].endswith(f'Class {current_label - 1}')

    properties = {'class': ['Background']}
    layer = Labels(data, properties=properties)
    layer_message = layer.get_status((0, 0))
    assert layer_message['coordinates'].endswith('[No Properties]')

    properties = {'class': ['Background', 'Class 12'], 'index': [0, 12]}
    label_index = {0: 0, 12: 1}
    layer = Labels(data, properties=properties)
    layer_message = layer.get_status((0, 0))
    assert layer._label_index == label_index
    assert layer_message['coordinates'].endswith('Class 12')


def test_colormap():
    """Test colormap."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert isinstance(layer.colormap, Colormap)
    assert layer.colormap.name == 'label_colormap'

    layer.new_colormap()
    assert isinstance(layer.colormap, Colormap)
    assert layer.colormap.name == 'label_colormap'


def test_label_colormap():
    """Test a label colormap."""
    colormap = label_colormap(num_colors=4)

    # Make sure color 0 is transparent
    assert not np.any(colormap.map([0.0]))

    # test that all four colors are represented in a large set of random
    # labels.
    # we choose non-zero labels, and then there should not be any transparent
    # values.
    labels = np.random.randint(1, 2**23, size=(100, 100)).astype(np.float32)
    colormapped = colormap.map(labels)
    linear = np.reshape(colormapped, (-1, 4))
    unique = np.unique(linear, axis=0)
    assert len(unique) == 4


def test_custom_color_dict():
    """Test custom color dict."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    cmap = DirectLabelColormap(
        color_dict=defaultdict(
            lambda: 'black',
            {2: 'white', 4: 'red', 8: 'blue', 16: 'red', 32: 'blue'},
        )
    )
    layer = Labels(data, colormap=cmap)

    # test with custom color dict
    assert isinstance(layer.get_color(2), np.ndarray)
    assert isinstance(layer.get_color(1), np.ndarray)
    assert (layer.get_color(2) == np.array([1.0, 1.0, 1.0, 1.0])).all()
    assert (layer.get_color(4) == layer.get_color(16)).all()
    assert (layer.get_color(8) == layer.get_color(32)).all()

    # test disable custom color dict
    # should not initialize as white since we are using random.seed
    assert not (layer.get_color(1) == np.array([1.0, 1.0, 1.0, 1.0])).all()


@pytest.mark.parametrize(
    'colormap_like',
    [
        ['red', 'blue'],
        [[1, 0, 0, 1], [0, 0, 1, 1]],
        {None: 'transparent', 1: 'red', 2: 'blue'},
        {None: [0, 0, 0, 0], 1: [1, 0, 0, 1], 2: [0, 0, 1, 1]},
        defaultdict(lambda: 'transparent', {1: 'red', 2: 'blue'}),
    ],
)
def test_colormap_simple_data_types(colormap_like):
    """Test that setting colormap with list or dict of colors works."""
    data = np.random.randint(20, size=(10, 15))
    # test in constructor
    _ = Labels(data, colormap=colormap_like)
    # test assignment
    layer = Labels(data)
    layer.colormap = colormap_like


def test_metadata():
    """Test setting labels metadata."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.metadata == {}

    layer = Labels(data, metadata={'unit': 'cm'})
    assert layer.metadata == {'unit': 'cm'}


def test_brush_size():
    """Test changing brush size."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.brush_size == 10

    layer.brush_size = 20
    assert layer.brush_size == 20


def test_contiguous():
    """Test changing contiguous."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.contiguous is True

    layer.contiguous = False
    assert layer.contiguous is False


def test_n_edit_dimensions():
    """Test changing the number of editable dimensions."""
    np.random.seed(0)
    data = np.random.randint(20, size=(5, 10, 15))
    layer = Labels(data)
    layer.n_edit_dimensions = 2
    layer.n_edit_dimensions = 3


@pytest.mark.parametrize(
    ('input_data', 'expected_data_view'),
    [
        (
            np.array(
                [
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 5, 5, 5, 0, 0],
                    [0, 0, 1, 1, 1, 5, 5, 5, 0, 0],
                    [0, 0, 1, 1, 1, 5, 5, 5, 0, 0],
                    [0, 0, 1, 1, 1, 5, 5, 5, 0, 0],
                    [0, 0, 0, 0, 0, 5, 5, 5, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                ],
                dtype=np.int_,
            ),
            np.array(
                [
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 5, 5, 5, 0, 0],
                    [0, 0, 1, 1, 1, 5, 0, 5, 0, 0],
                    [0, 0, 1, 0, 1, 5, 0, 5, 0, 0],
                    [0, 0, 1, 1, 1, 5, 0, 5, 0, 0],
                    [0, 0, 0, 0, 0, 5, 5, 5, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                ],
                dtype=np.int_,
            ),
        ),
        (
            np.array(
                [
                    [1, 1, 0, 0, 0, 0, 0, 2, 2, 2],
                    [1, 1, 0, 0, 0, 0, 0, 2, 2, 2],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 4, 4, 4, 4],
                    [3, 3, 3, 0, 0, 0, 4, 4, 4, 4],
                    [3, 3, 3, 0, 0, 0, 4, 4, 4, 4],
                    [3, 3, 3, 0, 0, 0, 4, 4, 4, 4],
                ],
                dtype=np.int_,
            ),
            np.array(
                [
                    [0, 1, 0, 0, 0, 0, 0, 2, 0, 0],
                    [1, 1, 0, 0, 0, 0, 0, 2, 2, 2],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 4, 4, 4, 4],
                    [3, 3, 3, 0, 0, 0, 4, 0, 0, 0],
                    [0, 0, 3, 0, 0, 0, 4, 0, 0, 0],
                    [0, 0, 3, 0, 0, 0, 4, 0, 0, 0],
                ],
                dtype=np.int_,
            ),
        ),
        (
            5 * np.ones((9, 10), dtype=np.uint32),
            np.zeros((9, 10), dtype=np.uint32),
        ),
    ],
    ids=['touching objects', 'touching border', 'full array'],
)
def test_contour(input_data, expected_data_view):
    """Test changing contour."""
    layer = Labels(input_data)
    assert layer.contour == 0
    np.testing.assert_array_equal(layer.data, input_data)

    np.testing.assert_array_equal(
        layer._raw_to_displayed(input_data),
        layer._data_view,
    )
    data_view_before_contour = layer._data_view.copy()

    layer.contour = 1
    assert layer.contour == 1

    # Check `layer.data` didn't change
    np.testing.assert_array_equal(layer.data, input_data)

    # Check what is returned in the view of the data
    np.testing.assert_array_equal(
        layer._data_view,
        np.where(
            expected_data_view > 0,
            expected_data_view,
            0,
        ),
    )

    # Check the view of the data changed after setting the contour
    with np.testing.assert_raises(AssertionError):
        np.testing.assert_array_equal(
            data_view_before_contour, layer._data_view
        )

    layer.contour = 0
    assert layer.contour == 0

    # Check it's in the same state as before setting the contour
    np.testing.assert_array_equal(
        layer._raw_to_displayed(input_data), layer._data_view
    )

    with pytest.raises(ValueError, match='contour value must be >= 0'):
        layer.contour = -1


@pytest.mark.parametrize('background_num', [0, 1, 2, -1])
def test_background_label(background_num):
    data = np.zeros((10, 10), dtype=np.int32)
    data[1:-1, 1:-1] = 1
    data[2:-2, 2:-2] = 2
    data[4:-4, 4:-4] = -1

    layer = Labels(data)
    layer.colormap = label_colormap(49, background_value=background_num)
    np.testing.assert_array_equal(
        layer._data_view == 0, data == background_num
    )
    np.testing.assert_array_equal(
        layer._data_view != 0, data != background_num
    )


def test_contour_large_new_labels():
    """Check that new labels larger than the lookup table work in contour mode.

    References
    ----------
    [1]: https://forum.image.sc/t/data-specific-reason-for-indexerror-in-raw-to-displayed/60808
    [2]: https://github.com/napari/napari/pull/3697
    """
    viewer = ViewerModel()

    labels = np.zeros((5, 10, 10), dtype=int)
    labels[0, 4:6, 4:6] = 1
    labels[4, 4:6, 4:6] = 1000
    labels_layer = viewer.add_labels(labels)
    labels_layer.contour = 1
    # This used to fail with IndexError
    viewer.dims.set_point(axis=0, value=4)


def test_contour_local_updates():
    """Checks if contours are rendered correctly with local updates"""
    data = np.zeros((7, 7), dtype=np.int32)

    layer = Labels(data)
    layer.contour = 1
    assert np.allclose(
        layer._raw_to_displayed(layer._slice.image.raw),
        np.zeros((7, 7), dtype=np.float32),
    )

    painting_mask = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 1, 1, 0, 0],
            [0, 0, 1, 1, 1, 0, 0],
            [0, 0, 1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ],
        dtype=np.int32,
    )

    layer.data_setitem(np.nonzero(painting_mask), 1, refresh=True)

    assert np.array_equiv(
        (layer._slice.image.view > 0), get_contours(painting_mask, 1, 0)
    )


def test_data_setitem_multi_dim():
    """
    this test checks if data_setitem works when some of the indices are
    outside currently rendered slice
    """
    # create zarr zeros array in memory
    data = zarr.zeros((10, 10, 10), chunks=(5, 5, 5), dtype=np.uint32)
    labels = Labels(data)
    labels.data_setitem(
        (np.array([0, 1, 1]), np.array([1, 1, 2]), np.array([0, 0, 0])),
        [1, 2, 0],
    )


def test_data_setitiem_transposed_axes():
    data = np.zeros((10, 100), dtype=np.uint32)
    labels = Labels(data)
    dims = Dims(ndim=2, ndisplay=2, order=(1, 0))
    labels.data_setitem((np.array([9]), np.array([99])), 1)
    labels._slice_dims(dims)
    labels.data_setitem((np.array([9]), np.array([99])), 2)


def test_selecting_label():
    """Test selecting label."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    assert layer.selected_label == 1
    assert (layer._selected_color == layer.get_color(1)).all

    layer.selected_label = 1
    assert layer.selected_label == 1
    assert len(layer._selected_color) == 4


def test_label_color():
    """Test getting label color."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    col = layer.get_color(0)
    assert col is None

    col = layer.get_color(1)
    assert len(col) == 4


def test_show_selected_label():
    """Test color of labels when filtering to selected labels"""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    original_color = layer.get_color(1)

    layer.show_selected_label = True
    original_background_color = layer.get_color(
        layer.colormap.background_value
    )
    none_color = layer.get_color(None)
    layer.selected_label = 1

    # color of selected label has not changed
    assert np.allclose(layer.get_color(layer.selected_label), original_color)

    current_background_color = layer.get_color(layer.colormap.background_value)
    # color of background is background color
    assert current_background_color == original_background_color

    # color of all others is none color
    other_labels = np.unique(layer.data)[2:]
    other_colors = np.array([layer.get_color(x) for x in other_labels])
    assert np.allclose(other_colors, none_color)


def test_paint():
    """Test painting labels with different circle brush sizes."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    data[:10, :10] = 1
    layer = Labels(data)

    assert np.unique(layer.data[:5, :5]) == 1
    assert np.unique(layer.data[5:10, 5:10]) == 1

    layer.brush_size = 9
    layer.paint([0, 0], 2)
    assert np.unique(layer.data[:4, :4]) == 2
    assert np.unique(layer.data[5:10, 5:10]) == 1

    layer.brush_size = 10
    layer.paint([0, 0], 2)
    assert np.unique(layer.data[0:6, 0:3]) == 2
    assert np.unique(layer.data[0:3, 0:6]) == 2
    assert np.unique(layer.data[6:10, 6:10]) == 1

    layer.brush_size = 19
    layer.paint([0, 0], 2)
    assert np.unique(layer.data[0:4, 0:10]) == 2
    assert np.unique(layer.data[0:10, 0:4]) == 2
    assert np.unique(layer.data[3:7, 3:7]) == 2
    assert np.unique(layer.data[7:10, 7:10]) == 1


def test_paint_with_preserve_labels():
    """Test painting labels with square brush while preserving existing labels."""
    data = np.zeros((15, 10), dtype=np.uint32)
    data[:3, :3] = 1
    layer = Labels(data)

    layer.preserve_labels = True
    assert np.unique(layer.data[:3, :3]) == 1

    layer.brush_size = 9
    layer.paint([0, 0], 2)

    assert np.unique(layer.data[3:5, 0:3]) == 2
    assert np.unique(layer.data[0:3, 3:5]) == 2
    assert np.unique(layer.data[:3, :3]) == 1


def test_setting_prev_selected_label():
    """Test that _prev_selected_label is set when selected_label
    is set to the colormap background_value."""
    data = np.zeros((15, 10), dtype=np.uint32)
    layer = Labels(data)

    # set the selected label, _prev_selected_label should be None
    layer.selected_label = 1
    assert not layer._prev_selected_label

    layer.selected_label = layer.colormap.background_value
    assert layer._prev_selected_label == 1

    layer.selected_label = 2
    # swap the selected and background labels
    # _prev_selected_label should be set
    layer.swap_selected_and_background_labels()
    assert layer.selected_label == layer.colormap.background_value
    assert layer._prev_selected_label == 2


def test_paint_swap_with_preserve_labels():
    """Test painting and swapping labels & background while preserving labels."""
    data = np.zeros((15, 10), dtype=np.uint32)
    data[:3, :3] = 1
    layer = Labels(data)

    layer.preserve_labels = True
    assert np.unique(layer.data[:3, :3]) == 1

    layer.brush_size = 9
    layer.selected_label = 2
    layer.paint([0, 0], layer.selected_label)

    assert np.unique(layer.data[3:5, 0:3]) == 2
    assert np.unique(layer.data[0:3, 3:5]) == 2
    assert np.unique(layer.data[:3, :3]) == 1

    current_label = layer.selected_label
    layer.swap_selected_and_background_labels()
    assert layer.selected_label == 0
    assert layer._prev_selected_label == current_label
    layer.paint([0, 0], layer.selected_label)

    # only label 2 should be erased
    assert np.unique(layer.data[3:5, 0:3]) == 0
    assert np.unique(layer.data[0:3, 3:5]) == 0
    assert np.unique(layer.data[:3, :3]) == 1


def test_paint_2d():
    """Test painting labels with circle brush."""
    data = np.zeros((40, 40), dtype=np.uint32)
    layer = Labels(data)
    layer.brush_size = 12
    layer.mode = 'paint'
    layer.paint((0, 0), 3)

    layer.brush_size = 12
    layer.paint((15, 8), 4)

    layer.brush_size = 13
    layer.paint((30.2, 7.8), 5)

    layer.brush_size = 12
    layer.paint((39, 39), 6)

    layer.brush_size = 20
    layer.paint((15, 27), 7)

    assert np.sum(layer.data[:8, :8] == 3) == 41
    assert np.sum(layer.data[9:22, 2:15] == 4) == 137
    assert np.sum(layer.data[24:37, 2:15] == 5) == 137
    assert np.sum(layer.data[33:, 33:] == 6) == 41
    assert np.sum(layer.data[5:26, 17:38] == 7) == 349


def test_paint_2d_xarray():
    """Test the memory usage of painting a xarray indirectly via timeout."""
    now = time.monotonic()
    data = xr.DataArray(np.zeros((3, 3, 1024, 1024), dtype=np.uint32))

    layer = Labels(data)
    layer.brush_size = 12
    layer.mode = 'paint'
    layer.paint((1, 1, 512, 512), 3)
    assert isinstance(layer.data, xr.DataArray)
    assert layer.data.sum() == 411
    elapsed = time.monotonic() - now
    assert elapsed < 1, 'test was too slow, computation was likely not lazy'


def test_paint_3d():
    """Test painting labels with circle brush on 3D image."""
    data = np.zeros((30, 40, 40), dtype=np.uint32)
    layer = Labels(data)
    layer.brush_size = 12
    layer.mode = 'paint'

    # Paint in 2D
    layer.paint((10, 10, 10), 3)

    # Paint in 3D
    layer.n_edit_dimensions = 3
    layer.paint((10, 25, 10), 4)

    # Paint in 3D, preserve labels
    layer.n_edit_dimensions = 3
    layer.preserve_labels = True
    layer.paint((10, 15, 15), 5)

    assert np.sum(layer.data[4:17, 4:17, 4:17] == 3) == 137
    assert np.sum(layer.data[4:17, 19:32, 4:17] == 4) == 1189
    assert np.sum(layer.data[4:17, 9:32, 9:32] == 5) == 1103


def test_paint_polygon():
    """Test painting labels with polygons."""
    data = np.zeros((10, 15), dtype=int)
    data[:10, :10] = 1
    layer = Labels(data)

    layer.paint_polygon([[0, 0], [0, 5], [5, 5], [5, 0]], 2)
    assert np.array_equiv(layer.data[:5, :5], 2)
    assert np.array_equiv(layer.data[:10, 6:10], 1)
    assert np.array_equiv(layer.data[6:10, :10], 1)

    layer.paint_polygon([[7, 7], [7, 7], [7, 7]], 3)
    assert layer.data[7, 7] == 3
    assert np.array_equiv(
        layer.data[[6, 7, 8, 7, 8, 6], [7, 6, 7, 8, 8, 6]], 1
    )

    data[:10, :10] = 0
    gt_pattern = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 1, 1, 1, 1, 0],
            [0, 1, 1, 1, 1, 1, 1, 0],
            [0, 1, 1, 0, 0, 1, 1, 0],
            [0, 1, 1, 0, 0, 1, 1, 0],
            [0, 1, 1, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )
    polygon_points = [
        [1, 1],
        [1, 6],
        [5, 6],
        [5, 5],
        [2, 5],
        [2, 2],
        [5, 2],
        [5, 1],
    ]
    layer.paint_polygon(polygon_points, 1)
    assert np.allclose(layer.data[:7, :8], gt_pattern)

    data[:10, :10] = 0
    layer.paint_polygon(polygon_points[::-1], 1)
    assert np.allclose(layer.data[:7, :8], gt_pattern)


def test_paint_polygon_2d_in_3d():
    """Test painting labels with polygons in a 3D array"""
    data = np.zeros((3, 10, 10), dtype=int)
    layer = Labels(data)

    assert layer.n_edit_dimensions == 2

    layer.paint_polygon([[1, 0, 0], [1, 0, 9], [1, 9, 9], [1, 9, 0]], 1)

    assert np.array_equiv(data[1, :], 1)
    assert np.array_equiv(data[[0, 2], :], 0)


def test_fill():
    """Test filling labels with different brush sizes."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    data[:10, :10] = 2
    data[:5, :5] = 1
    layer = Labels(data)
    assert np.unique(layer.data[:5, :5]) == 1
    assert np.unique(layer.data[5:10, 5:10]) == 2

    layer.fill([0, 0], 3)
    assert np.unique(layer.data[:5, :5]) == 3
    assert np.unique(layer.data[5:10, 5:10]) == 2


def test_fill_swap_with_preserve_labels():
    """Test fill and swap background while preserving existing labels."""
    data = np.zeros((15, 10), dtype=np.uint32)
    data[:3, :3] = 1
    layer = Labels(data)

    layer.preserve_labels = True
    assert np.unique(layer.data[:3, :3]) == 1

    layer.selected_label = 2
    prev_layer_data = layer.data
    layer.fill([0, 0], layer.selected_label)
    # existing label should not be filled
    assert np.all(layer.data == prev_layer_data)

    layer.fill([3, 3], layer.selected_label)
    # background should be filled
    assert np.unique(layer.data[3:, 0:3]) == 2
    assert np.unique(layer.data[0:3, 3:]) == 2
    # existing label should not be filled
    assert np.unique(layer.data[:3, :3]) == 1

    current_label = layer.selected_label
    layer.swap_selected_and_background_labels()
    assert layer.selected_label == 0
    assert layer._prev_selected_label == current_label
    prev_layer_data = layer.data
    layer.fill([0, 0], layer.selected_label)
    # existing label should not be erased
    assert np.all(layer.data == prev_layer_data)

    layer.fill([3, 3], layer.selected_label)
    # the pre-swap label should be erassed
    assert np.unique(layer.data[3:, 0:3]) == 0
    assert np.unique(layer.data[0:3, 3:]) == 0
    # existing label should not be filled
    assert np.unique(layer.data[:3, :3]) == 1


def test_value():
    """Test getting the value of the data at the current coordinates."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    value = layer.get_value((0, 0))
    assert value == data[0, 0]


@pytest.mark.parametrize(
    ('position', 'view_direction', 'dims_displayed', 'world'),
    [
        ([10, 5, 5], [1, 0, 0], [0, 1, 2], False),
        ([10, 5, 5], [1, 0, 0], [0, 1, 2], True),
        ([0, 10, 5, 5], [0, 1, 0, 0], [1, 2, 3], True),
    ],
)
def test_value_3d(position, view_direction, dims_displayed, world):
    """get_value should return label value in 3D"""
    data = np.zeros((20, 20, 20), dtype=int)
    data[0:10, 0:10, 0:10] = 1
    layer = Labels(data)
    layer._slice_dims(Dims(ndim=3, ndisplay=3))
    value = layer.get_value(
        position,
        view_direction=view_direction,
        dims_displayed=dims_displayed,
        world=world,
    )
    assert value == 1


def test_message():
    """Test converting value and coords to message."""
    np.random.seed(0)
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    msg = layer.get_status((0, 0))
    assert isinstance(msg, dict)


def test_thumbnail():
    """Test the image thumbnail for square data."""
    np.random.seed(0)
    data = np.random.randint(20, size=(30, 30))
    layer = Labels(data)
    layer._update_thumbnail()
    assert layer.thumbnail.shape == layer._thumbnail_shape


@pytest.mark.parametrize('value', [1, 10, 50, -2, -10])
@pytest.mark.parametrize('dtype', [np.int8, np.int32])
def test_thumbnail_single_color(value, dtype):
    labels = Labels(np.full((10, 10), value, dtype=dtype), opacity=1)
    labels._update_thumbnail()
    mid_point = tuple(np.array(labels.thumbnail.shape[:2]) // 2)
    npt.assert_array_equal(
        labels.thumbnail[mid_point], labels.get_color(value) * 255
    )


def test_world_data_extent():
    """Test extent after applying transforms."""
    np.random.seed(0)
    shape = (6, 10, 15)
    data = np.random.randint(20, size=shape)
    layer = Labels(data)
    extent = np.array(((0,) * 3, [s - 1 for s in shape]))
    check_layer_world_data_extent(layer, extent, (3, 1, 1), (10, 20, 5))


@pytest.mark.parametrize(
    (
        'brush_size',
        'mode',
        'selected_label',
        'preserve_labels',
        'n_edit_dimensions',
    ),
    list(
        itertools.product(
            list(range(1, 22, 5)),
            ['fill', 'erase', 'paint'],
            [1, 20, 100],
            [True, False],
            [3, 2],
        )
    ),
)
def test_undo_redo(
    brush_size,
    mode,
    selected_label,
    preserve_labels,
    n_edit_dimensions,
):
    blobs = sk_data.binary_blobs(length=64, volume_fraction=0.3, n_dim=3)
    layer = Labels(blobs)
    data_history = [blobs.copy()]
    layer.brush_size = brush_size
    layer.mode = mode
    layer.selected_label = selected_label
    layer.preserve_labels = preserve_labels
    layer.n_edit_dimensions = n_edit_dimensions
    coord = np.random.random((3,)) * (np.array(blobs.shape) - 1)
    while layer.data[tuple(coord.astype(int))] == 0 and np.any(layer.data):
        coord = np.random.random((3,)) * (np.array(blobs.shape) - 1)
    if layer.mode == 'fill':
        layer.fill(coord, layer.selected_label)
    if layer.mode == 'erase':
        layer.paint(coord, 0)
    if layer.mode == 'paint':
        layer.paint(coord, layer.selected_label)
    data_history.append(np.copy(layer.data))
    layer.undo()
    np.testing.assert_array_equal(layer.data, data_history[0])
    layer.redo()
    np.testing.assert_array_equal(layer.data, data_history[1])


def test_ndim_fill():
    test_array = np.zeros((5, 5, 5, 5), dtype=int)

    test_array[:, 1:3, 1:3, 1:3] = 1

    layer = Labels(test_array)
    layer.n_edit_dimensions = 3

    layer.fill((0, 1, 1, 1), 2)

    np.testing.assert_equal(layer.data[0, 1:3, 1:3, 1:3], 2)
    np.testing.assert_equal(layer.data[1, 1:3, 1:3, 1:3], 1)

    layer.n_edit_dimensions = 4

    layer.fill((1, 1, 1, 1), 3)

    np.testing.assert_equal(layer.data[0, 1:3, 1:3, 1:3], 2)
    np.testing.assert_equal(layer.data[1:, 1:3, 1:3, 1:3], 3)


def test_ndim_paint():
    test_array = np.zeros((5, 6, 7, 8), dtype=int)
    layer = Labels(test_array)
    layer.n_edit_dimensions = 3
    layer.brush_size = 2  # equivalent to 18-connected 3D neighborhood
    layer.paint((1, 1, 1, 1), 1)

    assert np.sum(layer.data) == 19  # 18 + center
    assert not np.any(layer.data[0])
    assert not np.any(layer.data[2:])

    layer.n_edit_dimensions = 2  # 3x3 square
    layer._slice_dims(Dims(ndim=4, order=(1, 2, 0, 3)))
    layer.paint((4, 5, 6, 7), 8)
    assert len(np.flatnonzero(layer.data == 8)) == 4  # 2D square is in corner
    np.testing.assert_array_equal(
        test_array[:, 5, 6, :],
        np.array(
            [
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 8, 8],
                [0, 0, 0, 0, 0, 0, 8, 8],
            ]
        ),
    )


def test_cursor_size_with_negative_scale():
    layer = Labels(np.zeros((5, 5), dtype=int), scale=[-1, -1])
    layer.mode = 'paint'
    assert layer.cursor_size > 0


def test_large_label_values():
    label_array = 2**23 + np.arange(4, dtype=np.uint64).reshape((2, 2))
    layer = Labels(label_array)
    mapped = layer._random_colormap.map(layer.data)

    assert len(np.unique(mapped.reshape((-1, 4)), axis=0)) == 4


if parse_version(version('zarr')) > parse_version('3.0.0a0'):
    driver = [(2, 'zarr'), (3, 'zarr3')]
else:
    driver = [(2, 'zarr')]


@pytest.mark.parametrize(('zarr_version', 'zarr_driver'), driver)
def test_fill_tensorstore(tmp_path, zarr_version, zarr_driver):
    ts = pytest.importorskip('tensorstore')

    labels = np.zeros((5, 7, 8, 9), dtype=int)
    labels[1, 2:4, 4:6, 4:6] = 1
    labels[1, 3:5, 5:7, 6:8] = 2
    labels[2, 3:5, 5:7, 6:8] = 3

    file_path = str(tmp_path / 'labels.zarr')

    labels_temp = zarr.open(
        store=file_path,
        mode='w',
        shape=labels.shape,
        dtype=np.uint32,
        chunks=(1, 1, 8, 9),
        zarr_version=zarr_version,
    )
    labels_temp[:] = labels
    labels_ts_spec = {
        'driver': zarr_driver,
        'kvstore': {'driver': 'file', 'path': file_path},
        'path': '',
    }
    data = ts.open(labels_ts_spec, create=False, open=True).result()
    layer = Labels(data)
    layer.n_edit_dimensions = 3
    layer.fill((1, 4, 6, 7), 4)
    modified_labels = np.where(labels == 2, 4, labels)
    np.testing.assert_array_equal(modified_labels, np.asarray(data))


def test_fill_with_xarray():
    """See https://github.com/napari/napari/issues/2374"""
    data = xr.DataArray(np.zeros((5, 4, 4), dtype=int))
    layer = Labels(data)

    layer.fill((0, 2, 2), 1)

    np.testing.assert_array_equal(layer.data[0, :, :], np.ones((4, 4)))
    np.testing.assert_array_equal(layer.data[1:, :, :], np.zeros((4, 4, 4)))
    # In the associated issue, using xarray.DataArray caused memory allocation
    # problems due to different read indexing rules, so check that the data
    # saved for undo has the expected vectorized shape and values.
    undo_data = layer._undo_history[0][0][1]
    np.testing.assert_array_equal(undo_data, np.zeros((16,)))


@pytest.mark.parametrize(
    'scale', list(itertools.product([-2, 2], [-0.5, 0.5], [-0.5, 0.5]))
)
def test_paint_3d_negative_scale(scale):
    labels = np.zeros((3, 5, 11, 11), dtype=int)
    labels_layer = Labels(
        labels, scale=(1, *scale), translate=(-200, 100, 100)
    )
    labels_layer.n_edit_dimensions = 3
    labels_layer.brush_size = 8
    labels_layer.paint((1, 2, 5, 5), 1)
    np.testing.assert_array_equal(
        np.sum(labels_layer.data, axis=(1, 2, 3)), [0, 95, 0]
    )


def test_rendering_init():
    shape = (6, 10, 15)
    np.random.seed(0)
    data = np.random.randint(20, size=shape)
    layer = Labels(data, rendering='iso_categorical')

    assert layer.rendering == LabelsRendering.ISO_CATEGORICAL.value


def test_3d_video_and_3d_scale_translate_then_scale_translate_padded():
    # See the GitHub issue for more details:
    # https://github.com/napari/napari/issues/2967
    data = np.zeros((3, 5, 11, 11), dtype=int)
    labels = Labels(data, scale=(2, 1, 1), translate=(5, 5, 5))

    np.testing.assert_array_equal(labels.scale, (1, 2, 1, 1))
    np.testing.assert_array_equal(labels.translate, (0, 5, 5, 5))


@dataclass
class MouseEvent:
    # mock mouse event class
    pos: list[int]
    position: list[int]
    dims_point: list[int]
    dims_displayed: list[int]
    view_direction: list[int]


def test_get_value_ray_3d():
    """Test using _get_value_ray to interrogate labels in 3D"""
    # make a mock mouse event
    mouse_event = MouseEvent(
        pos=[25, 25],
        position=[10, 5, 5],
        dims_point=[1, 0, 0, 0],
        dims_displayed=[1, 2, 3],
        view_direction=[1, 0, 0],
    )
    data = np.zeros((5, 20, 20, 20), dtype=int)
    data[1, 0:10, 0:10, 0:10] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(5, 5, 5))

    # set the dims to the slice with labels
    labels._slice_dims(Dims(ndim=4, ndisplay=3, point=(1, 0, 0, 0)))

    value = labels._get_value_ray(
        start_point=np.array([1, 0, 5, 5]),
        end_point=np.array([1, 20, 5, 5]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value == 1

    # check with a ray that only goes through background
    value = labels._get_value_ray(
        start_point=np.array([1, 0, 15, 15]),
        end_point=np.array([1, 20, 15, 15]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value is None

    # set the dims to a slice without labels
    labels._slice_dims(Dims(ndim=4, ndisplay=3, point=(0, 0, 0, 0)))

    value = labels._get_value_ray(
        start_point=np.array([0, 0, 5, 5]),
        end_point=np.array([0, 20, 5, 5]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value is None


def test_get_value_ray_3d_rolled():
    """Test using _get_value_ray to interrogate labels in 3D
    with the dimensions rolled.
    """
    # make a mock mouse event
    mouse_event = MouseEvent(
        pos=[25, 25],
        position=[10, 5, 5, 1],
        dims_point=[0, 0, 0, 1],
        dims_displayed=[0, 1, 2],
        view_direction=[1, 0, 0, 0],
    )
    data = np.zeros((20, 20, 20, 5), dtype=int)
    data[0:10, 0:10, 0:10, 1] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(5, 5, 5, 0))

    # set the dims to the slice with labels
    labels._slice_dims(
        Dims(ndim=4, ndisplay=3, order=(3, 0, 1, 2), point=(0, 0, 0, 1))
    )
    labels.set_view_slice()

    value = labels._get_value_ray(
        start_point=np.array([0, 5, 5, 1]),
        end_point=np.array([20, 5, 5, 1]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value == 1


def test_get_value_ray_3d_transposed():
    """Test using _get_value_ray to interrogate labels in 3D
    with the dimensions transposed.
    """
    # make a mock mouse event
    mouse_event = MouseEvent(
        pos=[25, 25],
        position=[10, 5, 5, 1],
        dims_point=[0, 0, 0, 1],
        dims_displayed=[1, 3, 2],
        view_direction=[1, 0, 0, 0],
    )
    data = np.zeros((5, 20, 20, 20), dtype=int)
    data[1, 0:10, 0:10, 0:10] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(0, 5, 5, 5))

    # set the dims to the slice with labels
    labels._slice_dims(
        Dims(ndim=4, ndisplay=3, order=(0, 1, 3, 2), point=(1, 0, 0, 0))
    )
    labels.set_view_slice()

    value = labels._get_value_ray(
        start_point=np.array([1, 0, 5, 5]),
        end_point=np.array([1, 20, 5, 5]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value == 1


def test_get_value_ray_2d():
    """_get_value_ray currently only returns None in 2D
    (i.e., it shouldn't be used for 2D).
    """
    # make a mock mouse event
    mouse_event = MouseEvent(
        pos=[25, 25],
        position=[5, 5],
        dims_point=[1, 10, 0, 0],
        dims_displayed=[2, 3],
        view_direction=[1, 0, 0],
    )
    data = np.zeros((5, 20, 20, 20), dtype=int)
    data[1, 0:10, 0:10, 0:10] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(5, 5, 5))

    # set the dims to the slice with labels, but 2D
    labels._slice_dims(Dims(ndim=4, ndisplay=2, point=(1, 10, 0, 0)))

    value = labels._get_value_ray(
        start_point=np.empty([]),
        end_point=np.empty([]),
        dims_displayed=mouse_event.dims_displayed,
    )
    assert value is None


def test_cursor_ray_3d():
    # make a mock mouse event
    mouse_event_1 = MouseEvent(
        pos=[25, 25],
        position=[1, 10, 27, 10],
        dims_point=[1, 0, 0, 0],
        dims_displayed=[1, 2, 3],
        view_direction=[0, 1, 0, 0],
    )
    data = np.zeros((5, 20, 20, 20), dtype=int)
    data[1, 0:10, 0:10, 0:10] = 1
    labels = Labels(data, scale=(1, 1, 2, 1), translate=(5, 5, 5))

    # set the slice to one with data and the view to 3D
    labels._slice_dims(Dims(ndim=4, ndisplay=3, point=(1, 0, 0, 0)))

    # axis 0 : [0, 20], bounding box extents along view axis, [1, 0, 0]
    # click is transformed: (value - translation) / scale
    # axis 1: click at 27 in world coords -> (27 - 5) / 2 = 11
    # axis 2: click at 10 in world coords -> (10 - 5) / 1 = 5
    start_point, end_point = labels.get_ray_intersections(
        mouse_event_1.position,
        mouse_event_1.view_direction,
        mouse_event_1.dims_displayed,
    )
    np.testing.assert_allclose(start_point, [1, 0, 11, 5])
    np.testing.assert_allclose(end_point, [1, 20, 11, 5])

    # click in the background
    mouse_event_2 = MouseEvent(
        pos=[25, 25],
        position=[1, 10, 65, 10],
        dims_point=[1, 0, 0, 0],
        dims_displayed=[1, 2, 3],
        view_direction=[0, 1, 0, 0],
    )
    start_point, end_point = labels.get_ray_intersections(
        mouse_event_2.position,
        mouse_event_2.view_direction,
        mouse_event_2.dims_displayed,
    )
    assert start_point is None
    assert end_point is None

    # click in a slice with no labels
    mouse_event_3 = MouseEvent(
        pos=[25, 25],
        position=[0, 10, 27, 10],
        dims_point=[0, 0, 0, 0],
        dims_displayed=[1, 2, 3],
        view_direction=[0, 1, 0, 0],
    )
    labels._slice_dims(Dims(ndim=4, ndisplay=3))
    start_point, end_point = labels.get_ray_intersections(
        mouse_event_3.position,
        mouse_event_3.view_direction,
        mouse_event_3.dims_displayed,
    )
    np.testing.assert_allclose(start_point, [0, 0, 11, 5])
    np.testing.assert_allclose(end_point, [0, 20, 11, 5])


def test_cursor_ray_3d_rolled():
    """Test that the cursor works when the displayed
    viewer axes have been rolled
    """
    # make a mock mouse event
    mouse_event_1 = MouseEvent(
        pos=[25, 25],
        position=[10, 27, 10, 1],
        dims_point=[0, 0, 0, 1],
        dims_displayed=[0, 1, 2],
        view_direction=[1, 0, 0, 0],
    )
    data = np.zeros((20, 20, 20, 5), dtype=int)
    data[0:10, 0:10, 0:10, 1] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(5, 5, 5, 0))

    # set the slice to one with data and the view to 3D
    labels._slice_dims(Dims(ndim=4, ndisplay=3, point=(0, 0, 0, 1)))

    start_point, end_point = labels.get_ray_intersections(
        mouse_event_1.position,
        mouse_event_1.view_direction,
        mouse_event_1.dims_displayed,
    )
    np.testing.assert_allclose(start_point, [0, 11, 5, 1])
    np.testing.assert_allclose(end_point, [20, 11, 5, 1])


def test_cursor_ray_3d_transposed():
    """Test that the cursor works when the displayed
    viewer axes have been transposed
    """
    # make a mock mouse event
    mouse_event_1 = MouseEvent(
        pos=[25, 25],
        position=[10, 27, 10, 1],
        dims_point=[0, 0, 0, 1],
        dims_displayed=[0, 2, 1],
        view_direction=[1, 0, 0, 0],
    )
    data = np.zeros((20, 20, 20, 5), dtype=int)
    data[0:10, 0:10, 0:10, 1] = 1
    labels = Labels(data, scale=(1, 2, 1, 1), translate=(5, 5, 5, 0))

    # set the slice to one with data and the view to 3D
    labels._slice_dims(Dims(ndim=4, ndisplay=3, point=(0, 0, 0, 1)))

    start_point, end_point = labels.get_ray_intersections(
        mouse_event_1.position,
        mouse_event_1.view_direction,
        mouse_event_1.dims_displayed,
    )
    np.testing.assert_allclose(start_point, [0, 11, 5, 1])
    np.testing.assert_allclose(end_point, [20, 11, 5, 1])


def test_labels_state_update():
    """Test that a labels layer can be updated from the output of its
    _get_state() method
    """
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)
    state = layer._get_state()
    for k, v in state.items():
        setattr(layer, k, v)


def test_is_default_color():
    """Test labels layer default color for None and background

    Previously, setting color to just default values would
    change color mode to DIRECT and display a black layer.
    This test ensures `is_default_color` is
    correctly checking against layer defaults, and `color_mode`
    is only changed when appropriate.

    See
        - https://github.com/napari/napari/issues/2479
        - https://github.com/napari/napari/issues/2953
    """
    data = np.random.randint(20, size=(10, 15))
    layer = Labels(data)

    # layer gets instantiated with defaults
    current_color = layer._direct_colormap.color_dict
    assert layer._is_default_colors(current_color)

    # setting color to default colors doesn't update color mode
    layer.colormap = DirectLabelColormap(color_dict=current_color)
    assert isinstance(layer.colormap, CyclicLabelColormap)

    # new colors are not default
    new_color = {0: 'white', 1: 'red', 3: 'green', None: 'blue'}
    assert not layer._is_default_colors(new_color)
    # setting the color with non-default colors updates color mode
    layer.colormap = DirectLabelColormap(color_dict=new_color)
    assert isinstance(layer.colormap, DirectLabelColormap)


def test_large_labels_direct_color():
    """Make sure direct color works with large label ranges"""
    pytest.importorskip('numba')
    data = np.array([[0, 1], [2**16, 2**20]], dtype=np.uint32)
    colors = {1: 'white', 2**16: 'green', 2**20: 'magenta'}
    layer = Labels(
        data,
        colormap=DirectLabelColormap(
            color_dict=defaultdict(lambda: 'black', colors)
        ),
    )
    np.testing.assert_allclose(layer.get_color(2**20), [1.0, 0.0, 1.0, 1.0])


def test_invalidate_cache_when_change_color_mode(
    direct_colormap, random_colormap
):
    """Checks if the cache is invalidated when color mode is changed."""
    data = np.zeros((4, 10), dtype=np.int32)
    data[1, :] = np.arange(0, 10)

    layer = Labels(data)
    layer.selected_label = 0
    gt_auto = layer._raw_to_displayed(layer._slice.image.raw)
    assert gt_auto.dtype == np.uint8

    layer.colormap = direct_colormap
    layer._cached_labels = None
    assert layer._raw_to_displayed(layer._slice.image.raw).dtype == np.uint8

    layer.colormap = random_colormap
    # If the cache is not invalidated, it returns colors for
    # the direct color mode instead of the color for the auto mode
    assert np.allclose(
        layer._raw_to_displayed(layer._slice.image.raw), gt_auto
    )


def test_color_mapping_when_color_is_changed():
    """Checks if the color mapping is computed correctly when the color palette is changed."""

    data = np.zeros((4, 5), dtype=np.int32)
    data[1, :] = np.arange(0, 5)
    layer = Labels(
        data,
        colormap=DirectLabelColormap(
            color_dict={1: 'green', 2: 'red', 3: 'white', None: 'black'}
        ),
    )
    gt_direct_3colors = layer._raw_to_displayed(layer._slice.image.raw)

    layer = Labels(
        data,
        colormap=DirectLabelColormap(
            color_dict={1: 'green', 2: 'red', None: 'black'}
        ),
    )
    assert layer._raw_to_displayed(layer._slice.image.raw).dtype == np.uint8
    layer.colormap = DirectLabelColormap(
        color_dict={1: 'green', 2: 'red', 3: 'white', None: 'black'}
    )

    assert np.allclose(
        layer._raw_to_displayed(layer._slice.image.raw), gt_direct_3colors
    )


def test_color_mapping_with_show_selected_label():
    """Checks if the color mapping is computed correctly when show_selected_label is activated."""

    data = np.arange(5, dtype=np.int32)[:, np.newaxis].repeat(5, axis=1)
    layer = Labels(data)
    mapped_colors_all = layer.colormap.map(data)

    layer.show_selected_label = True

    for selected_label in range(5):
        layer.selected_label = selected_label
        label_mask = data == selected_label
        mapped_colors = layer.colormap.map(data)

        npt.assert_allclose(
            mapped_colors[label_mask], mapped_colors_all[label_mask]
        )
        npt.assert_allclose(mapped_colors[np.logical_not(label_mask)], 0)

    layer.show_selected_label = False
    assert np.allclose(layer.colormap.map(data), mapped_colors_all)


def test_color_mapping_when_seed_is_changed():
    """Checks if the color mapping is updated when the color palette seed is changed."""
    np.random.seed(0)
    layer = Labels(np.random.randint(50, size=(10, 10)))
    mapped_colors1 = layer.colormap.map(
        layer._to_vispy_texture_dtype(layer._slice.image.raw)
    )

    layer.new_colormap()
    mapped_colors2 = layer.colormap.map(
        layer._to_vispy_texture_dtype(layer._slice.image.raw)
    )

    assert not np.allclose(mapped_colors1, mapped_colors2)


@pytest.mark.parametrize('num_colors', [49, 50, 254, 255, 60000, 65534])
def test_color_shuffling_above_num_colors(num_colors):
    r"""Check that the color shuffle does not result in the same collisions.

    See https://github.com/napari/napari/issues/6448.

    Note that we don't support more than 2\ :sup:`16` colors, and behavior
    with more colors is undefined, so we don't test it here.
    """
    labels = np.arange(1, 1 + 2 * (num_colors - 1)).reshape((2, -1))
    layer = Labels(labels, colormap=label_colormap(num_colors - 1))
    colors0 = layer.colormap.map(labels)
    assert np.all(colors0[0] == colors0[1])
    layer.new_colormap()
    colors1 = layer.colormap.map(labels)
    assert not np.all(colors1[0] == colors1[1])


def test_negative_label():
    """Test negative label values are supported."""
    data = np.random.randint(low=-1, high=20, size=(10, 10))
    original_data = np.copy(data)
    layer = Labels(data)
    layer.selected_label = -1
    layer.brush_size = 3
    layer.paint((5, 5), -1)
    assert np.count_nonzero(layer.data == -1) > np.count_nonzero(
        original_data == -1
    )


def test_negative_label_slicing():
    """Test negative label color doesn't change during slicing."""
    data = np.array([[[0, 1], [-1, -1]], [[100, 100], [-1, -2]]])
    layer = Labels(data)
    assert tuple(layer.get_color(1)) != tuple(layer.get_color(-1))
    layer._slice_dims(Dims(ndim=3, point=(1, 0, 0)))
    assert tuple(layer.get_color(-1)) != tuple(layer.get_color(100))
    assert tuple(layer.get_color(-2)) != tuple(layer.get_color(100))


def test_negative_label_doesnt_flicker():
    data = np.array(
        [
            [[0, 5], [0, 5]],
            [[-1, 5], [-1, 5]],
            [[-1, 6], [-1, 6]],
        ]
    )
    layer = Labels(data)
    layer._slice_dims(Dims(ndim=3, point=(1, 0, 0)))
    # This used to fail when negative values were used to index into _all_vals.
    assert tuple(layer.get_color(-1)) != tuple(layer.get_color(5))
    minus_one_color_original = tuple(layer.get_color(-1))
    layer.dims_point = (2, 0, 0)
    layer._set_view_slice()

    assert tuple(layer.get_color(-1)) == minus_one_color_original


def test_get_status_with_custom_index():
    """See https://github.com/napari/napari/issues/3811"""
    data = np.zeros((10, 10), dtype=np.uint8)
    data[2:5, 2:-2] = 1
    data[5:-2, 2:-2] = 2
    layer = Labels(data)
    df = pd.DataFrame(
        {'text1': [1, 3], 'text2': [7, -2], 'index': [1, 2]}, index=[1, 2]
    )
    layer.properties = df
    assert (
        layer.get_status((0, 0))['coordinates'] == ' [0 0]: 0; [No Properties]'
    )
    assert (
        layer.get_status((3, 3))['coordinates']
        == ' [3 3]: 1; text1: 1, text2: 7'
    )
    assert (
        layer.get_status((6, 6))['coordinates']
        == ' [6 6]: 2; text1: 3, text2: -2'
    )


def test_labels_features_event():
    event_emitted = False

    def on_event():
        nonlocal event_emitted
        event_emitted = True

    layer = Labels(np.zeros((4, 5), dtype=np.uint8))
    layer.events.features.connect(on_event)

    layer.features = {'some_feature': []}

    assert event_emitted


def test_copy():
    l1 = Labels(np.zeros((2, 4, 5), dtype=np.uint8))
    l2 = copy.copy(l1)
    l3 = Labels.create(*l1.as_layer_data_tuple())
    assert l1.data is not l2.data
    assert l1.data is l3.data


@pytest.mark.parametrize(
    ('colormap', 'expected'),
    [
        (label_colormap(49, 0.5), [0, 1]),
        (
            DirectLabelColormap(
                color_dict={
                    0: np.array([0, 0, 0, 0]),
                    1: np.array([1, 0, 0, 1]),
                    None: np.array([1, 1, 0, 1]),
                }
            ),
            [1, 2],
        ),
    ],
    ids=['auto', 'direct'],
)
def test_draw(colormap, expected):
    labels = Labels(np.zeros((30, 30), dtype=np.uint32))
    labels.mode = 'paint'
    labels.colormap = colormap
    labels.selected_label = 1
    npt.assert_array_equal(np.unique(labels._slice.image.raw), [0])
    npt.assert_array_equal(np.unique(labels._slice.image.view), expected[:1])
    labels._draw(1, (15, 15), (15, 15))
    npt.assert_array_equal(np.unique(labels._slice.image.raw), [0, 1])
    npt.assert_array_equal(np.unique(labels._slice.image.view), expected)


class TestLabels:
    @staticmethod
    def get_objects():
        return [(Labels(np.zeros((10, 10), dtype=np.uint8)))]

    def test_events_defined(self, event_define_check, obj):
        event_define_check(
            obj,
            {'seed', 'num_colors', 'color', 'seed_rng'},
        )


def test_docstring():
    validate_all_params_in_docstring(Labels)
    validate_kwargs_sorted(Labels)


def test_new_colormap_int8():
    """Check that int8 labels colors can be shuffled without overflow.

    See https://github.com/napari/napari/issues/7277.
    """
    data = np.arange(-128, 128, dtype=np.int8).reshape((16, 16))
    layer = Labels(data)
    layer.new_colormap(seed=0)


@pytest.mark.parametrize('visible', [True, False])
@pytest.mark.parametrize('dtype', [np.uint8, np.int8, np.uint32, np.int64])
def test_view_dtype(visible, dtype):
    layer = Labels(np.arange(25, dtype=dtype).reshape(5, 5), visible=visible)
    assert layer._slice.image.view.dtype == np.uint8


@pytest.mark.parametrize('visible', [True, False])
@pytest.mark.parametrize('dtype', [np.uint16, np.int16])
def test_view_dtype_int16(visible, dtype):
    layer = Labels(np.arange(25, dtype=dtype).reshape(5, 5), visible=visible)
    assert layer._slice.image.view.dtype == np.uint16
