MAYA FACIAL FLIPBOOK TEST

Files:
 maya_flipbook.py
 textures/blink_atlas.png (8 horizontal cells, transparent RGBA)
 textures/smile_atlas.png (8 horizontal cells, transparent RGBA)

In Maya Script Editor, Python tab:
 import sys
 sys.path.insert(0, r'/YOUR/PATH/maya_flipbook_test')
 import maya_flipbook
 maya_flipbook.build_test_scene(save_path=r'/YOUR/PATH/maya_flipbook_test/flipbook_test.ma')

Select face components for blink and store them:
 blink_faces = cmds.ls(sl=True, fl=True)
Select face components for smile and store them:
 smile_faces = cmds.ls(sl=True, fl=True)
 maya_flipbook.setup_from_two_selections(blink_faces, smile_faces, r'/YOUR/PATH/maya_flipbook_test/textures')

Each feature gets its own UV set copied from the mesh's current UV set.
IMPORTANT: For production geometry, selected faces must already have UVs occupying
0..1 in their own UV set. Lay out each feature's UVs in 0..1 before setup.
The atlas is a SINGLE ROW of equally-sized cells. Controller 0..1 is quantized
by stepped animCurveUU keys, so there is no in-between image sliding.

The generated .ma file is saved by running Maya itself (not a simulated scene).
View in textured viewport mode (key 6), ideally with transparency enabled.
