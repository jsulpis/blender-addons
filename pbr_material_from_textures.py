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
from bpy.props import CollectionProperty, StringProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty, FloatProperty
from bpy.types import Operator, AddonPreferences


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

def set_color_map(self, context):
    """set the colors maps to use in the material"""
    value = self.color_map
    # deselect all
    bpy.ops.object.select_all(action='DESELECT')
    nodes = context.active_object.active_material.node_tree.nodes
    if value == 'DIF':
        image = PbrNodeTree.IMAGES["Dif"]
        PbrNodeTree.nodes["Color"].image = image
    elif value == 'ALB':
        image = PbrNodeTree.IMAGES["Alb"]
        PbrNodeTree.nodes["Color"].image = image
        
def toggle_normal(self, context):
    """Enable or disable the normal map"""
    ntree = bpy.context.active_object.active_material.node_tree
    if bpy.context.scene.mft_props.use_normal == False:
        normal_map = ntree.nodes["Normal Map"]
        normal_tex = ntree.nodes["Normal"]
        ntree.nodes.remove(normal_map)
        ntree.nodes.remove(normal_tex)
    else:
        PbrNodeTree.add_normal(image=PbrNodeTree.IMAGES["Nor"])
        
def toggle_disp(self, context):
    """Enable or disable the displacement map"""
    ntree = bpy.context.active_object.active_material.node_tree
    if bpy.context.scene.mft_props.use_disp == False:
        displacement_tex = ntree.nodes["Displacement"]
        math_node = ntree.nodes["Disp strength"]
        materialOutput = ntree.nodes["Material Output"]
        
        ntree.nodes.remove(displacement_tex)
        ntree.nodes.remove(math_node)
        materialOutput.location = (300, 0)
    else:
        PbrNodeTree.add_height(image=PbrNodeTree.IMAGES["Dis"])
    

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

    color_map = bpy.props.EnumProperty(
        name="Color map",
        items=[('DIF', 'Diffuse', 'Use the diffuse map.'),
            ('ALB', 'Albedo', 'Use the albedo map.')],
        description="Which color map to use",
        update=set_color_map,
        default='ALB',
    )
    
    use_normal = BoolProperty(
        name="Use normal map",
        default=True,
        update=toggle_normal
    )
    
    use_disp = BoolProperty(
        name="Use displacement map",
        default=True,
        update=toggle_disp
    )

#--------------------------------------------------------------------------------------------------------
# PBR Node Tree
#--------------------------------------------------------------------------------------------------------
class PbrNodeTree:
    """A class which encapsulates a PBR material node tree"""
    
    IMAGES = {}
    
    def init():

        # Create the class attributes
        PbrNodeTree.ntree = bpy.context.active_object.active_material.node_tree
        PbrNodeTree.nodes = PbrNodeTree.ntree.nodes
        
        # Clear the current node tree if needed
        PbrNodeTree.nodes.clear()    

        # Create a startup node tree : material output and principled shader
        materialOutput = PbrNodeTree.nodes.new("ShaderNodeOutputMaterial")
        materialOutput.location = (300, 0)

        principledShader = PbrNodeTree.nodes.new("ShaderNodeBsdfPrincipled")
        PbrNodeTree.add_link("Principled BSDF", 0, "Material Output", 0)
        
        # Add texture coordinates and mapping nodes
        PbrNodeTree.add_tex_coord()

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
        
    def add_color(image):
        """add a color map and mix it with the ambient occlusion if it exists"""
        if "Color" in PbrNodeTree.nodes.keys():
            return
        PbrNodeTree.add_image_texture(image, "Color", (-400, 100), 'COLOR')
        PbrNodeTree.add_link("Color", 0, "Principled BSDF", 0)
                
        if "Hue Saturation Value" not in PbrNodeTree.nodes.keys():
            PbrNodeTree.add_hsv_node()
        PbrNodeTree.add_link("Hue Saturation Value", 0, "Principled BSDF", 0)
        PbrNodeTree.add_link("Color", 0, "Hue Saturation Value", 4)
                
        if "Ambient Occlusion" in PbrNodeTree.nodes.keys():
            PbrNodeTree.nodes["Color"].location = (-600, 220)
            PbrNodeTree.mix_rgb("Color", 0, "Ambient Occlusion", 0, "Hue Saturation Value", 4)
        
    def add_ao(image):
        """add an ambient occlusion map and mix it with the diffuse if it exists"""
        PbrNodeTree.add_image_texture(image, "Ambient Occlusion", (-600, -40))
        if "Color" in PbrNodeTree.nodes.keys():
            PbrNodeTree.nodes["Color"].location = (-600, 220)
            PbrNodeTree.mix_rgb("Color", 0, "Ambient Occlusion", 0, "Hue Saturation Value", 4)

    def add_roughness(image):
        """add a roughness map"""
        if "Glossiness" in PbrNodeTree.nodes.keys():
            return
        PbrNodeTree.add_image_texture(image, "Roughness", (-400, -260))
        PbrNodeTree.add_link("Roughness", 0, "Principled BSDF", 7)
        
    def add_glossiness(image):
        """add a glossiness map"""
        if "Roughness" in PbrNodeTree.nodes.keys():
            return
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
            "Alb": PbrNodeTree.add_color,
            "AO": PbrNodeTree.add_ao,
            "Dif": PbrNodeTree.add_color,
            "Dis": PbrNodeTree.add_height,
            "Nor": PbrNodeTree.add_normal,
            "Rou": PbrNodeTree.add_roughness,
            "Glo": PbrNodeTree.add_glossiness,
            "Met": PbrNodeTree.add_metallic,
            "Bum": PbrNodeTree.add_bump
        }
        for extension, image in PbrNodeTree.IMAGES.items():
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

        row = layout.row()
        row.scale_y = 2
        row.operator("import_image.to_material", text="Load textures", icon="FILESEL")
        
        if not PbrNodeTree.IMAGES:
            # no map imported
            return
        
        mft_props = context.scene.mft_props
        ntree = context.active_object.active_material.node_tree
        
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

        if "Nor" in PbrNodeTree.IMAGES.keys():
            col = split.column()
            col.label("Normal:")
            col.prop(mft_props, 'use_normal', text="Enabled")
            if mft_props.use_normal:
                col.prop(ntree.nodes["Normal Map"].inputs[0], 'default_value', text="")

        if "Dis" in PbrNodeTree.IMAGES.keys():
            col = split.column()
            col.label("Displacement:")
            col.prop(mft_props, 'use_disp', text="Enabled")
            if mft_props.use_disp:        
                col.prop(ntree.nodes["Disp strength"].inputs[1], 'default_value', text="")
        
        row = box.row()
        row.operator("reset_nodes.relief", text="Reset Relief Settings")

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
            row.prop(mft_props, 'color_map', expand=True)
        
        split = box.split()
        
        col = split.column(align=True)
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[0], 'default_value', text="Hue")
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[1], 'default_value', text="Saturation")
        col.prop(ntree.nodes["Hue Saturation Value"].inputs[2], 'default_value', text="Value")
        
        if "Ambient Occlusion" in ntree.nodes.keys():
            col = split.column()
            col.label("AO Mix:")
            col.prop(ntree.nodes["Mix Col - Amb"].inputs[0], 'default_value', text="")
        
        row = box.row()
        row.operator("reset_nodes.color", text="Reset Color Settings")

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES'


