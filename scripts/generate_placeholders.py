import os
from PIL import Image, ImageDraw, ImageFont

# Simple script to generate placeholder PNGs for exercises
activities = [
    "walking", "light_jogging", "cycling", "swimming",
    "stretching", "yoga", "resistance_bands", "chair_exercises",
    "arm_raises", "leg_raises", "wall_pushups", "seated_marches",
    "balance_exercises", "cooldown_stretches"
]

output_dir = "c:/Users/hp/Desktop/AdpativHealth/mobile-app/assets/exercises"

# Create images
for activity in activities:
    # 400x400 image, pleasant background color
    img = Image.new('RGB', (400, 400), color=(224, 242, 254)) # light blue
    d = ImageDraw.Draw(img)
    
    # draw a simple icon-like circle
    d.ellipse([100, 100, 300, 300], fill=(37, 99, 235)) # primary blue
    
    # try to add text
    text = activity.replace("_", " ").title()
    # we can't easily center text without font, so keep it simple
    # let's just make it a colored placeholder with no text, to be super safe
    
    img.save(os.path.join(output_dir, f"{activity}.png"))

print("Created 14 placeholder images")
