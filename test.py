from openai import AzureOpenAI

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

copenai = AzureOpenAI(
    azure_endpoint = 'https://kingsware3.openai.azure.com/',
    api_version = '2024-02-15-preview',
    api_key = 'fc78e8e6b2074403b240493e158ce840',
    )


messages = [{"role": "system", "content": system_prompt}]

# Add the current user message
messages.append({"role": "user", "content": "add a cube"})

response = copenai.chat.completions.create(
    model="gpt4-turbo",
    messages=messages,
    stream=True,
    max_tokens=1500,
)
completion_text = ''
for event in response:
    if len(event.choices) == 0:
        # skip
        continue
    if event.choices[0].delta.content is None:
        # skip
        continue
    event_text = event.choices[0].delta.content
    completion_text += event_text  # append the text

print("##########################################")
print(completion_text, flush=True, end='\r')