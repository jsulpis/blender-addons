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
#--------------------------------------------------------------------------------------------------------
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
        if node.type == 'TEX_IMAGE':
            node.projection = value

def set_color_maps(self, context):
    """set the colors maps to use in the material"""
    value = self.color_maps
    # deselect all
    bpy.ops.object.select_all(action='DESELECT')
    nodes = context.active_object.active_material.node_tree.nodes
    if value == 'DIF':
        if "Diffuse" in nodes.keys():
            # the diffuse map is already created
            return
        if "Ambient Occlusion" in nodes.keys():
            ao = nodes["Ambient Occlusion"]
            nodes.remove(ao)
        if "Mix Alb - Amb" in nodes.keys():
            mix = nodes["Mix Alb - Amb"]
            nodes.remove(mix)
        if "Albedo" in nodes.keys():
            albedo = nodes["Albedo"]
            nodes.remove(albedo)
        image = PbrNodeTree.IMAGES["Dif"]
        PbrNodeTree.add_diffuse(image)
    elif value == 'ALB':
        if "Albedo" in nodes.keys():
            # the Albedo + AO maps are already created
            return
        if "Diffuse" in nodes.keys():
            diffuse = nodes["Diffuse"]
            nodes.remove(diffuse)
        PbrNodeTree.add_albedo(PbrNodeTree.IMAGES["Alb"])
        PbrNodeTree.add_ao(PbrNodeTree.IMAGES["AO"])
        


class PBRMaterialProperties(bpy.types.PropertyGroup):
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

    color_maps = bpy.props.EnumProperty(
        name="Color maps",
        items=[('DIF', 'Diffuse', 'Use only the diffuse map.'),
            ('ALB', 'Albedo + AO', 'Mix the Albedo and Ambient Occlusion maps.')],
        description="Which color maps to use",
        update=set_color_maps,
        default='ALB',
    )
    

