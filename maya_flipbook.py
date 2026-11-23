"""Maya 2023+ native DG facial flipbook test. Run inside Maya's Python tab."""
import os
import maya.cmds as cmds

FRAME_COUNT = 8


def _mesh_from_selection(components):
    """Return the mesh shape and face components for a polygon selection."""
    faces = cmds.filterExpand(components, selectionMask=34, expand=True) or []
    if not faces:
        raise ValueError('Select polygon faces, not only a mesh transform.')
    shapes = set()
    for face in faces:
        transform = face.split('.')[0]
        shape = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True, type='mesh') or []
        if not shape:
            raise ValueError('Selection contains no polygon mesh: ' + face)
        shapes.add(shape[0])
    if len(shapes) != 1:
        raise ValueError('Each feature must be on one mesh. Call setup_feature separately for other meshes.')
    return next(iter(shapes)), faces


def setup_feature(faces, feature, atlas_path, controller=None, frame_count=FRAME_COUNT):
    """Assign a sprite atlas to faces, with a private UV set and stepped controller.

    Args:
        faces: Selected polygon face components from one mesh, with UVs in 0..1.
        feature: Unique feature name, e.g. 'blink' or 'smile'.
        atlas_path: Path to a single-row, equally spaced PNG sprite atlas.
        controller: Optional existing Maya transform. Created if omitted.
        frame_count: Number of horizontal sprite cells.
    Returns:
        dict: Controller, UV set, shader, file, placement and animation nodes.
    Example:
        setup_feature(cmds.ls(sl=True, fl=True), 'blink', '/tmp/blink_atlas.png')
    """
    if not os.path.isfile(atlas_path):
        raise IOError('Atlas not found: ' + atlas_path)
    if frame_count < 2:
        raise ValueError('frame_count must be at least 2')
    mesh, faces = _mesh_from_selection(faces)
    uv_set = feature + 'UV'
    existing = cmds.polyUVSet(mesh, query=True, allUVSets=True) or []
    source_uv = cmds.polyUVSet(mesh, query=True, currentUVSet=True)[0]
    if uv_set not in existing:
        cmds.polyUVSet(mesh, copy=True, uvSet=source_uv, newUVSet=uv_set)
    # Keep the copied 0..1 UVs unchanged; the placement node selects the tile.
    if controller is None:
        controller = cmds.circle(name='face_CTRL', normal=(0, 0, 1), radius=1.5, ch=False)[0] if not cmds.objExists('face_CTRL') else 'face_CTRL'
    attr = feature
    if not cmds.attributeQuery(attr, node=controller, exists=True):
        cmds.addAttr(controller, ln=attr, at='double', min=0, max=1, dv=0, keyable=True)
    shader = cmds.shadingNode('lambert', asShader=True, name=feature+'_MAT')
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=feature+'_SG')
    cmds.connectAttr(shader+'.outColor', sg+'.surfaceShader', force=True)
    file_node = cmds.shadingNode('file', asTexture=True, isColorManaged=True, name=feature+'_FILE')
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=feature+'_PLACE2D')
    cmds.setAttr(file_node+'.fileTextureName', os.path.abspath(atlas_path), type='string')
    cmds.setAttr(file_node+'.filterType', 0)  # No filtering across sprite boundaries
    cmds.setAttr(place+'.wrapU', 0)
    cmds.setAttr(place+'.wrapV', 0)
    cmds.setAttr(place+'.repeatU', 1.0/frame_count)
    cmds.setAttr(place+'.repeatV', 1)
    for src, dst in [('outUV','uvCoord'),('outUvFilterSize','uvFilterSize')]:
        cmds.connectAttr(place+'.'+src, file_node+'.'+dst, force=True)
    cmds.connectAttr(file_node+'.outColor', shader+'.color', force=True)
    cmds.connectAttr(file_node+'.outTransparency', shader+'.transparency', force=True)
    cmds.setAttr(shader+'.ambientColor', 1, 1, 1, type='double3')
    cmds.setAttr(shader+'.diffuse', 0)
    cmds.sets(faces, edit=True, forceElement=sg)
    # UV links are per texture and mesh, allowing both features on one mesh.
    cmds.uvLink(make=True, texture=file_node, uvSet=mesh+'.uvSet['+str((cmds.polyUVSet(mesh, q=True, allUVSets=True) or []).index(uv_set))+'].uvSetName')
    # animCurveUU maps normalized controller input to discrete tile index.
    curve = cmds.createNode('animCurveUU', name=feature+'_FRAME_STEPPED')
    for i in range(frame_count):
        cmds.setKeyframe(curve, float=float(i)/(frame_count-1), value=float(i)/frame_count)
    cmds.keyTangent(curve, edit=True, inTangentType='linear', outTangentType='step')
    cmds.setInfinity(curve, pri='constant', poi='constant')
    cmds.connectAttr(controller+'.'+attr, curve+'.input', force=True)
    cmds.connectAttr(curve+'.output', place+'.offsetU', force=True)
    return dict(controller=controller, uvSet=uv_set, shader=shader,
                shadingGroup=sg, file=file_node, placement=place, curve=curve)


