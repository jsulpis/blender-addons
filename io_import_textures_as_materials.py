#----------------------------------------------------------
# File io_import_textures_as_materials.py
#----------------------------------------------------------
import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import CollectionProperty
from bpy.types import Operator
  
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

    def add_image_texture(self, image, name, location, color_space='NONE'):
        """add an image texture node"""
        imageTexture = self.active_mat.node_tree.nodes.new("ShaderNodeTexImage")
        imageTexture.location = location
        imageTexture.label = name
        imageTexture.color_space = color_space
        self.nodes[name] = imageTexture
        
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
        self.nodes["Mapping"] = mapping
        
        self.add_link("Tex Coord", 0, "Mapping", 0)
        for name in ["Diffuse", "Ambient Occlusion", "Metallic", "Roughness", "Glossiness", "Normal", "Bump", "Height"]:
            if name in self.nodes.keys():
                self.add_link("Mapping", 0, name, 0)
        

    def add_link(self, nodeName1, outputId, nodeName2, inputId):
        """add a link between the two existing nodes"""
        node1 = self.nodes[nodeName1]
        node2 = self.nodes[nodeName2]
        self.active_mat.node_tree.links.new(node1.outputs[outputId], node2.inputs[inputId])


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
    """Load textures into a generated node tree to automate PBR material creation"""
    bl_idname = "import_image.to_material"
    bl_label = "Import Textures As Material"
    bl_options = {'REGISTER', 'UNDO'}

    files = CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)

    filename_ext = "*" + ";*".join(bpy.path.extensions_image)

    def execute(self, context):
        # Retrieve the current material
        active_mat = bpy.context.active_object.active_material
        active_mat.use_nodes = True

        # Fill the material node tree
        image = None
        
        node_tree = PbrNodeTree(active_mat)
            
        node_tree.add_metallic(image)
        node_tree.add_ao(image)
        node_tree.add_diffuse(image)
        
        #node_tree.add_roughness(image)
        node_tree.add_glossiness(image)
        node_tree.add_normal(image)
        #node_tree.add_bump(image)
        node_tree.add_height(image)
        
        node_tree.add_tex_coord()

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

    # test call
    bpy.ops.import_image.to_material('INVOKE_DEFAULT')