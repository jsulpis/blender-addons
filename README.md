# PBR Material From Textures
This is an add-on for Blender which automates the creation of PBR materials from textures by using their extension (Alb, AO, Nor, etc). It also allows to tweak the material from a simple user interface in not in the node tree.

Tested with textures from the following sites (unexpected behaviours might still occur, please report them by opening an issue):
- [3d-wolf.com](https://www.3d-wolf.com/textures.html)
- [Poliigon.com](https://www.poliigon.com)
- [Substance Suite](https://www.allegorithmic.com)

## Getting Started
### Installing
You can install this add-on in the User Preferences menu (Ctrl + Alt + U), in the Add-ons section, by clicking _Install Add-on from File…_ and providing the .py file.

### Settings
In the add-on preferences (in the User Preferences menu), you will find a list of predefined suffixes for the different texture files. You can check that the textures you will be using have their suffixes in this list, otherwise add them in each field. This has to be done only once per file naming convention.

## Features
### Done
- Loads a set of textures and automatically creates a PBR material node tree
- Allows to set the mapping options (vector, scale and projection)
- Provide an interface to tweak the material (displacement and normal strength, mix Albedo - AO)
- Supports multiple file naming conventions (see the list of supported texture websites above)
- Creates a new material for each set of textures and name it properly

### Backlog
- Add more options to tweak the material in the UI in the Material section
- Integration with the microdisplacement feature
