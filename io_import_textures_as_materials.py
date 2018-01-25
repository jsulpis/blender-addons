import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import CollectionProperty
from bpy.types import Operator


class ImportTexturesAsMaterial(Operator, ImportHelper):
    """Load textures into a generated node tree to automate PBR material creation."""
    bl_idname = "import_image.to_material"
    bl_label = "Import Textures As Material"
    bl_options = {'REGISTER', 'UNDO'}

    files = CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)

    filename_ext = "*" + ";*".join(bpy.path.extensions_image)

    def execute(self, context):
        for file in self.files:
            print(file.name)
        return {"FINISHED"}

def register():
    bpy.utils.register_class(ImportTexturesAsMaterial)


def unregister():
    bpy.utils.unregister_class(ImportTexturesAsMaterial)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_image.to_material('INVOKE_DEFAULT')
