bl_info = {  
 "name": "Material Fade Tools",  
 "author": "Bastian Ilso (bastianilso)",  
 "version": (0, 1),  
 "blender": (2, 7, 8),  
 "location": "Tools Panel -> Commotion",  
 "description": "Tools for creating fades and other effects on materials.",  
 "warning": "",
 "wiki_url": "",  
 "tracker_url": "https://github.com/bastianilso/blender-cycles-material-fade-in-out",  
 "category": "Material"}

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import IntProperty, PointerProperty

class UI:
    bl_category = 'Commotion'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context = 'objectmode'

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and len(ob.material_slots) > 0 and bpy.context.scene.render.engine == 'CYCLES'

class MaterialToolProperties(PropertyGroup):
    duration = IntProperty(
            name="Duration",
            description="Duration of the animation (in frames)",
            default=13,
            subtype="TIME",
            )
    offset = IntProperty(
        name="Offset",
        description="Offset between each object fade",
        min=0,
        default=0,
        )

class MaterialTools(UI,Panel):
    """Creates a material tool panel in the commotion tab"""
    bl_label = 'Material Tools'
    bl_idname = 'commotion_mat_tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.commotion_mat_tools, "duration")
        
        row = layout.row()
        row.prop(scene.commotion_mat_tools, "offset")
        if len(bpy.context.selected_objects) <= 1:
            row.enabled = False
            
        layout.operator("object.fade_in", icon="MATERIAL", text="Fade In")
        layout.operator("object.fade_out", icon="MATERIAL", text="Fade Out")

class NodeUtils:
    
    def create_fade_nodes(self, material):
        tree = material.node_tree
        trans_node = tree.nodes.new(type='ShaderNodeBsdfTransparent')
        mix_node = tree.nodes.new(type='ShaderNodeMixShader')
        
        inp = mix_node.inputs[1]
        out = trans_node.outputs['BSDF']
        tree.links.new(inp,out)

        if not tree.nodes['Material Output']:
            tree.nodes.new(type='ShaderNodeOutputMaterial')

        if tree.nodes['Material Output'].inputs['Surface'].links:
            inp = mix_node.inputs[2]
            out = tree.nodes['Material Output'].inputs['Surface'].links[0].from_node.outputs[0]
            tree.links.new(inp,out)
        
        inp = tree.nodes['Material Output'].inputs['Surface']
        out = mix_node.outputs['Shader']
        tree.links.new(inp,out)
        
        return mix_node
    
    def detect_fade_nodes(self, material):
        tree = material.node_tree
        
        if not tree.nodes['Material Output']:
            #print("No Material Output")
            return None 
        
        if not tree.nodes['Material Output'].inputs['Surface'].links:
            #print("Nothing linked with Material Output")
            return None
        
        from_node = tree.nodes['Material Output'].inputs['Surface'].links[0].from_node
        
        if not 'Mix Shader' in from_node.name:
            #print("Mix Shader not connected to Material Output")
            return None
        
        if not from_node.inputs[1].links:
            #print("Mix Shader has no inputs")
            return None
        
        if not 'Transparent BSDF' in from_node.inputs[1].links[0].from_node.name:
            #print("Mix Shader does not have Trans BSDF as first shader input")
            return None
        
        if from_node.inputs['Fac'].links:
            #print("Mix Shader's Fac is connected")
            return None        
        
        return from_node
    
    def fade_selected_objects(self, duration, offset, start_val, end_val):
        frame_restore = bpy.context.scene.frame_current
        for ob in bpy.context.selected_objects:
            
            for slot in ob.material_slots:
                if not slot.material:
                    continue
                
                # Make material unique if we are making object offset.
                if slot.material.users > 1 and offset > 0:
                    slot.material = slot.material.copy()
                
                slot.material.use_nodes = True
                
                mix_node = self.detect_fade_nodes(slot.material)
        
                if mix_node is None:
                    mix_node = self.create_fade_nodes(slot.material)

                # Delete old keyframes if any
                #mix_node.inputs['Fac'].id_data.animation_data_clear()
                
                # Animate Factor on Mix Shader
                mix_node.inputs['Fac'].default_value = start_val
                mix_node.inputs['Fac'].keyframe_insert(data_path="default_value", index=-1)
                bpy.context.scene.frame_current += duration
                mix_node.inputs['Fac'].default_value = end_val
                mix_node.inputs['Fac'].keyframe_insert(data_path="default_value", index=-1)
                bpy.context.scene.frame_current -= duration
            bpy.context.scene.frame_current += offset     
        
        bpy.context.scene.frame_current = frame_restore 
        

class FadeOut(Operator):
    """Fade out a material"""
    bl_idname = "object.fade_out"
    bl_label = "Fade Out"
    
    def execute(self,context):
        duration = bpy.context.scene.commotion_mat_tools.duration
        offset = bpy.context.scene.commotion_mat_tools.offset
        nodeutils = NodeUtils()
        nodeutils.fade_selected_objects(duration, offset, 1.0, 0.0)
        return {'FINISHED'}

class FadeIn(Operator):
    """Fade in a material"""
    bl_idname = "object.fade_in"
    bl_label = "Fade In"
    
    def execute(self,context):
        duration = bpy.context.scene.commotion_mat_tools.duration
        offset = bpy.context.scene.commotion_mat_tools.offset
        nodeutils = NodeUtils()
        nodeutils.fade_selected_objects(duration, offset, 0.0, 1.0)         
        return {'FINISHED'}


classes = (
    MaterialTools,
    FadeIn,
    FadeOut,
    MaterialToolProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.commotion_mat_tools = PointerProperty(type=MaterialToolProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
