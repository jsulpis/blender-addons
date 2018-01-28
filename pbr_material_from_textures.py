#----------------------------------------------------------
# File pbr_material_from_textures.py
#----------------------------------------------------------

bl_info = {
    "name": "PBR Material from Textures",
    "author": "Julien Sulpis",
    "location": "Properties > Material > PBR Material from textures ",
    "description": "Creates a full PBR material from a set of image textures",
    "wiki_url": "https://github.com/jsulpis/blender-addons",
    "category": "Material"}

import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import CollectionProperty, StringProperty, EnumProperty, PointerProperty, FloatProperty
from bpy.types import Operator


#--------------------------------------------------------------------------------------------------------
# Settings

def set_mapping(self, context):
    """set the texture coordinate mapping"""
    value = int(self.mapping)
    tex_coord = context.active_object.active_material.node_tree.nodes["Texture Coordinate"]
    mapping = context.active_object.active_material.node_tree.nodes["Mapping"]
    context.active_object.active_material.node_tree.links.new(tex_coord.outputs[value], mapping.inputs[0])

def set_scale(self, context):
    """set the scale of the texture"""
    value = self.texture_scale
    mapping = context.active_object.active_material.node_tree.nodes["Mapping"]
    mapping.scale[0], mapping.scale[1], mapping.scale[2] = (value, value, value)
    
def set_projection(self, context):
    """set the projection of a 2D image on a 3D object"""
    value = self.projection
    for node in bpy.context.active_object.active_material.node_tree.nodes:
        if node.name.startswith("Image Texture"):
            node.projection = value    


class PBRMaterialSettings(bpy.types.PropertyGroup):
    """The set of properties to tweak the material"""
    mapping = bpy.props.EnumProperty(
        name="Vector",
        items=[('0', 'Generated', 'Automatically-generated texture coordinates from the vertex positions of the mesh without deformation.'),
            ('1', 'Normal', 'Object space normal, for texturing objects with the texture staying fixed on the object as it transformed.'),
            ('2', 'UV', 'UV texture coordinates from the active render UV map.'),
            ('3', 'Object', 'Position coordinate in object space.'),
            ('4', 'Camera', 'Position coordinate in camera space.'),
            ('5', 'Window', 'Location of shading point on the screen, ranging from 0.0 to 1. 0 from the left to right side and bottom to top of the render.'),
            ('6', 'Reflection', 'Vector in the direction of a sharp reflection, typically used for environment maps.')],
        description="Calculation of the texture vector",
        update=set_mapping,
        default='0',
    )
    
    texture_scale = bpy.props.FloatProperty(
        name="Texture scale",
        description="Texture scale",
        update=set_scale,
        soft_min=0,
        step=10,
        default=1.0
    )
    
    projection = bpy.props.EnumProperty(
        name="Projection",
        items=[('FLAT', 'Flat', 'Image is projected flat using the X and Y coordinates of the texture vector.'),
            ('BOX', 'Box', 'Image is projected using different components for each side of the object space bounding box.'),
            ('SPHERE', 'Sphere', 'Sphere, Image is projected spherically using the Z axis as central.'),
            ('TUBE', 'Tube', 'Image is projected from the tube using the Z axis as central.')],
        description="Method to project 2D image on object with a 3D texture vector",
        update=set_projection,
        default='FLAT',
    )


