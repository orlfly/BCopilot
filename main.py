import bpy
import bpy.props
import json

from utilities import *

bl_info = {
    "name": "Blender Copilot",
    "blender": (2, 82, 0),
    "category": "Object",
    "author": "Pramish Paudel",
    "version": (1, 0, 1),
    "location": "3D View > UI > Copilot",
    "description": "Automate Blender using OpenAI's GPT to perform various tasks.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}


system_prompt = """You are an assistant made for the purposes of helping the user with Blender, the 3D software. 
- Respond with your answers in markdown (```) as shown in example. 
- Preferably import entire modules instead of bits. 
- Do not perform destructive operations on the meshes. 
- Do not use cap_ends. Do not do more than what is asked (setting up render settings, adding cameras, etc)
- Do not respond with anything that is not Python code.
- Use alpha channel for color ex: (1,0,0,1). 
- Check if the material exits before applying color. If not material, create new.
- If asked to animate, use keyframe animation for animation. 

Example:

user: create 10 cubes in random locations from -10 to 10
assistant:
```
import bpy
import random

# Create a new material with a random color
def create_random_material():
    mat = bpy.data.materials.new(name="RandomColor")
    mat.diffuse_color = (random.uniform(0,1), random.uniform(0,1), random.uniform(0,1), 1) # alpha channel is required
    return mat

bpy.ops.mesh.primitive_cube_add()

#how many cubes you want to add
count = 10

for c in range(0,count):
    x = random.randint(-10,10)
    y = random.randint(-10,10)
    z = random.randint(-10,10)
    bpy.ops.mesh.primitive_cube_add(location=(x,y,z))
    cube = bpy.context.active_object
    # Assign a random material to the cube
    cube.data.materials.append(create_random_material())

```"""


class GPT4_OT_DeleteMessage(bpy.types.Operator):
    bl_idname = "gpt4.delete_message"
    bl_label = "Delete Message"
    bl_options = {'REGISTER', 'UNDO'}

    message_index: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.gpt4_chat_history.remove(self.message_index)
        return {'FINISHED'}


class GPT4_OT_ShowCode(bpy.types.Operator):
    bl_idname = "gpt4.show_code"
    bl_label = "Show Code"
    bl_options = {'REGISTER', 'UNDO'}

    code: bpy.props.StringProperty(
        name="Code",
        description="The generated code",
        default="",
    )

    def execute(self, context):
        text_name = "GPT4_Generated_Code.py"
        text = bpy.data.texts.get(text_name)
        if text is None:
            text = bpy.data.texts.new(text_name)

        text.clear()
        text.write(self.code)

        text_editor_area = None
        for area in context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                text_editor_area = area
                break

        if text_editor_area is None:
            text_editor_area = split_area_to_text_editor(context)

        text_editor_area.spaces.active.text = text

        return {'FINISHED'}


class GPT4_PT_Panel(bpy.types.Panel):
    bl_label = "Copilot"
    bl_idname = "blender_copilot_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GPT Copilot'

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        column.label(text="Chat history:")
        box = column.box()
        for index, message in enumerate(context.scene.gpt4_chat_history):
            if message.type == 'assistant':
                row = box.row()
                row.label(text="Assistant: ")
                show_code_op = row.operator("gpt4.show_code", text="Show Code")
                show_code_op.code = message.content
                delete_message_op = row.operator("gpt4.delete_message", text="", icon="TRASH", emboss=False)
                delete_message_op.message_index = index
            else:
                row = box.row()
                row.label(text=f"User: {message.content}")
                delete_message_op = row.operator("gpt4.delete_message", text="", icon="TRASH", emboss=False)
                delete_message_op.message_index = index

        column.separator()

        column.label(text="GPT Model:")
        column.prop(context.scene, "gpt4_model", text="")

        column.label(text="Enter your message:")
        column.prop(context.scene, "gpt4_chat_input", text="")
        button_label = "Please wait...(this might take some time)" if context.scene.gpt4_button_pressed else "Execute"
        row = column.row(align=True)
        row.operator("gpt4.send_message", text=button_label)
        row.operator("gpt4.clear_chat", text="Clear Chat")

        column.separator()


class GPT4_OT_ClearChat(bpy.types.Operator):
    bl_idname = "gpt4.clear_chat"
    bl_label = "Clear Chat"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.gpt4_chat_history.clear()
        return {'FINISHED'}


class GPT4_OT_Execute(bpy.types.Operator):
    bl_idname = "gpt4.send_message"
    bl_label = "Send Message"
    bl_options = {'REGISTER', 'UNDO'}

    natural_language_input: bpy.props.StringProperty(
        name="Command",
        description="Enter the natural language command",
        default="",
    )

    def execute(self, context):
        global system_prompt

        context.scene.gpt4_button_pressed = True
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        ## add context to system prompt
        # Get the minimal scene data
        scene_data = {
            "objects": []
        }

        for obj in bpy.context.scene.objects:
            scene_data["objects"].append({
                "name": obj.name,
                "type": obj.type,
                # "location": list(obj.location),
                # "rotation_euler": list(obj.rotation_euler),
                # "scale": list(obj.scale),
            })

        if len(scene_data["objects"]) == 0: scene_data = None
        # if scene_data:
        #     system_prompt = system_prompt + """Below is the minimal scene context.\n""" + json.dumps(scene_data)

        blender_code = generate_blender_code(context.scene.gpt4_chat_input, context.scene.gpt4_chat_history, context,
                                             system_prompt)

        message = context.scene.gpt4_chat_history.add()
        message.type = 'user'
        message.content = context.scene.gpt4_chat_input

        # Clear the chat input field
        context.scene.gpt4_chat_input = ""

        if blender_code:
            message = context.scene.gpt4_chat_history.add()
            message.type = 'assistant'
            message.content = blender_code

            global_namespace = globals().copy()

        try:
            exec(blender_code, global_namespace)
        except Exception as e:
            self.report({'ERROR'}, f"Error executing generated code: {e}")
            context.scene.gpt4_button_pressed = False
            return {'CANCELLED'}

        context.scene.gpt4_button_pressed = False
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(GPT4_OT_Execute.bl_idname)


class GPT4AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__


def register():
    bpy.utils.register_class(GPT4AddonPreferences)
    bpy.utils.register_class(GPT4_OT_Execute)
    bpy.utils.register_class(GPT4_PT_Panel)
    bpy.utils.register_class(GPT4_OT_ClearChat)
    bpy.utils.register_class(GPT4_OT_ShowCode)
    bpy.utils.register_class(GPT4_OT_DeleteMessage)

    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    init_props()


def unregister():
    bpy.utils.unregister_class(GPT4AddonPreferences)
    bpy.utils.unregister_class(GPT4_OT_Execute)
    bpy.utils.unregister_class(GPT4_PT_Panel)
    bpy.utils.unregister_class(GPT4_OT_ClearChat)
    bpy.utils.unregister_class(GPT4_OT_ShowCode)
    bpy.utils.unregister_class(GPT4_OT_DeleteMessage)

    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    clear_props()


if __name__ == "__main__":
    register()