def setup_from_two_selections(blink_faces, smile_faces, texture_directory, controller=None):
    """Create blink and smile networks from two independent face selections.

    Args:
        blink_faces: First polygon face selection.
        smile_faces: Second polygon face selection.
        texture_directory: Directory containing blink_atlas.png and smile_atlas.png.
        controller: Optional existing transform.
    Returns:
        dict: The two created feature networks.
    Example:
        setup_from_two_selections(blink_faces, smile_faces, '/tmp/textures')
    """
    controller = controller or (cmds.circle(name='face_CTRL', normal=(0,0,1), radius=1.5, ch=False)[0]
                                if not cmds.objExists('face_CTRL') else 'face_CTRL')
    return {
        'blink': setup_feature(blink_faces, 'blink', os.path.join(texture_directory, 'blink_atlas.png'), controller),
        'smile': setup_feature(smile_faces, 'smile', os.path.join(texture_directory, 'smile_atlas.png'), controller),
    }


def build_test_scene(texture_directory=None, save_path=None):
    """Create two face planes, a controller, texture networks and test keys.

    Args:
        texture_directory: Folder containing the two PNG sprite sheets.
        save_path: Optional destination .ma scene path.
    Returns:
        dict: Created feature networks.
    Example:
        build_test_scene('/path/to/textures', '/path/to/flipbook_test.ma')
    """
    if texture_directory is None:
        texture_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'textures')
    cmds.file(new=True, force=True)
    blink_mesh = cmds.polyPlane(name='blink_GEO', width=2.5, height=1.1, sx=1, sy=1, axis=(0,0,1), ch=False)[0]
    smile_mesh = cmds.polyPlane(name='smile_GEO', width=2.5, height=1.1, sx=1, sy=1, axis=(0,0,1), ch=False)[0]
    cmds.move(0, 0.85, 0, blink_mesh)
    cmds.move(0, -0.85, 0, smile_mesh)
    controller = cmds.circle(name='face_CTRL', normal=(0,0,1), radius=0.45, ch=False)[0]
    cmds.move(2.4, 0, 0, controller)
    networks = setup_from_two_selections([blink_mesh+'.f[0]'], [smile_mesh+'.f[0]'], texture_directory, controller)
    for frame, blink, smile in [(1,0,0),(5,1,0),(9,0,0),(13,0,1),(17,0,0),(21,1,1),(25,0,0)]:
        for name,value in [('blink',blink),('smile',smile)]:
            cmds.setKeyframe(controller, attribute=name, time=frame, value=value)
    cmds.playbackOptions(minTime=1, maxTime=25)
    cmds.currentTime(1)
    cmds.select(controller, replace=True)
    if save_path:
        cmds.file(rename=os.path.abspath(save_path))
        cmds.file(save=True, type='mayaAscii', force=True)
    return networks
