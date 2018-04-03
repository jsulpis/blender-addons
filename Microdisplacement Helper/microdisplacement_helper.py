#----------------------------------------------------------
# File microdisplacement_helper.py
#----------------------------------------------------------

bl_info = {
    "name": "Microdisplacement Helper",
    "author": "Julien Sulpis",
    "location": "Properties > Material > Microdisplacement Helper ",
    "description": "Centralize tools for the microdisplacement feature",
    "wiki_url": "https://github.com/jsulpis/blender-addons",
    "category": "Material"
    }
    
import bpy

from bpy.props import BoolProperty

# The message to display in the panel
message = ""

# The links that has been removed and may be recreated
normal_links = []

#--------------------------------------------------------------------------------------------------------
# Functions
#--------------------------------------------------------------------------------------------------------
def toggle_links(ntree):
    """ Connect or disconnect all links from the normal source in the node tree """
    global message, normal_links
    
    # If there are node groups in the tree, we recursively process them
    for node in ntree.nodes:
        if node.type == 'GROUP':
            toggle_links(node.node_tree)
    
    if bpy.context.scene.use_microdisp:
        # Remove all links from the normal source
        for link in ntree.links:
            if link.from_node.type == 'NORMAL_MAP' or link.from_node.type == 'BUMP':
                normal_links.append((link.from_socket, link.to_socket))
                ntree.links.remove(link)
                
        message = "All normal inputs disconnected"
    else:
        # Make links from the normal source to all the shaders with a normal input
        for from_socket, to_socket in normal_links:
            ntree.links.new(from_socket, to_socket)
        message = "All normal inputs connected"
        
    
def toggle_microdisp(self, context):
    """Enable or disable the microdisplacement feature"""
    object = bpy.context.active_object
    mat = object.active_material
    ntree = mat.node_tree
    
    if self.use_microdisp:
        # Set the feature set
        mode = bpy.context.scene.cycles.feature_set
        bpy.context.scene.cycles.feature_set = 'EXPERIMENTAL'
        
        # Set the subsurf
        mat.cycles.displacement_method = 'TRUE' if self.use_microdisp else 'BUMP'
        
        if "Subsurf" not in object.modifiers.keys():
            bpy.ops.object.modifier_add(type='SUBSURF')
        object.cycles.use_adaptive_subdivision = True
        
        # Reinitialize the list of links
        normal_links = []
        
    else:
        bpy.context.scene.cycles.feature_set = 'SUPPORTED'
        mat.cycles.displacement_method = 'BUMP'
    
    toggle_links(ntree)
        
#--------------------------------------------------------------------------------------------------------
# Properties
#--------------------------------------------------------------------------------------------------------
bpy.types.Scene.use_microdisp = BoolProperty(
    name="Use microdisplacement feature",
    default=False,
    update=toggle_microdisp
)


#--------------------------------------------------------------------------------------------------------
# Panel
#--------------------------------------------------------------------------------------------------------
class MaterialPanel(bpy.types.Panel):
    """Create a Panel in the Material window"""
    bl_label = "Microdisplacement Helper"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES' and context.material is not None
    
    def draw(self, context):
        layout = self.layout
        
        ob = bpy.context.active_object
        scene = context.scene
        cscene = scene.cycles
        mat = context.material
        cmat = mat.cycles
        
        feature_set = cscene.feature_set

        layout.row().prop(scene, 'use_microdisp', text="Use Microdisplacement")
        layout.row().prop(cscene, 'feature_set', text="Feature Set")
        
        if feature_set == 'EXPERIMENTAL':
            layout.row().prop(cmat, 'displacement_method', text="Displacement")
        
        if message != "":
            layout.label(message)
        
        if "Subsurf" not in ob.modifiers.keys():
            return
        
        box = layout.box()
        box.label("Settings")
        
        box.row().prop(ob.modifiers["Subsurf"], 'subdivision_type', expand=True)
        
        split = box.split()
                
        col = split.column()
            
        sub = col.column(align=True)
        sub.label("Subsurf:")
        sub.prop(ob.modifiers["Subsurf"], 'levels', text="View")
            
        if feature_set == 'EXPERIMENTAL':
            sub.prop(ob.cycles, "use_adaptive_subdivision", text="Adaptive")
        
            col = split.column()

            sub = col.column(align=True)
            sub.label("Subdivision Rate:")
            sub.prop(cscene, "dicing_rate", text="Render")
            sub.prop(cscene, "preview_dicing_rate", text="Preview")
        else:
            sub.prop(ob.modifiers["Subsurf"], 'render_levels', text="Render")


#--------------------------------------------------------------------------------------------------------
# Register
#--------------------------------------------------------------------------------------------------------
def register():
    bpy.utils.register_class(MaterialPanel)


def unregister():
    bpy.utils.unregister_class(MaterialPanel)

if __name__ == "__main__":
    register()