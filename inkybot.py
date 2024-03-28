#!/usr/bin/env python3

import sys, os, random, time, signal
import numpy as np
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
from inky.inky_uc8159 import Inky


class Inkybot:

    # FIXME: a bunch of this needs to be parameterized

    palette = [
        (0, 0, 0),        # black
        (255, 255, 255),  # white
        (0, 255, 0),      # green
        (0, 0, 255),      # blue
        (255, 0, 0),      # red
        (255, 255, 0),    # yellow
        (255, 140, 0),    # orange
        (255, 255, 255)   # white again???
    ]

    font_size = 60
    picpath = '/srv/inkybot/pictures'
    saturation = 0.7

    exiting = False
    skip_img = False


    BUTTONS = [5,6,16,24]
    LABELS  = ['A', 'B', 'C', 'D']
    
    inky = Inky()

    def __init__(self):
        self.font = ImageFont.truetype("fonts/3270NerdFontMono-Regular.ttf", size=self.font_size)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        for pin in self.BUTTONS:
            GPIO.add_event_detect(pin, GPIO.FALLING, self.handle_button, bouncetime=250)


    def color_similarity(self, color1, color2):
        return np.sqrt(np.sum((np.array(color1) - np.array(color2)) ** 2))

#    def quantize_image(self, image, reference_palette, similarity_threshold):
#        pixels = image.getdata()
#        new_image = Image.new(image.mode, image.size)
#
#        # Quantize the image colors only if they're within the similarity range to the reference palette
#        for i, pixel in enumerate(pixels):
#            best_match = min(reference_palette, key=lambda ref_color: color_similarity(ref_color, pixel))
#            if color_similarity(best_match, pixel) <= similarity_threshold:
#                new_image.putpixel((i % image.width, i // image.width), best_match)
#            else:
#                new_image.putpixel((i % image.width, i // image.width), pixel)
#
#        return new_image


    def least_similar_color(self, color, palette):
        return max(self.palette, key=lambda ref_color: self.color_similarity(ref_color, color))

    def average_outer_perimeter_color(self,image):
        # Get image dimensions
        width, height = image.size
        
        # Extract the outer 1-pixel perimeter
        outer_perimeter_pixels = []
        for x in range(width):
            outer_perimeter_pixels.append(image.getpixel((x, 0)))                    # Top row
            outer_perimeter_pixels.append(image.getpixel((x, height - 1)))          # Bottom row
        for y in range(1, height - 1):
            outer_perimeter_pixels.append(image.getpixel((0, y)))                   # Left column
            outer_perimeter_pixels.append(image.getpixel((width - 1, y)))           # Right column

        # Calculate average color
        total_pixels = len(outer_perimeter_pixels)
        total_red = sum(pixel[0] for pixel in outer_perimeter_pixels)
        total_green = sum(pixel[1] for pixel in outer_perimeter_pixels)
        total_blue = sum(pixel[2] for pixel in outer_perimeter_pixels)

        average_red = total_red // total_pixels
        average_green = total_green // total_pixels
        average_blue = total_blue // total_pixels

        return (average_red, average_green, average_blue)

    def resize_with_letterbox(self, image, resolution, letterbox_color=(0, 0, 0)):
        target_width = resolution[0]
        target_height = resolution[1]
        
        # Get original width and height
        original_width, original_height = image.size
        
        # Calculate the aspect ratios
        original_aspect_ratio = original_width / original_height
        target_aspect_ratio = target_width / target_height
      
        #print(image.size, resolution)
        #print(original_aspect_ratio, target_aspect_ratio)

        # Calculate resizing factors
        if original_aspect_ratio < target_aspect_ratio:
            # Image is narrower than target, resize based on height
            new_width = int(target_height * original_aspect_ratio)
            new_height = target_height
        else:
            # Image is taller than target, resize based on width
            new_width = target_width
            new_height = int(target_width / original_aspect_ratio)
        
        # Resize the image
        resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)
        
        # Create a new image with letterbox bars
        x_max = target_width - new_width
        if x_max // 2 > self.font_size:
            x = x_max // 2
        else:
            x = min(x_max, x_max // 2 + self.font_size)
        letterbox_image = Image.new(image.mode, (target_width, target_height), letterbox_color)
        #letterbox_image.paste(resized_image, ((target_width - new_width) // 2, (target_height - new_height) // 2))
        letterbox_image.paste(resized_image, (x, (target_height - new_height) // 2))
        
        return letterbox_image


    def handle_button(self,pin):
        label = self.LABELS[self.BUTTONS.index(pin)]
        print(f"Button pressed: {pin} {label}")
        if pin == 24:
            self.skip_img = True
            print("skipping!")

    def go(self):

        text = "test"
        text_objects = [
            {
                "text": "󰸋",
                #"text": "󰧸",
                "left": 10,
                "top": 49
            },
            {
                "text": "",
                #"text": "󰧸",
                "left": 10,
                "top": 161
            },
            {
                "text": "",
                #"text": "󰧸",
                "left": 10,
                "top": 273
            },
            {
                #"text": "󰧸",
                "text": "󱧾",
                "left": 10,
                "top": 385
            }
        ]
        imagelist = []

        while self.exiting is not True:
            self.skip_img = False
            target = time.time() + 60.0
            
            if len(imagelist) == 0:
                imagelist = os.listdir(self.picpath)
                random.shuffle(imagelist)

            fn = imagelist.pop()
            print(f"Displaying {fn}")

            image = Image.open(f"{self.picpath}/{fn}") # XXX FIXME: os join function instead

            resizedimage = self.resize_with_letterbox(
                    image,
                    self.inky.resolution,
                    self.average_outer_perimeter_color(image)
                    )

            draw = ImageDraw.Draw(resizedimage)
            c = self.least_similar_color(self.average_outer_perimeter_color(image), self.palette)
            c2 = self.least_similar_color(c, self.palette) # hahahahaha what am i thinking

            for t in text_objects:
                text_width, text_height = draw.textsize(t["text"], font=self.font)
                dy = int(text_height / 2)
                for x in range(t["left"] - 1, t["left"] + 2, 1):
                    for y in range(t["top"] - 1 - dy, t["top"] + 2 - dy, 1):
                        draw.text((x,y), t["text"], fill=c, font=self.font)

                draw.text((t["left"],t["top"] - dy), t["text"], fill=c2, font=self.font)

            self.inky.set_image(resizedimage, saturation=self.saturation)
            self.inky.show()

            while time.time() < target and self.skip_img is False:
                time.sleep(0.1)

if __name__ == "__main__":
    inkybot = Inkybot()
    inkybot.go()

#inky = auto(ask_user=True, verbose=True)

# buttons:
# - hostap vs wpa_supplicant
# - next image
# - ??? mode picture vs. status?
# - ??? music play/pause/skip?

