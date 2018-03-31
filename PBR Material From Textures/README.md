# PBR Material From Textures
This is an add-on for Blender which automates the creation of PBR materials from external textures by using their extension (Alb, AO, Nor, etc). It creates a full PBR node tree in a node group, which allows to tweak the settings from the Surface tab of the Material panel.

Tested with textures from the following sites (unexpected behaviours might still occur, please report them by opening an issue):
- [Substance Suite](https://www.allegorithmic.com)
- [Poliigon](https://www.poliigon.com)
- [3D Wolf](https://www.3d-wolf.com/textures.html)
- [Megascans](https://megascans.se/)
- [Friendly Shade](https://www.friendlyshade.com/)


## Getting Started
### Installing
You can install this add-on in the User Preferences menu (Ctrl + Alt + U), in the Add-ons section, by clicking _Install Add-on from File…_ and providing the .py file.

### Settings
In the add-on preferences (in the User Preferences menu), you will find a list of predefined suffixes for the different texture files. You can check that the textures you will be using have their suffixes in this list, otherwise add them in each field. This has to be done only once per file naming convention.

## Features
- Create automatically a full PBR material node tree from a set of external textures. Detect the type of each texture by using its name and the list of suffixes in the add-on preferences.
- Adapt the number of texture nodes and the inputs of the node group according to the number of imported textures (see the 2nd and 3rd screenshots below).
- Create a new material for each set of textures and name it according to the textures names.
- Gather all the useful settings (color brightness, saturation, normal intensity, etc) in the Surface tab of the Material panel. These are the inputs of the node group which is connected to the Material Output node.
- Create empty node trees to start a PBR material with a good foundation. (See the panel on the 1st screenshot and an empty material on the 2nd screenshot)
- Support Metallic/Roughness and Specular/Glossiness maps. REMINDER: the Principled shader of Blender does not fully support the Specular/Glossiness workflow: its specular input is a greyscale map, whereas Specular maps should be colored in this workflow. More information [here](https://www.youtube.com/watch?v=mrNMpqdNchY).
- Provide an interface to set the mapping options (vector for the texture coordinates and projection of all the image textures) from the panel in the Material section. Works with all materials (not only with this add-on) provided there is a Texture Coordinate node, a Mapping node and Image Texture nodes.
- Bonus: a button to delete all unused data blocks. Useful after creating a lot of materials with this add-on but you don't need all of them :)

### Note about relief maps
Three types of relief maps are supported by this add-on: normal, bump and displacement/height. Here is how they are integrated into the node tree:
- A displacement map is always connected to the group output (after a math node for the intensity), for use with microdisplacement for example. Remember to disconnect the normal input of the Principled shader in this case.
- If there are only normal and bump maps, they are combined in a Bump node which is then connected to the Normal input of the Principled shader.
- The same thing with normal and displacement maps.
- If there are the three maps, the normal and bump maps are combined and the displacement just goes into the group output.
- If there is no normal map, the bump map is connected to the Normal input of the Principled shader after a Bump node, and the displacement map is connected to the group output.

## Screenshots
![Panel](https://raw.githubusercontent.com/jsulpis/blender-addons/master/PBR%20Material%20From%20Textures/Screenshots/material_panel.JPG)
![Full PBR node of Specular/Glossiness workflow](https://raw.githubusercontent.com/jsulpis/blender-addons/master/PBR%20Material%20From%20Textures/Screenshots/spec-glos_group_preview.jpg)
![Small group](https://raw.githubusercontent.com/jsulpis/blender-addons/master/PBR%20Material%20From%20Textures/Screenshots/small_group_preview.jpg)
