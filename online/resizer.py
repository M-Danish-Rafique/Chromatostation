from PIL import Image

img = Image.open("D:\Education\.NET\Project\Software\online\Resources\Icons\Audit Trail.png")

target_height = 55
ratio = target_height / img.height
new_width = int(img.width * ratio)

img = img.resize((new_width, target_height), Image.NEAREST)
img.save("D:\Education\.NET\Project\Software\online\Resources\Icons\Audit Trailed.png")