#--------------------------------------------------------------------------------------------------------
# PBR Node Tree
#--------------------------------------------------------------------------------------------------------
class PbrNodeTree:
    """A class which encapsulates a PBR material node tree"""
    ntree = bpy.context.active_object.active_material.node_tree
    nodes = ntree.nodes
    IMAGES = {}
    
    def init():

        # Clear the current node tree if needed
        PbrNodeTree.nodes.clear()    

        # Create a startup node tree : material output and principled shader
        materialOutput = PbrNodeTree.nodes.new("ShaderNodeOutputMaterial")
        materialOutput.location = (300, 0)

        principledShader = PbrNodeTree.nodes.new("ShaderNodeBsdfPrincipled")
        PbrNodeTree.add_link("Principled BSDF", 0, "Material Output", 0)
        
        # Add texture coordinates and mapping nodes
        PbrNodeTree.add_tex_coord()
        print(bpy.context.scene.mft_props.color_maps)

    def add_image_texture(image, name, location, color_space='NONE'):
        """add an image texture node"""
        imageTexture = PbrNodeTree.nodes.new("ShaderNodeTexImage")
        imageTexture.image = image
        imageTexture.location = location
        imageTexture.name = name
        imageTexture.label = name
        imageTexture.color_space = color_space
        
        PbrNodeTree.add_link("Mapping", 0, name, 0)
        
    def add_hsv_node():
        """add a Hue Saturation Value node"""
        hue = PbrNodeTree.nodes.new("ShaderNodeHueSaturation")
        hue.location = (-200, 90)
                
    def add_diffuse(image):
        """add a diffuse map and mix it with the ambient occlusion if it exists"""
        print(bpy.context.scene.mft_props.color_maps)
        if bpy.context.scene.mft_props.color_maps == 'DIF':
            PbrNodeTree.add_image_texture(image, "Diffuse", (-400, 100), 'COLOR')
            PbrNodeTree.add_link("Diffuse", 0, "Principled BSDF", 0)
                
            if "Hue Saturation Value" not in PbrNodeTree.nodes.keys():
                PbrNodeTree.add_hsv_node()
            PbrNodeTree.add_link("Hue Saturation Value", 0, "Principled BSDF", 0)
            PbrNodeTree.add_link("Diffuse", 0, "Hue Saturation Value", 4)
        
    def add_albedo(image):
        """add a diffuse map and mix it with the ambient occlusion if it exists"""
        if bpy.context.scene.mft_props.color_maps == 'ALB':
            PbrNodeTree.add_image_texture(image, "Albedo", (-400, 100), 'COLOR')
            PbrNodeTree.add_link("Albedo", 0, "Principled BSDF", 0)
                
            if "Hue Saturation Value" not in PbrNodeTree.nodes.keys():
                PbrNodeTree.add_hsv_node()
            PbrNodeTree.add_link("Hue Saturation Value", 0, "Principled BSDF", 0)
            PbrNodeTree.add_link("Albedo", 0, "Hue Saturation Value", 4)
                
            if "Ambient Occlusion" in PbrNodeTree.nodes.keys():
                PbrNodeTree.nodes["Albedo"].location = (-600, 220)
                PbrNodeTree.mix_rgb("Albedo", 0, "Ambient Occlusion", 0, "Hue Saturation Value", 4)
        
    def add_ao(image):
        """add an ambient occlusion map and mix it with the diffuse if it exists"""
        if bpy.context.scene.mft_props.color_maps == 'ALB':
            PbrNodeTree.add_image_texture(image, "Ambient Occlusion", (-600, -40))
            if "Albedo" in PbrNodeTree.nodes.keys():
                PbrNodeTree.nodes["Albedo"].location = (-600, 220)
                PbrNodeTree.mix_rgb("Albedo", 0, "Ambient Occlusion", 0, "Hue Saturation Value", 4)

    def add_roughness(image):
        """add a roughness map"""
        PbrNodeTree.add_image_texture(image, "Roughness", (-400, -260))
        PbrNodeTree.add_link("Roughness", 0, "Principled BSDF", 7)
        
    def add_glossiness(image):
        """add a glossiness map"""
        PbrNodeTree.add_image_texture(image, "Glossiness", (-400, -260))
        invert = PbrNodeTree.nodes.new("ShaderNodeInvert")
        invert.location = (-200, -340)
        PbrNodeTree.add_link("Glossiness", 0, "Invert", 1)
        PbrNodeTree.add_link("Invert", 0, "Principled BSDF", 7)
        
    def add_normal(image):
        """add a normal map texture and a normal map node"""
        PbrNodeTree.add_image_texture(image, "Normal", (-400, -520))
        normalMap = PbrNodeTree.nodes.new("ShaderNodeNormalMap")
        normalMap.location = (-200, -500)
        PbrNodeTree.add_link("Normal", 0, "Normal Map", 1)
        PbrNodeTree.add_link("Normal Map", 0, "Principled BSDF", 17)
        
    def add_bump(image):
        """add a bump texture and a bump node"""
        PbrNodeTree.add_image_texture(image, "Bump", (-400, -520))
        bumpMap = PbrNodeTree.nodes.new("ShaderNodeBump")
        bumpMap.name = "Bump Map"
        bumpMap.location = (-200, -500)
        PbrNodeTree.add_link("Bump", 0, "Bump Map", 2)
        PbrNodeTree.add_link("Bump Map", 0, "Principled BSDF", 17)
        
    def add_metallic(image):
        """add a metallic map"""
        PbrNodeTree.add_image_texture(image, "Metallic", (-200, -80))
        PbrNodeTree.add_link("Metallic", 0, "Principled BSDF", 4)

    def add_height(image):
        """add a displacement map and a math node to adjust the strength"""
        PbrNodeTree.nodes["Material Output"].location.x = 600
        PbrNodeTree.add_image_texture(image, "Displacement", (200, -100))

        mix_shader = PbrNodeTree.nodes.new("ShaderNodeMath")
        mix_shader.location = (400, -100)
        mix_shader.inputs[0].default_value = 0
        name = "Disp strength"
        mix_shader.name = name
        mix_shader.label = name
        mix_shader.operation = 'MULTIPLY'
        mix_shader.inputs[1].default_value = 1

        PbrNodeTree.add_link("Displacement", 0, "Disp strength", 0)
        PbrNodeTree.add_link("Disp strength", 0, "Material Output", 2)        

    def mix_rgb(nodeName1, input1, nodeName2, input2, nodeName3, output):
        """add a mix RGB shader in multiply mode between two existing nodes"""
        mix_shader = PbrNodeTree.nodes.new("ShaderNodeMixRGB")
        mix_shader.inputs[0].default_value = 1
        
        location_y = (PbrNodeTree.nodes[nodeName1].location.y + PbrNodeTree.nodes[nodeName2].location.y) / 2
        location_x = max(PbrNodeTree.nodes[nodeName1].location.x, PbrNodeTree.nodes[nodeName2].location.x) + 200
        mix_shader.location = (location_x, location_y)
        mix_shader.blend_type = 'MULTIPLY'

        name = "Mix " + nodeName1[:3] + " - " + nodeName2[:3]
        mix_shader.name = name
        mix_shader.label = name

        PbrNodeTree.add_link(nodeName1, input1, name, 1)
        PbrNodeTree.add_link(nodeName2, input2, name, 2)
        PbrNodeTree.add_link(name, 0, nodeName3, output)
        
    def add_tex_coord():
        """add a texture coordinate and mapping nodes"""
        text_coord = PbrNodeTree.nodes.new("ShaderNodeTexCoord")
        text_coord.location = (-1200, -40)
        
        mapping = PbrNodeTree.nodes.new("ShaderNodeMapping")
        mapping.location = (-1000, -40)
        scale = bpy.context.scene.mft_props.texture_scale
        mapping.scale[0], mapping.scale[1], mapping.scale[2] = (scale, scale, scale)
        
        PbrNodeTree.add_link("Texture Coordinate", int(bpy.context.scene.mft_props.mapping), "Mapping", 0)

    def add_link(nodeName1, outputId, nodeName2, inputId):
        """add a link between the two existing nodes"""
        node1 = PbrNodeTree.nodes[nodeName1]
        node2 = PbrNodeTree.nodes[nodeName2]
        PbrNodeTree.ntree.links.new(node1.outputs[outputId], node2.inputs[inputId])
        
    @staticmethod
    def fill_tree():
        """create the nodes according to the available maps"""
        actions = {
            "Alb": PbrNodeTree.add_albedo,
            "AO": PbrNodeTree.add_ao,
            "Dif": PbrNodeTree.add_diffuse,
            "Dis": PbrNodeTree.add_height,
            "Nor": PbrNodeTree.add_normal,
            "Rou": PbrNodeTree.add_roughness,
            "Glo": PbrNodeTree.add_glossiness,
            "Met": PbrNodeTree.add_metallic,
            "Bum": PbrNodeTree.add_bump
        }
        for extension, image in PbrNodeTree.IMAGES.items():
            print(extension)
            if extension in actions.keys():
                actions[extension](image)