#--------------------------------------------------------------------------------------------------------
# Operators
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
        # Create a new material
        new_material = bpy.data.materials.new(name=self.get_material_name())
        new_material.use_nodes = True
        bpy.context.active_object.active_material = new_material

        # Retrieve the images and their extension (type)
        images = self.sort_files(context, self.files, self.directory)                
        
        # Set the color map property (Diffuse or Albedo) if there is only one color map
        self.set_color_map(images)
        
        # Fill the node tree
        PbrNodeTree.init()
        PbrNodeTree.IMAGES = images
        PbrNodeTree.fill_tree()
            
        # Test
        #PbrNodeTree.add_metallic(None)
        #PbrNodeTree.add_glossiness(None)
        
        return {'FINISHED'}
    
    def get_material_name(self):
        """find the name of the material based on the textures name"""
        name1 = self.files[0].name.split('_')
        name2 = self.files[-1].name.split('_')
        intersection = set(name1).intersection(name2)
        name = ""
        for elt in intersection:
            elt = elt[0].upper() + elt[1:].lower()
            if "k" in elt:
                # there is the resolution of the texture, we don't want it
                continue
            name += " " + elt
        return name
    
    def sort_files(self, context, files, directory):
        """find the type (Diffuse, etc) of each map and return a dictionnary with each map associated to a type"""
        images = {}
        prefs = context.user_preferences.addons['pbr_material_from_textures'].preferences
        suffixes = {
            'diffuse_suffixes': 'Dif', 
            'albedo_suffixes': 'Alb', 
            'ao_suffixes': 'AO', 
            'roughness_suffixes': 'Rou', 
            'glossiness_suffixes': 'Glo', 
            'normal_suffixes': 'Nor', 
            'bump_suffixes': 'Bum', 
            'height_suffixes': 'Dis', 
            'metallic_suffixes': 'Met'
        }
        for file in files:
            path = directory + file.name
            print("Loading file: " + file.name)
            image = bpy.data.images.load(path, check_existing=True)
            name_list = image.name.split('.')[0].split('_')
            extension = name_list[-1]
            
            # Name variations
            if 'k' in extension.lower() or "hires" == extension.lower():
                # the last part of the name is probably the resolution (like 4K)
                if len(name_list) == 4:
                    # This is probably a Poliigon texture of either Color or Displacement
                    if name_list[1] == 'COL' and name_list[2] == 'VAR1':
                        images["Dif"] = image
                    elif name_list[1] == 'COL' and name_list[2] == 'VAR2':
                        images["Alb"] = image
                    elif name_list[1] == 'DISP':
                        images["Dis"] = image
                else:
                    # The extension we want should be before the resolution
                    extension = name_list[-2]
                    
            for type in suffixes.keys():
                if extension in prefs[type].split(';'):
                    suffix = suffixes[type]
                    images[suffix] = image
        return images

    def set_color_map(self, images):
        """ Set the color map property (Diffuse or Albedo) """
        dif, alb = False, False
        for extension in images.keys():
            if extension == "Dif":
                dif = True
            elif extension == "Alb":
                alb = True
        if dif and not alb:
            bpy.context.scene.mft_props.color_map = 'DIF'
        elif alb and not dif:
            bpy.context.scene.mft_props.color_map = 'ALB'