#--------------------------------------------------------------------------------------------------------
# PBR Node Tree
class PbrNodeTree:
    """A class which encapsulates a PBR material node tree"""

    def __init__(self, active_mat):
        self.active_mat = active_mat
        self.nodes = {}

        # Clear the current node tree if needed
        self.active_mat.node_tree.nodes.clear()    

        # Create a startup node tree : material output and principled shader
        materialOutput = self.active_mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        materialOutput.location = (300, 0)
        self.nodes["Output"] = materialOutput

        principledShader = self.active_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        self.nodes["Principled"] = principledShader
        self.active_mat.node_tree.links.new(principledShader.outputs[0], materialOutput.inputs[0])
        
        # Add texture coordinates and mapping nodes
        self.add_tex_coord()

    def add_image_texture(self, image, name, location, color_space='NONE'):
        """add an image texture node"""
        imageTexture = self.active_mat.node_tree.nodes.new("ShaderNodeTexImage")
        imageTexture.image = image
        imageTexture.location = location
        imageTexture.label = name
        imageTexture.color_space = color_space
        self.nodes[name] = imageTexture
        
        self.add_link("Mapping", 0, name, 0)
        
    def add_diffuse(self, image):
        """add a diffuse map and mix it with the ambient occlusion if it exists"""
        self.add_image_texture(image, "Diffuse", (-400, 0), 'COLOR')
        self.add_link("Diffuse", 0, "Principled", 0)
        if "Ambient Occlusion" in self.nodes.keys():
            self.nodes["Diffuse"].location.y = 260
            self.mix_rgb("Diffuse", 0, "Ambient Occlusion", 0, "Principled", 0)
        
    def add_ao(self, image):
        """add an ambient occlusion map and mix it with the diffuse if it exists"""
        self.add_image_texture(image, "Ambient Occlusion", (-400, 0))
        if "Diffuse" in self.nodes.keys():
            self.nodes["Diffuse"].location = (-400, 260)
            self.mix_rgb("Diffuse", 0, "Ambient Occlusion", 0, "Principled", 0)

    def add_roughness(self, image):
        """add a roughness map"""
        self.add_image_texture(image, "Roughness", (-400, -260))
        self.add_link("Roughness", 0, "Principled", 7)
        
    def add_glossiness(self, image):
        """add a glossiness map"""
        self.add_image_texture(image, "Glossiness", (-400, -260))
        invert = self.active_mat.node_tree.nodes.new("ShaderNodeInvert")
        invert.location = (-200, -340)
        self.nodes["Invert"] = invert
        self.add_link("Glossiness", 0, "Invert", 1)
        self.add_link("Invert", 0, "Principled", 7)
        
    def add_normal(self, image):
        """add a normal map texture and a normal map node"""
        self.add_image_texture(image, "Normal", (-400, -520))
        normalMap = self.active_mat.node_tree.nodes.new("ShaderNodeNormalMap")
        normalMap.location = (-200, -500)
        self.nodes["Normal Map"] = normalMap
        self.add_link("Normal", 0, "Normal Map", 1)
        self.add_link("Normal Map", 0, "Principled", 17)
        
    def add_bump(self, image):
        """add a bump texture and a bump node"""
        self.add_image_texture(image, "Bump", (-400, -520))
        normalMap = self.active_mat.node_tree.nodes.new("ShaderNodeBump")
        normalMap.location = (-200, -500)
        self.nodes["Bump Map"] = normalMap
        self.add_link("Bump", 0, "Bump Map", 2)
        self.add_link("Bump Map", 0, "Principled", 17)
        
    def add_metallic(self, image):
        """add a metallic map"""
        self.add_image_texture(image, "Metallic", (-200, -80))
        self.add_link("Metallic", 0, "Principled", 4)

    def add_height(self, image):
        """add a displacement map and a math node to adjust the strength"""
        self.nodes["Output"].location.x = 600
        self.add_image_texture(image, "Displacement", (200, -100))

        mix_shader = self.active_mat.node_tree.nodes.new("ShaderNodeMath")
        mix_shader.location = (400, -100)
        mix_shader.inputs[0].default_value = 0
        name = "Disp strength"
        mix_shader.label = name
        mix_shader.operation = 'MULTIPLY'
        mix_shader.inputs[1].default_value = 1
        self.nodes[name] = mix_shader

        self.add_link("Displacement", 0, "Disp strength", 0)
        self.add_link("Disp strength", 0, "Output", 2)        

    def mix_rgb(self, nodeName1, input1, nodeName2, input2, nodeName3, output):
        """add a mix RGB shader in multiply mode between two existing nodes"""
        mix_shader = self.active_mat.node_tree.nodes.new("ShaderNodeMixRGB")
        mix_shader.inputs[0].default_value = 1
        
        location_y = (self.nodes[nodeName1].location.y + self.nodes[nodeName2].location.y) / 2
        location_x = max(self.nodes[nodeName1].location.x, self.nodes[nodeName2].location.x) + 200
        mix_shader.location = (location_x, location_y)
        mix_shader.blend_type = 'MULTIPLY'

        name = "Mix " + nodeName1[:3] + " - " + nodeName2[:3]
        mix_shader.label = name

        self.nodes[name] = mix_shader
        self.add_link(nodeName1, input1, name, 1)
        self.add_link(nodeName2, input2, name, 2)
        self.add_link(name, 0, nodeName3, output)
        
    def add_tex_coord(self):
        """add a texture coordinate and mapping nodes"""
        text_coord = self.active_mat.node_tree.nodes.new("ShaderNodeTexCoord")
        text_coord.location = (-1000, 0)
        self.nodes["Tex Coord"] = text_coord
        
        mapping = self.active_mat.node_tree.nodes.new("ShaderNodeMapping")
        mapping.location = (-800, 0)
        scale = bpy.context.scene.mft_props.texture_scale
        mapping.scale[0], mapping.scale[1], mapping.scale[2] = (scale, scale, scale)
        self.nodes["Mapping"] = mapping
        
        self.add_link("Tex Coord", int(bpy.context.scene.mft_props.mapping), "Mapping", 0)

    def add_link(self, nodeName1, outputId, nodeName2, inputId):
        """add a link between the two existing nodes"""
        node1 = self.nodes[nodeName1]
        node2 = self.nodes[nodeName2]
        self.active_mat.node_tree.links.new(node1.outputs[outputId], node2.inputs[inputId])
        
    def add_nodes(self, image):
        """add one or more nodes depending on the image type"""
        actions = {
            "Alb": self.add_diffuse,
            "AO": self.add_ao,
            "Dif": self.add_diffuse,
            "Dis": self.add_height,
            "Nor": self.add_normal,
            "Rou": self.add_roughness,
            "Glo": self.add_glossiness,
            "Met": self.add_metallic,
            "Bum": self.add_bump
        }
        extension = image.name.split('.')[0].split("_")[-1]
        if extension in actions.keys():
            actions[extension](image)


