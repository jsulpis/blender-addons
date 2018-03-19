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
    
def set_projection(self, context):
    """set the projection of a 2D image on a 3D object"""
    value = self.projection
    for node in bpy.context.active_object.active_material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            node.projection = value

def toggle_microdisp(self, context):
    """Enable or disable the microdisplacement feature"""
    mode = bpy.context.scene.cycles.feature_set
    bpy.context.scene.cycles.feature_set = 'EXPERIMENTAL' if mode == 'SUPPORTED' else 'SUPPORTED'
    object = bpy.context.active_object
    object.active_material.cycles.displacement_method = 'TRUE'
    if "Subsurf" not in object.modifiers.keys():
        bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.scene.mft_props.use_normal = False
    object.cycles.use_adaptive_subdivision = True

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
    
    use_microdisp = BoolProperty(
        name="Use microdisplacement feature",
        default=False,
        update=toggle_microdisp
    )

#--------------------------------------------------------------------------------------------------------
# PBR Node Tree
#--------------------------------------------------------------------------------------------------------
class PbrNodeTree:
    """A class which encapsulates a PBR material node tree"""
    
    IMAGES = {}
    
    def init(material_name):

        # Create the class attributes
        PbrNodeTree.base_tree = bpy.context.active_object.active_material.node_tree
        PbrNodeTree.base_tree.nodes.clear()  
        
        PbrNodeTree.ntree = bpy.data.node_groups.new(type="ShaderNodeTree", name=material_name)
        PbrNodeTree.nodes = PbrNodeTree.ntree.nodes

        PbrNodeTree.pbr_group = PbrNodeTree.base_tree.nodes.new("ShaderNodeGroup")
        PbrNodeTree.pbr_group .node_tree = PbrNodeTree.ntree
        PbrNodeTree.pbr_group .width = 250

        input_node = PbrNodeTree.nodes.new("NodeGroupInput")
        input_node.location = (-1800, -300)
        output_node = PbrNodeTree.nodes.new("NodeGroupOutput")
        output_node.location = (350, 0)
        
        # Create a startup node tree : material output and principled shader
        material_output = PbrNodeTree.base_tree.nodes.new("ShaderNodeOutputMaterial")
        material_output.location = (300, 0)
        
        PbrNodeTree.ntree.outputs.new("NodeSocketShader", "Surface")
        PbrNodeTree.base_tree.links.new(PbrNodeTree.pbr_group .outputs[0], material_output.inputs[0])
        
        PbrNodeTree.nodes.new("ShaderNodeBsdfPrincipled")
        PbrNodeTree.add_link("Principled BSDF", 0, "Group Output", 0)
        
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
        imageTexture.projection = bpy.context.scene.mft_props.projection
        imageTexture.width = 250
        
        PbrNodeTree.add_link("Scale", 0, name, 0)
        
    def add_color(image):
        """add a color map and mix it with the ambient occlusion if it exists"""
        if "Color" in PbrNodeTree.nodes.keys():
            return
        PbrNodeTree.add_image_texture(image, "Color", (-1200, 600), 'COLOR')
                
        hue = PbrNodeTree.nodes.new("ShaderNodeHueSaturation")
        hue.location = (-900, 600)
        
        brightness = PbrNodeTree.nodes.new("ShaderNodeBrightContrast")
        brightness.location = (-700, 600)
        
        PbrNodeTree.add_link("Hue Saturation Value", 0, "Bright/Contrast", 0)
        PbrNodeTree.add_link("Bright/Contrast", 0, "Principled BSDF", 0)
        PbrNodeTree.add_link("Color", 0, "Hue Saturation Value", 4)
                
        if "Ambient Occlusion" in PbrNodeTree.nodes.keys():
            PbrNodeTree.mix_col_ao()
        
    def add_ao(image):
        """add an ambient occlusion map and mix it with the diffuse if it exists"""
        PbrNodeTree.add_image_texture(image, "Ambient Occlusion", (-1200, 300))
        if "Color" in PbrNodeTree.nodes.keys():
            PbrNodeTree.mix_col_ao()
            
    def add_metallic(image):
        """add a metallic map"""
        PbrNodeTree.add_image_texture(image, "Metallic", (-1200, 0))
        PbrNodeTree.add_link("Metallic", 0, "Principled BSDF", 4)
        
    def add_specular(image):
        """add a specular map"""
        PbrNodeTree.add_image_texture(image, "Specular", (-1200, 0))
                
        offset_node = PbrNodeTree.nodes.new("ShaderNodeMath")
        offset_node.location = (-900, 0)
        offset_node.name = "Reflection Offset"
        offset_node.label = "Reflection Offset"
        offset_node.operation = 'ADD'
        
        PbrNodeTree.add_link("Specular", 0, "Reflection Offset", 0)
        PbrNodeTree.add_link("Reflection Offset", 0, "Principled BSDF", 5)

    def add_roughness(image):
        """add a roughness map and a math node for the offset"""
        if "Glossiness" in PbrNodeTree.nodes.keys():
            return
        PbrNodeTree.add_image_texture(image, "Roughness", (-1200, -300))
        
        offset_node = PbrNodeTree.nodes.new("ShaderNodeMath")
        offset_node.location = (-900, -300)
        offset_node.name = "Roughness Offset"
        offset_node.label = "Roughness Offset"
        offset_node.operation = 'ADD'
        
        PbrNodeTree.add_link("Roughness", 0, "Roughness Offset", 0)
        PbrNodeTree.add_link("Roughness Offset", 0, "Principled BSDF", 7)
        
    def add_glossiness(image):
        """add a glossiness map"""
        if "Roughness" in PbrNodeTree.nodes.keys():
            return
        PbrNodeTree.add_image_texture(image, "Glossiness", (-1200, -300))
        offset_node = PbrNodeTree.nodes.new("ShaderNodeMath")
        offset_node.location = (-900, -300)
        offset_node.name = "Glossiness Offset"
        offset_node.label = "Glossiness Offset"
        offset_node.operation = 'ADD'
        
        invert = PbrNodeTree.nodes.new("ShaderNodeInvert")
        invert.location = (-700, -300)
        
        PbrNodeTree.add_link("Glossiness", 0, "Glossiness Offset", 0)
        PbrNodeTree.add_link("Glossiness Offset", 0, "Invert", 1)
        PbrNodeTree.add_link("Invert", 0, "Principled BSDF", 7)
        
    def add_normal(image):
        """add a normal map texture and a normal map node"""
        if "Bump" in PbrNodeTree.nodes.keys():
            "we currently override the bump map with the normal map"
            PbrNodeTree.nodes.remove(PbrNodeTree.nodes["Bump"])
            PbrNodeTree.nodes.remove(PbrNodeTree.nodes["Bump Map"])
            
        PbrNodeTree.add_image_texture(image, "Normal", (-1200, -600))
        normalMap = PbrNodeTree.nodes.new("ShaderNodeNormalMap")
        normalMap.location = (-900, -600)
        PbrNodeTree.add_link("Normal", 0, "Normal Map", 1)
        PbrNodeTree.add_link("Normal Map", 0, "Principled BSDF", 17)
        
    def add_bump(image):
        """add a bump texture and a bump node"""
        if "Normal" in PbrNodeTree.nodes.keys():
            "There is already a normal map. We currently override it"
            return
        PbrNodeTree.add_image_texture(image, "Bump", (-1200, -600))
        bumpMap = PbrNodeTree.nodes.new("ShaderNodeBump")
        bumpMap.name = "Bump Map"
        bumpMap.location = (-900, -600)
        PbrNodeTree.add_link("Bump", 0, "Bump Map", 2)
        PbrNodeTree.add_link("Bump Map", 0, "Principled BSDF", 17)

    def add_height(image):
        """add a displacement map and a math node to adjust the strength"""
        PbrNodeTree.add_image_texture(image, "Displacement", (-1200, -900))

        mix_shader = PbrNodeTree.nodes.new("ShaderNodeMath")
        mix_shader.location = (-900, -900)
        name = "Disp Offset"
        mix_shader.name = name
        mix_shader.label = name
        mix_shader.operation = 'ADD'
        
        mix_shader = PbrNodeTree.nodes.new("ShaderNodeMath")
        mix_shader.location = (-700, -900)
        name = "Disp Intensity"
        mix_shader.name = name
        mix_shader.label = name
        mix_shader.operation = 'MULTIPLY'

        PbrNodeTree.ntree.outputs.new("NodeSocketFloat", "Displacement")
        PbrNodeTree.add_link("Displacement", 0, "Disp Offset", 0)
        PbrNodeTree.add_link("Disp Offset", 0, "Disp Intensity", 0)
        PbrNodeTree.add_link("Disp Intensity", 0, "Group Output", 1)
        group = PbrNodeTree.base_tree.nodes["Group"]
        material_output = PbrNodeTree.base_tree.nodes["Material Output"]
        PbrNodeTree.base_tree.links.new(group.outputs[1], material_output.inputs[2])     

    def mix_col_ao():
        """add a mix RGB shader between the color and AO maps"""
        mix_shader = PbrNodeTree.nodes.new("ShaderNodeMixRGB")
        
        mix_shader.location = (-500, 450)
        mix_shader.blend_type = 'MULTIPLY'

        name = "AO Intensity"
        mix_shader.name = name
        mix_shader.label = name

        PbrNodeTree.add_link("Bright/Contrast", 0, name, 1)
        PbrNodeTree.add_link("Ambient Occlusion", 0, name, 2)
        PbrNodeTree.add_link(name, 0, "Principled BSDF", 0)
        
    def add_tex_coord():
        """add a texture coordinate and mapping nodes"""
        text_coord = PbrNodeTree.nodes.new("ShaderNodeTexCoord")
        text_coord.location = (-2200, 0)
        
        mapping = PbrNodeTree.nodes.new("ShaderNodeMapping")
        mapping.location = (-2000, 0)
        
        # Create a Scale group to control the scale from the node group
        scale_tree = bpy.data.node_groups.new(type="ShaderNodeTree", name="Scale")
        scale_nodes = scale_tree.nodes

        scale_group = PbrNodeTree.ntree.nodes.new("ShaderNodeGroup")
        scale_group.node_tree = scale_tree
        scale_group.name = "Scale"
        scale_group.location = (-1500, 0)
        scale_tree.inputs.new("NodeSocketVector", "Vector")
        scale_tree.inputs.new("NodeSocketFloat", "Scale")
        scale_tree.outputs.new("NodeSocketVector", "Vector")
        
        input_node = scale_nodes.new("NodeGroupInput")
        input_node.location = (-300, 0)
        output_node = scale_nodes.new("NodeGroupOutput")
        output_node.location = (300, 0)
        mix_node = scale_nodes.new("ShaderNodeMixRGB")
        mix_node.inputs[0].default_value = 1
        mix_node.blend_type = 'MULTIPLY'
        
        scale_tree.links.new(input_node.outputs[0], mix_node.inputs[1])
        scale_tree.links.new(input_node.outputs[1], mix_node.inputs[2])
        scale_tree.links.new(mix_node.outputs[0], output_node.inputs[0])
        
        PbrNodeTree.add_link("Mapping", 0, "Scale", 0)
        PbrNodeTree.add_link("Texture Coordinate", int(bpy.context.scene.mft_props.mapping), "Mapping", 0)

    def add_link(nodeName1, outputId, nodeName2, inputId):
        """add a link between the two existing nodes"""
        node1 = PbrNodeTree.nodes[nodeName1]
        node2 = PbrNodeTree.nodes[nodeName2]
        PbrNodeTree.ntree.links.new(node1.outputs[outputId], node2.inputs[inputId])
        
    def set_single_controller(type, name, node_name, node_input, default_value, min_value, max_value, update):
        """add a controller in the node group"""
        group = bpy.context.active_object.active_material.node_tree.nodes["Group"]
        if node_name not in group.node_tree.nodes.keys():
            "there is no such node in the tree (the corresponding map has not been loaded)"
            return
        
        if not update:
            # create the inputs
            PbrNodeTree.ntree.inputs.new(type, name)
            PbrNodeTree.add_link("Group Input", PbrNodeTree.input_counter, node_name, node_input)
            PbrNodeTree.ntree.inputs[name].default_value = default_value
            PbrNodeTree.ntree.inputs[name].min_value = min_value
            PbrNodeTree.ntree.inputs[name].max_value = max_value
            PbrNodeTree.input_counter += 1
            
        group.inputs[name].default_value = default_value
                
    def set_controllers(update=False):
        """add all the inputs in the node group to control the material settings"""
        PbrNodeTree.input_counter = 0
        
        PbrNodeTree.set_single_controller("NodeSocketFloat", "Scale", "Scale", 1, 1, 0.2, 5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Saturation", "Hue Saturation Value", 1, 1, 0, 1.5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Brightness", "Hue Saturation Value", 2, 1, 0, 2, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Contrast", "Bright/Contrast", 2, 0, -0.1, 0.1, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "AO Power", "AO Power", 1, 1, 0, 5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "AO Intensity", "AO Intensity", 0, 1, 0, 1, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Reflection Offset", "Reflection Offset", 1, 0, -0.5, 0.5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Roughness Offset", "Roughness Offset", 1, 0, -0.5, 0.5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Glossiness Offset", "Glossiness Offset", 1, 0, -0.5, 0.5, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Normal Intensity", "Normal Map", 0, 1, 0, 2, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Bump Intensity", "Bump Intensity", 1, 0.5, 0, 2, update)
        PbrNodeTree.set_single_controller("NodeSocketFloatFactor", "Displacement Intensity", "Disp Intensity", 1, 0.3, 0, 2, update)
        
    @staticmethod
    def fill_tree():
        """create the nodes according to the available maps"""
        actions = {
            "AO": PbrNodeTree.add_ao,
            "Col": PbrNodeTree.add_color,
            "Dis": PbrNodeTree.add_height,
            "Nor": PbrNodeTree.add_normal,
            "Rou": PbrNodeTree.add_roughness,
            "Glo": PbrNodeTree.add_glossiness,
            "Met": PbrNodeTree.add_metallic,
            "Spec": PbrNodeTree.add_specular,
            "Bum": PbrNodeTree.add_bump
        }
        # For each image in the dictionnary, we call a method to add a map in the node tree.
        # We first sort the dictionnary so that we know in wich order the methods might be called:
        # In particular: Bump, then Displacement, then Normal, and Color after AO
        for extension, image in OrderedDict(sorted(PbrNodeTree.IMAGES.items())).items():
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
        row.operator("mft.import_textures", text="Load textures", icon="FILESEL")
        
        box = layout.box()
        box.label("Create empty node tree", icon="NODETREE")
        split = box.split()
        col = split.column()
        col.scale_y = 2
        col.operator("mft.new_pbr_mr_material", text="Metalness / Roughness")
        col = split.column()
        col.scale_y = 2
        col.operator("mft.new_pbr_sg_material", text="Specular / Glossiness")
    
        if not (context.active_object.active_material is None or context.active_object.active_material.node_tree is None):
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
            col.label("Projection:")
            col.prop(mft_props, 'projection', text="")
            
            # Reset
            row = layout.row()
            row.scale_y = 2
            row.operator("mft.reset_group", text="Reset Material", icon="FILE_REFRESH")
        
        # Delete unused data
        row = layout.row()
        row.operator("mft.delete_unused_data", text="Delete unused data", icon="OUTLINER_DATA_EMPTY")
        
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
        material_name = self.get_material_name()
        new_material = bpy.data.materials.new(name=material_name)
        new_material.use_nodes = True
        bpy.context.active_object.active_material = new_material

        # Retrieve the images and their extension (type)
        images = self.sort_files(context, self.files, self.directory)                
        
        # Set the color map property (Diffuse or Albedo) if there is only one color map
        self.set_color_map(images)
        
        # Fill the node tree
        PbrNodeTree.init(material_name)
        PbrNodeTree.IMAGES = images
        PbrNodeTree.fill_tree()
        PbrNodeTree.add_controllers()
        
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
            'metallic_suffixes': 'Met',
            'specular_suffixes': 'Spec'
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
    
    
class CreateEmptyMrMaterial(Operator):
    """Create a PBR node tree with Metallic/Roughness maps without images"""
    bl_idname = "mft.new_pbr_mr_material"
    bl_label = "Create a PBR material with Metallic/Roughness maps without images"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create a new material
        new_material = bpy.data.materials.new(name="PBR Material")
        new_material.use_nodes = True
        bpy.context.active_object.active_material = new_material
        
        # Fill the node tree
        PbrNodeTree.init("PBR Material")
        
        PbrNodeTree.add_ao(None)
        PbrNodeTree.add_color(None)
        PbrNodeTree.add_height(None)
        PbrNodeTree.add_normal(None)
        PbrNodeTree.add_roughness(None)
        PbrNodeTree.add_metallic(None)
        
        PbrNodeTree.set_controllers()
    
        return {'FINISHED'}
    

