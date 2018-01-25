#----------------------------------------------------------
# File io_import_textures_as_materials.py
#----------------------------------------------------------
import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import CollectionProperty
from bpy.types import Operator
  

class MaterialPanel(bpy.types.Panel):
    """Create a Panel in the Material window"""
    bl_label = "Material from textures"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
        
    def draw(self, context):
        self.layout.operator("import_image.to_material", text="Load textures", icon="FILESEL")
        
    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES' and \
    context.active_object.material_slots.data.active_material


class ImportTexturesAsMaterial(Operator, ImportHelper):
    """Load textures into a generated node tree to automate PBR material creation."""
    bl_idname = "import_image.to_material"
    bl_label = "Import Textures As Material"
    bl_options = {'REGISTER', 'UNDO'}

    files = CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)

    filename_ext = "*" + ";*".join(bpy.path.extensions_image)

    def execute(self, context):
        for file in self.files:
            print("Loaded file: " + file.name)
        return {"FINISHED"}

def register():
    bpy.utils.register_class(ImportTexturesAsMaterial)
    bpy.utils.register_class(MaterialPanel)


def unregister():
    bpy.utils.unregister_class(ImportTexturesAsMaterial)
    bpy.utils.unregister_class(MaterialPanel)

if __name__ == "__main__":
    register()
