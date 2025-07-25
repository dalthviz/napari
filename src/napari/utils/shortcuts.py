from app_model.types import KeyBinding, KeyCode, KeyMod

_default_shortcuts = {
    # viewer
    'napari:toggle_console_visibility': [
        KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyC
    ],
    'napari:toggle_ndisplay': [KeyMod.CtrlCmd | KeyCode.KeyY],
    'napari:toggle_theme': [KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyT],
    'napari:reset_view': [KeyMod.CtrlCmd | KeyCode.KeyR],
    'napari:delete_selected_layers': [
        KeyMod.CtrlCmd | KeyCode.Delete,
        KeyMod.CtrlCmd | KeyCode.Backspace,
    ],
    'napari:show_shortcuts': [KeyMod.CtrlCmd | KeyMod.Alt | KeyCode.Slash],
    'napari:increment_dims_left': [KeyCode.LeftArrow],
    'napari:increment_dims_right': [KeyCode.RightArrow],
    'napari:focus_axes_up': [KeyMod.Alt | KeyCode.UpArrow],
    'napari:focus_axes_down': [KeyMod.Alt | KeyCode.DownArrow],
    'napari:roll_axes': [KeyMod.CtrlCmd | KeyCode.KeyE],
    'napari:transpose_axes': [KeyMod.CtrlCmd | KeyCode.KeyT],
    'napari:rotate_layers': [KeyMod.CtrlCmd | KeyMod.Alt | KeyCode.KeyT],
    'napari:toggle_grid': [KeyMod.CtrlCmd | KeyCode.KeyG],
    'napari:toggle_selected_visibility': [KeyCode.KeyV],
    'napari:toggle_unselected_visibility': [KeyMod.Shift | KeyCode.KeyV],
    'napari:select_layer_above': [KeyMod.CtrlCmd | KeyCode.UpArrow],
    'napari:select_layer_below': [KeyMod.CtrlCmd | KeyCode.DownArrow],
    'napari:show_only_layer_above': [
        KeyMod.Shift | KeyMod.Alt | KeyCode.UpArrow
    ],
    'napari:show_only_layer_below': [
        KeyMod.Shift | KeyMod.Alt | KeyCode.DownArrow
    ],
    'napari:hold_for_pan_zoom': [KeyCode.Space],
    # labels
    'napari:activate_labels_erase_mode': [KeyCode.Digit1, KeyCode.KeyE],
    'napari:activate_labels_paint_mode': [KeyCode.Digit2, KeyCode.KeyP],
    'napari:activate_labels_polygon_mode': [KeyCode.Digit3],
    'napari:activate_labels_fill_mode': [KeyCode.Digit4, KeyCode.KeyF],
    'napari:activate_labels_picker_mode': [KeyCode.Digit5, KeyCode.KeyL],
    'napari:activate_labels_pan_zoom_mode': [KeyCode.Digit6, KeyCode.KeyZ],
    'napari:activate_labels_transform_mode': [KeyCode.Digit7],
    'napari:new_label': [KeyCode.KeyM],
    'napari:swap_selected_and_background_labels': [KeyCode.KeyX],
    'napari:decrease_label_id': [KeyCode.Minus],
    'napari:increase_label_id': [KeyCode.Equal],
    'napari:decrease_brush_size': [KeyCode.BracketLeft],
    'napari:increase_brush_size': [KeyCode.BracketRight],
    'napari:toggle_preserve_labels': [KeyCode.KeyB],
    'napari:reset_polygon': [KeyCode.Escape],
    'napari:complete_polygon': [KeyCode.Enter],
    # points
    'napari:activate_points_add_mode': [KeyCode.Digit2, KeyCode.KeyP],
    'napari:activate_points_select_mode': [KeyCode.Digit3, KeyCode.KeyS],
    'napari:activate_points_pan_zoom_mode': [KeyCode.Digit4, KeyCode.KeyZ],
    'napari:activate_points_transform_mode': [KeyCode.Digit5],
    'napari:select_all_in_slice': [
        KeyCode.KeyA,
        KeyMod.CtrlCmd | KeyCode.KeyA,
    ],
    'napari:select_all_data': [KeyMod.Shift | KeyCode.KeyA],
    'napari:delete_selected_points': [
        KeyCode.Digit1,
        KeyCode.Delete,
        KeyCode.Backspace,
    ],
    # shapes
    'napari:activate_add_rectangle_mode': [KeyCode.KeyR],
    'napari:activate_add_ellipse_mode': [KeyCode.KeyE],
    'napari:activate_add_line_mode': [KeyCode.KeyL],
    'napari:activate_add_path_mode': [KeyCode.KeyT],
    'napari:activate_add_polyline_mode': [KeyMod.Shift | KeyCode.KeyL],
    'napari:activate_add_polygon_mode': [KeyCode.KeyP],
    'napari:activate_add_polygon_lasso_mode': [KeyMod.Shift | KeyCode.KeyP],
    'napari:activate_direct_mode': [KeyCode.Digit4, KeyCode.KeyD],
    'napari:activate_select_mode': [KeyCode.Digit5, KeyCode.KeyS],
    'napari:activate_shapes_pan_zoom_mode': [KeyCode.Digit6, KeyCode.KeyZ],
    'napari:activate_shapes_transform_mode': [KeyCode.Digit7],
    'napari:activate_vertex_insert_mode': [KeyCode.Digit2, KeyCode.KeyI],
    'napari:activate_vertex_remove_mode': [KeyCode.Digit1, KeyCode.KeyX],
    'napari:copy_selected_shapes': [KeyMod.CtrlCmd | KeyCode.KeyC],
    'napari:paste_shape': [KeyMod.CtrlCmd | KeyCode.KeyV],
    'napari:move_shapes_selection_to_front': [KeyCode.KeyF],
    'napari:move_shapes_selection_to_back': [KeyCode.KeyB],
    'napari:select_all_shapes': [
        KeyCode.KeyA,
        KeyMod.CtrlCmd | KeyCode.KeyA,
    ],
    'napari:delete_selected_shapes': [
        KeyCode.Digit3,
        KeyCode.Delete,
        KeyCode.Backspace,
    ],
    'napari:finish_drawing_shape': [KeyCode.Enter, KeyCode.Escape],
    # image
    'napari:orient_plane_normal_along_x': [KeyCode.KeyX],
    'napari:orient_plane_normal_along_y': [KeyCode.KeyY],
    'napari:orient_plane_normal_along_z': [KeyCode.KeyZ],
    'napari:orient_plane_normal_along_view_direction': [KeyCode.KeyO],
    'napari:activate_image_pan_zoom_mode': [KeyCode.Digit1],
    'napari:activate_image_transform_mode': [KeyCode.Digit2],
    # vectors
    'napari:activate_vectors_pan_zoom_mode': [KeyCode.Digit1],
    'napari:activate_vectors_transform_mode': [KeyCode.Digit2],
    # tracks
    'napari:activate_tracks_pan_zoom_mode': [KeyCode.Digit1],
    'napari:activate_tracks_transform_mode': [KeyCode.Digit2],
    # surface
    'napari:activate_surface_pan_zoom_mode': [KeyCode.Digit1],
    'napari:activate_surface_transform_mode': [KeyCode.Digit2],
}

default_shortcuts: dict[str, list[KeyBinding]] = {
    name: [KeyBinding.from_int(kb) for kb in value]
    for name, value in _default_shortcuts.items()
}
