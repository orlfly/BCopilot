import bpy
from openai import AzureOpenAI
import re

copenai = AzureOpenAI(
    azure_endpoint = 'https://kingsware3.openai.azure.com/',
    api_version = '2024-02-15-preview',
    api_key = 'fc78e8e6b2074403b240493e158ce840',
    )

def wrap_prompt(prompt):
    wrapped = f"""Can you please write Blender code for me that accomplishes the following task: \n
    {prompt}?Do not respond with anything that is not Python code. Do not provide explanations. Don't use bpy.context.active_object. Color requires an alpha channel ex: red = (1,0,0,1). """
    return wrapped


def init_props():
    bpy.types.Scene.gpt4_chat_history = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.gpt4_model = bpy.props.EnumProperty(
        name="GPT Model",
        description="Select the GPT model to use",
        items=[
            ("gpt4-turbo", "GPT4 Turbo (powerful, expensive)", "Use GPT-4"),
        ],
        default="gpt4-turbo",
    )
    bpy.types.Scene.gpt4_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Enter your message",
        default="",
    )
    bpy.types.Scene.gpt4_button_pressed = bpy.props.BoolProperty(default=False)
    bpy.types.PropertyGroup.type = bpy.props.StringProperty()
    bpy.types.PropertyGroup.content = bpy.props.StringProperty()


def clear_props():
    del bpy.types.Scene.gpt4_chat_history
    del bpy.types.Scene.gpt4_chat_input
    del bpy.types.Scene.gpt4_button_pressed


def generate_blender_code(prompt, chat_history, context, system_prompt):
    messages = [{"role": "system", "content": system_prompt}]
    for message in chat_history[-10:]:
        if message.type == "assistant":
            messages.append({"role": "assistant", "content": "```\n" + message.content + "\n```"})
        else:
            messages.append({"role": message.type.lower(), "content": message.content})

    # Add the current user message
    messages.append({"role": "user", "content": wrap_prompt(prompt)})

    response = copenai.chat.completions.create(
        model=context.scene.gpt4_model,
        messages=messages,
        stream=True,
        max_tokens=1500,
    )

    try:
        collected_events = []
        completion_text = ''
        # iterate through the stream of events
        for event in response:
            if len(event.choices) == 0:
                # skip
                continue
            if event.choices[0].delta.content is None:
                # skip
                continue
            collected_events.append(event)  # save the event response
            event_text = event.choices[0].delta.content
            completion_text += event_text  # append the text
            print(completion_text, flush=True, end='\r')
        completion_text = re.findall(r'```(.*?)```', completion_text, re.DOTALL)[0]
        completion_text = re.sub(r'^python', '', completion_text, flags=re.MULTILINE)

        return completion_text
    except IndexError:
        return None


def split_area_to_text_editor(context):
    area = context.area
    for region in area.regions:
        if region.type == 'WINDOW':
            override = {'area': area, 'region': region}
            bpy.ops.screen.area_split(override, direction='VERTICAL', factor=0.5)
            break

    new_area = context.screen.areas[-1]
    new_area.type = 'TEXT_EDITOR'
    return new_area