class ResetReliefSettings(Operator):
    """Reset the Normal and Displacement strengthes to their default values"""
    bl_idname = "reset_nodes.relief"
    bl_label = "Reset the relief settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ntree = bpy.context.active_object.active_material.node_tree
        if "Normal Map" in ntree.nodes.keys():
            normal_map = ntree.nodes["Normal Map"]
            normal_map.inputs[0].default_value = 1
        
        if "Disp strength" in ntree.nodes.keys():
            disp_mix = ntree.nodes["Disp strength"]
            disp_mix.inputs[1].default_value = 1
            
        return {'FINISHED'}
    
    
class ResetColorSettings(Operator):
    """Reset the Hue Saturation Value and AO-mix nodes to their default values"""
    bl_idname = "reset_nodes.color"
    bl_label = "Reset the color settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ntree = bpy.context.active_object.active_material.node_tree
        if "Hue Saturation Value" in ntree.nodes.keys():
            print("coucou")
            hsv_node = ntree.nodes["Hue Saturation Value"]
            hsv_node.inputs[0].default_value = 0.5
            hsv_node.inputs[1].default_value = 1
            hsv_node.inputs[2].default_value = 1
        
        if "Mix Col - Amb" in ntree.nodes.keys():
            print("hello")
            ao_mix = ntree.nodes["Mix Col - Amb"]
            ao_mix.inputs[0].default_value = 1
            
        return {'FINISHED'}

#--------------------------------------------------------------------------------------------------------
# Addon Preferences
#--------------------------------------------------------------------------------------------------------
class AddonPreferences(AddonPreferences):
    bl_idname = __name__

    diffuse_suffixes = StringProperty(name="Diffuse")
    albedo_suffixes = StringProperty(name="Albedo")
    ao_suffixes = StringProperty(name="Ambient Occlusion")
    roughness_suffixes = StringProperty(name="Roughness")
    glossiness_suffixes = StringProperty(name="Glossiness")
    normal_suffixes = StringProperty(name="Normal")
    bump_suffixes = StringProperty(name="Bump")
    height_suffixes = StringProperty(name="Height")
    metallic_suffixes = StringProperty(name="Metallic")
    
    show_suffixes = BoolProperty(name="File suffixes")

    def draw(self, context):
        layout = self.layout
        
        if not self.show_suffixes:
            layout.prop(self, "show_suffixes", icon="TRIA_RIGHT")
            
        else:
            layout.prop(self, "show_suffixes", icon="TRIA_DOWN")
            layout.label(text="Set the suffixes to use for each map, separated with semicolons.")
            
            layout.prop(self, "diffuse_suffixes")
            layout.prop(self, "albedo_suffixes")
            layout.prop(self, "ao_suffixes")
            layout.prop(self, "roughness_suffixes")
            layout.prop(self, "glossiness_suffixes")
            layout.prop(self, "normal_suffixes")
            layout.prop(self, "bump_suffixes")
            layout.prop(self, "height_suffixes")
            layout.prop(self, "metallic_suffixes")

    @staticmethod
    def init():
        """set the default values for the file suffixes"""
        prefs = bpy.context.user_preferences.addons['pbr_material_from_textures'].preferences
        prefs["diffuse_suffixes"] = "Dif;Diffuse;BaseColor"
        prefs["albedo_suffixes"] = "Alb;Albedo"
        prefs["ao_suffixes"] = "AO"
        prefs["roughness_suffixes"] = "Rou;Roughness"
        prefs["glossiness_suffixes"] = "Gloss;Glossiness;GLOSS"
        prefs["normal_suffixes"] = "Nor;Normal;NRM"
        prefs["bump_suffixes"] = "Bump"
        prefs["height_suffixes"] = "Dis;Height;DISP"
        prefs["metallic_suffixes"] = "Met;Metallic"


#--------------------------------------------------------------------------------------------------------
# Register
#--------------------------------------------------------------------------------------------------------
def register():
    bpy.utils.register_module(__name__)

    bpy.types.Scene.mft_props = bpy.props.PointerProperty(type=PBRMaterialProperties)
    AddonPreferences.init()
    

def unregister():
    bpy.utils.unregister_module(__name__)
    
    del bpy.types.Scene.mft_props

if __name__ == "__main__":
    register()
    