class MaterialPanel(bpy.types.Panel):
    """Create a Panel in the Material window"""
    bl_label = "PBR Material from Textures"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
        
    def draw(self, context):
        layout = self.layout
        mft_props = context.scene.mft_props

        row = layout.row()
        row.operator("import_image.to_material", text="Load textures", icon="FILESEL")

        # Mapping      
        layout.label(text="Mapping")
        
        row = layout.row()
        row.prop(mft_props, 'mapping', text="")
        row.prop(mft_props, 'texture_scale', text="Scale")
        row.prop(mft_props, 'projection', text="")

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES' and \
    context.active_object.material_slots.data.active_material


class ImportTexturesAsMaterial(Operator, ImportHelper):
    """Load textures into a generated node tree to automate PBR material creation"""
    bl_idname = "import_image.to_material"
    bl_label = "Import Textures As Material"
    bl_options = {'REGISTER', 'UNDO'}

    files = CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory = StringProperty(maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    filename_ext = "*" + ";*".join(bpy.path.extensions_image)

    def execute(self, context):
        # Retrieve the current material
        active_mat = bpy.context.active_object.active_material
        active_mat.use_nodes = True

        # Fill the material node tree
        node_tree = PbrNodeTree(active_mat)
        
        for file in self.files:
            path = self.directory + file.name
            print("Loading file: " + file.name)
            image = bpy.data.images.load(path, check_existing=True)
            node_tree.add_nodes(image)
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ImportTexturesAsMaterial)
    bpy.utils.register_class(MaterialPanel)
    bpy.utils.register_class(PBRMaterialSettings)

    bpy.types.Scene.mft_props = bpy.props.PointerProperty(type=PBRMaterialSettings)

def unregister():
    bpy.utils.unregister_class(ImportTexturesAsMaterial)
    bpy.utils.unregister_class(MaterialPanel)
    bpy.utils.unregister_class(PBRMaterialSettings)
    
    del bpy.types.Scene.mft_props

if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.import_image.to_material('INVOKE_DEFAULT')