class CreateEmptySgMaterial(Operator):
    """Create a PBR node tree with Specular/Glossiness maps without images"""
    bl_idname = "mft.new_pbr_sg_material"
    bl_label = "Create a PBR material with Specular/Glossiness maps without images"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create a new material
        new_material = bpy.data.materials.new(name="PBR Material")
        new_material.use_nodes = True
        bpy.context.active_object.active_material = new_material
        
        # Fill the node tree
        PbrNodeTree.init("PBR Material")
        
        PbrNodeTree.add_ao(None)
        PbrNodeTree.add_color(None)
        PbrNodeTree.add_height(None)
        PbrNodeTree.add_normal(None)
        PbrNodeTree.add_specular(None)
        PbrNodeTree.add_glossiness(None)
        
        PbrNodeTree.set_controllers()
        
        return {'FINISHED'}
    
    
class ResetNodeGroup(Operator):
    """Reset the node group inputs to their default values"""
    bl_idname = "mft.reset_group"
    bl_label = "Reset the Node Group"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            group = context.active_object.active_material.node_tree.nodes["Group"]
        except KeyError:
            # No group in the node tree
            return {'FINISHED'}
        
        PbrNodeTree.set_controllers(update=True)
    
        return {'FINISHED'}
    
    
class DeleteUnusedData(Operator):
    """Delete the mesh, material, texture and image data blocks that are unused"""
    bl_idname = "mft.delete_unused_data"
    bl_label = "Delete unused data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)

        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)

        for block in bpy.data.textures:
            if block.users == 0:
                bpy.data.textures.remove(block)

        for block in bpy.data.images:
            if block.users == 0:
                bpy.data.images.remove(block)
    
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
    specular_suffixes = StringProperty(name="Specular")
    
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
            layout.prop(self, "specular_sufixes")

    @staticmethod
    def init():
        """set the default values for the file suffixes"""
        prefs = bpy.context.user_preferences.addons['pbr_material_from_textures'].preferences
        prefs["diffuse_suffixes"] = "Dif;Diffuse;BaseColor;Color;COL"
        prefs["albedo_suffixes"] = "Alb;Albedo"
        prefs["ao_suffixes"] = "AO;Occlusion"
        prefs["roughness_suffixes"] = "Rou;Roughness"
        prefs["glossiness_suffixes"] = "Gloss;Glossiness;GLOSS"
        prefs["normal_suffixes"] = "Nor;Normal;NRM"
        prefs["bump_suffixes"] = "Bump"
        prefs["height_suffixes"] = "Dis;Displacement;Height;DISP"
        prefs["metallic_suffixes"] = "Met;Metallic;METALNESS"
        prefs["specular_suffixes"] = "REFL"


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
    