#--------------------------------------------------------------------------------------------------------
# Panel
#--------------------------------------------------------------------------------------------------------
class MaterialPanel(bpy.types.Panel):
    """Create a Panel in the Material window"""
    bl_label = "PBR Material from Textures"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
        
    def draw(self, context):
        layout = self.layout
        mft_props = context.scene.mft_props
        ntree = context.active_object.active_material.node_tree

        row = layout.row()
        row.scale_y = 2
        row.operator("import_image.to_material", text="Load textures", icon="FILESEL")
        
        # Mapping
        box = layout.box()
        box.label("Mapping")
        
        split = box.split()
        
        col = split.column()
        col.label("Vector:")
        col.prop(mft_props, 'mapping', text="")
        
        col = split.column()
        col.label("Scale:")
        col.prop(mft_props, 'texture_scale', text="")
        
        col = split.column()
        col.label("Projection:")
        col.prop(mft_props, 'projection', text="")
        
        # Relief strength
        box = layout.box()
        box.label("Relief strength")
        split = box.split()

        col = split.column()
        col.label("Normal:")
        col.prop(ntree.nodes["Normal Map"].inputs[0], 'default_value', text="")

        col = split.column()
        col.label("Displacement:")
        col.prop(ntree.nodes["Disp strength"].inputs[1], 'default_value', text="")

        # Color
        box = layout.box()
        box.label("Color")
        
        dif, alb = False, False
        for extension in PbrNodeTree.IMAGES.keys():
            if extension == "Dif":
                dif = True
            elif extension == "Alb":
                alb = True
        if dif and alb:
            row = box.row()
            row.prop(mft_props, 'color_maps', expand=True)
        
        split = box.split()
        
        col = split.column(align=True)
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[0], 'default_value', text="Hue")
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[1], 'default_value', text="Saturation")
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[2], 'default_value', text="Value")
        
        if bpy.context.scene.mft_props.color_maps == 'ALB':
            col = split.column()
            col.label("Alb - AO Mix:")
            col.prop(ntree.nodes["Mix Alb - Amb"].inputs[0], 'default_value', text="")
        

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES' and \
    context.active_object.material_slots.data.active_material


#--------------------------------------------------------------------------------------------------------
# Operator
#--------------------------------------------------------------------------------------------------------
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

        # Retrieve the images and their extension (type)
        images = {}
        for file in self.files:
            path = self.directory + file.name
            print("Loading file: " + file.name)
            image = bpy.data.images.load(path, check_existing=True)
            extension = image.name.split('.')[0].split("_")[-1]
            images[extension] = image
        
        # Set the color map property (Diffuse or Albedo + AO)
        dif, alb = False, False
        for extension in images.keys():
            if extension == "Dif":
                dif = True
            elif extension == "Alb":
                alb = True
        if dif and not alb:
            bpy.context.scene.mft_props.color_maps = 'DIF'
        elif alb and not dif:
            bpy.context.scene.mft_props.color_maps = 'ALB'
        
        # Fill the node tree
        PbrNodeTree.init()
        PbrNodeTree.IMAGES = images
        PbrNodeTree.fill_tree()
            
        # Test
        #PbrNodeTree.add_metallic(None)
        #PbrNodeTree.add_glossiness(None)
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ImportTexturesAsMaterial)
    bpy.utils.register_class(MaterialPanel)
    bpy.utils.register_class(PBRMaterialProperties)

    bpy.types.Scene.mft_props = bpy.props.PointerProperty(type=PBRMaterialProperties)
    

def unregister():
    bpy.utils.unregister_class(ImportTexturesAsMaterial)
    bpy.utils.unregister_class(MaterialPanel)
    bpy.utils.unregister_class(PBRMaterialProperties)
    
    del bpy.types.Scene.mft_props

if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.import_image.to_material('INVOKE_DEFAULT')