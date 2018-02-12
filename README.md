# PBR Material From Textures
This is an addon for Blender which automates the creation of PBR materials from textures by using their extension (Alb, AO, Nor, etc).

Tested with textures from the following sites (unexpected behaviours might still occur, please report them by opening an issue):
- [3d-wolf.com](https://www.3d-wolf.com/textures.html)
- [Poliigon.com](https://www.poliigon.com)
- [Substance Suite](https://www.allegorithmic.com)

### Current features
- Loads a set of textures and automatically creates a PBR material node tree
- Allows to set the mapping options (vector, scale and projection)
- Provide an interface to tweak the material (displacement and normal strength, mix Albedo - AO)
- Supports multiple file naming conventions (see the list of supported texture websites above)

### Backlog
- Rename the material using the texture names
- Create new materials after each import
- Integration with the microdisplacement feature
