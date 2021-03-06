#!/usr/bin/env python3

import sys
import os
import argparse
import random
import time
import re
import threading

import tkinter
from PIL import Image, ImageTk


class FileManager:
    extensions = {'jpeg', 'jpg', 'png'}
    files = []

    def __init__(self, args):
        self.path = args.path

    def getFiles(self):
        if self.path:
            os.chdir(self.path)
        
        with os.scandir() as entries:
            for entry in entries:
                if (not entry.is_dir()):
                    if (self.checkFileExtension(entry.name)):
                        self.files.append(entry.name)

    def checkFileExtension(self, file):
        extension = os.path.splitext(file)[1]
        if (extension.replace('.', '') in self.extensions):
            return True
        else:
            return False


class SlideShow:
    screen = {}
    currentPosition = 0
    pause = False
    slide_time = 5

    def __init__(self, imagesList, parameters):
        self.parameters = parameters
        self.imagesList = imagesList

        self.setDisplay()
        self.setKeyBindings()
        self.configuration()
                
        if len(self.imagesList) == 0:
            print('[-] No images could be found... Exiting')
            sys.exit(-1)
        if self.parameters.verbosity == 1:
            print('[+] Loaded %i images' % (len(self.imagesList)))

        self.imagesCache = ImagesCache(self.imageManager, self.imagesList, self.parameters)
        self.displayImage(self.imagesCache.getCurrentImage())

        self.updateTimer()
        self.root.mainloop()

    def setDisplay(self):
        self.root = tkinter.Tk()
        self.screen['width'] = self.root.winfo_screenwidth()
        self.screen['height'] = self.root.winfo_screenheight()

        self.imageManager = ImageManager(self.screen)

        self.root.overrideredirect(True)
        if sys.platform.startswith('darwin'):
            self.root.overrideredirect(False)

        self.root.geometry('%dx%d+%d+%d' % (self.screen['width'], self.screen['height'], 0, 0))
        self.root.focus_set()

        self.label = tkinter.Label(self.root, image = None, width = self.screen['width'], height = self.screen['height'])
        self.label.pack()
        self.label.configure(background = 'black', borderwidth = 0)

    def setKeyBindings(self):
        self.root.bind("<Escape>", self.exit)
        self.root.bind("<q>", self.exit)
        self.root.bind("<Return>", self.showNextImage)
        self.root.bind("<space>", self.togglePause)
        self.root.bind("<Right>", self.showNextImage)
        self.root.bind("<Left>", self.showPrevImage)
        self.root.bind("<Up>", self.showPrevImage)
        self.root.bind("<Down>", self.showNextImage)

    def configuration(self):
        if self.parameters.random:
            random.shuffle(self.imagesList)

        if self.parameters.filter:
            r = re.compile('.*%s.*' % (self.parameters.filter))
            self.imagesList = list(filter(r.match, self.imagesList))
        
        if self.parameters.time:
            self.slide_time = self.parameters.time

    def updateTimer(self):
        if not self.pause:
            if time.time() - self.lastTimeView >= self.slide_time:
                self.showNextImage()
                self.root.after(int(self.slide_time * 1000), self.updateTimer)
            else:
                nextTime = int((self.slide_time - (time.time() - self.lastTimeView)) * 1000) + 1
                if nextTime < 0:
                    nextTime = 0
                self.root.after(nextTime, self.updateTimer)

    def exit(self, e = None):
        self.root.destroy()

    def togglePause(self, e = None):
        self.pause = not self.pause
        if not self.pause:
            self.root.after(self.slide_time * 1000, self.updateTimer)

    def showNextImage(self, e = None):
        if not self.parameters.loop and self.currentPosition + 1 > len(self.imagesList) - 1:
            self.lastTimeView = time.time()
            return


        image = self.imagesCache.getNextImage()

        self.currentPosition += 1        
        if image:
            self.displayImage(image)

    def showPrevImage(self, e = None):
        if not self.parameters.loop and self.currentPosition - 1 < 0:
            self.lastTimeView = time.time()
            return

        image = self.imagesCache.getPreviousImage()
        self.currentPosition -= 1
        if image:
            self.displayImage(image)

    def displayImage(self, image):
        if self.parameters.verbosity == 1:
            print('Current Image: %s' % (image.name))

        self.label.configure(image = image.imageTk)
        self.label.image = image.imageTk
        self.lastTimeView = time.time()


class ImagesCache():
    cache = 3

    def __init__(self, imageManager, imagesList, parameters):
        self.imageManager = imageManager
        self.imagesList = imagesList
        
        if parameters.cache != None:
            print(parameters.cache)
            if parameters.cache < 1:
                print('[-] %s is not a valid cache size, using 1 instead' % (parameters.cache))
                self.cache = 1
            else:
                self.cache = parameters.cache
                
        self.verbosity = parameters.verbosity
        self.imagesListSize = len(self.imagesList)
        self.current_node = None
        self.start_node = None
        self.end_node = None

        self.loadFirst()
        self.e = threading.Event()
        self.updater = threading.Thread(target=self.updateImages, args=(self.e,), daemon=True)
        self.updater.start()

    def loadFirst(self):
        self.insert_start(self.imageManager.loadImage(self.imagesList[0]))

    def updateImages(self, e):
        while True:

            if self.verbosity == 2:
                print('Start: %s, Current %s, End: %s' % (self.start_node.position, self.current_node.position, self.end_node.position))
            next_preloaded = self.end_node.position - self.current_node.position
            if next_preloaded < self.cache:
                for _ in range(self.cache - next_preloaded):
                    if self.verbosity == 2:
                        print('\tloading end image %s: (%s -> %s)' % (self.end_node.position + 1, (self.end_node.position + 1) % self.imagesListSize, self.imagesList[(self.end_node.position + 1) % self.imagesListSize]))
                    self.insert_end(self.imageManager.loadImage(self.imagesList[(self.end_node.position + 1) % self.imagesListSize]))
            if next_preloaded > self.cache:
                for _ in range(next_preloaded - self.cache):
                    if self.verbosity == 2:
                        print('\tdelete end %s' % (self.end_node.position))
                    self.delete_end()

            previous_preloaded = self.current_node.position - self.start_node.position
            if previous_preloaded < self.cache:
                for _ in range(self.cache - previous_preloaded):
                    if self.verbosity == 2:
                        print('\tloading start image %s: (%s -> %s)' % (self.start_node.position -1, (self.start_node.position - 1) % self.imagesListSize, self.imagesList[(self.start_node.position - 1) % self.imagesListSize]))
                    self.insert_start(self.imageManager.loadImage(self.imagesList[(self.start_node.position - 1) % self.imagesListSize]))
            if previous_preloaded > self.cache:
                for _ in range(previous_preloaded - self.cache):
                    if self.verbosity == 2:
                        print('\tdelete start %s' % (self.start_node.position))
                    self.delete_start()

            e.wait()
            e.clear()

    def getCurrentImage(self):
        return self.current_node.image

    def getNextImage(self):
        self.e.set()
        if self.current_node.next:
            self.current_node = self.current_node.next
            image = self.current_node.image
            return image
        else:
            return None

    def getPreviousImage(self):
        self.e.set()
        if self.current_node.prev:
            self.current_node = self.current_node.prev
            image = self.current_node.image
            return image
        else:
            return None

    def insert_start(self, image):
        if self.start_node is None:
            self.start_node = ImageNode(image)
            self.start_node.position = 0
            self.end_node = self.start_node
            self.current_node = self.start_node

        else:
            new_node = ImageNode(image)
            new_node.position = self.start_node.position - 1
            new_node.next = self.start_node
            self.start_node.prev = new_node
            self.start_node = new_node

    def insert_end(self, image):
        if self.start_node is None:
            self.start_node = ImageNode(image)
            self.start_node.position = 0
            self.end_node = self.start_node
            self.current_node = self.start_node

        else:
            new_node = ImageNode(image)
            new_node.position = self.end_node.position + 1
            new_node.prev = self.end_node
            self.end_node.next = new_node
            self.end_node = new_node

    def delete_start(self):
        if self.start_node is None:
            return
        if self.start_node.next is None:
            self.start_node = None
            return

        self.start_node = self.start_node.next
        self.start_node.prev = None

    def delete_end(self):
        if self.end_node is None:
            return
        if self.end_node.prev is None:
            self.end_node = None

        self.end_node = self.end_node.prev
        self.end_node.next = None


class ImageNode():
    def __init__(self, image):
        self.image = image
        self.position = 0
        self.next = None
        self.prev = None


class ImageManager():
    def __init__(self, screen):
        self.width = screen['width']
        self.height = screen['height']

    def loadImage(self, filename):
        image = Image.open(filename)
        img_width, img_height = image.size

        if img_width != self.width or img_height != self.height:
            image = self.resizeImage(image)

        imageTk = ImageTk.PhotoImage(image)
        name = filename

        return MyImage(imageTk, name)

    def resizeImage(self, image):
        img_width, img_height = image.size

        ratio = min(self.width / img_width, self.height / img_height)
        img_width = int(img_width * ratio)
        img_height = int(img_height * ratio)
        image = image.resize((img_width, img_height), Image.ANTIALIAS)

        return image


class MyImage():
    def __init__(self, imageTk, name):
        self.imageTk = imageTk
        self.name = name


def parse_arguments():
    description = '''
    Simple slideshow written in pyhton with a buffer that allow to preload images for a smoother transition.
    This slideshow will allow form randomize the order of the images, change the time between images (in seconds) and some other features.
    All the images will be resized to full screen.

    Keyboard Controls:
        <Escape> <q>                Exit
        <space>                     Pause/Unpause
        <Return> <Right> <Down>     Next image
        <Left>   <Up>               Previous image
    '''
    epilog = '''

EXAMPLES:

    python3 slideshow.py -r
        This command will show all the images in the current folder with a random order
    
    python3 slideshow.py -t 3 -l
        This command will show all the images in the current folder with 3 seconds between them (-t 3) and once it reaches the last image it will start from the beginning (-l)

    python3 slideshow.py -p /home/user/pictures
        This command will show all the images in the folder "pictures" situated at "/home/user/pictures/"

    python3 slideshow.py -r -f moon
        This command will show all the images in the current folder that has "moon" in their name in a random order
    '''


    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter
        )
    parser.add_argument('-r', '--random', action='store_true', help='The images will be displayed in random order')
    parser.add_argument('-t', '--time', type=int, help='It defines the time it will take to slide an image in seconds. The default time is 5 seconds')
    parser.add_argument('-p', '--path', help='the path to the folder to show in the slideshow. If no path is presented, the current folder will be displayed')
    parser.add_argument('-l', '--loop', action='store_true', help='Once reached the last image, start again from the beginning')
    parser.add_argument('-f', '--filter', help='Show only images that contain certain word in their filename')
    parser.add_argument('--cache', type=int, help='It allow you to modify how many images are loaded in advance, this is specially useful when working with big images that take some time to load and resize. The default value is 3')
    parser.add_argument('-v', '--verbosity', action='count', help='(-v) Show the name of the image currently being dilsplayed on the console. (-vv) Show what images are being loaded and deleted')
    # parser.add_argument('-R', '--recursive', action='store_true', help='Display images in subdirectories too')
    # parser.add_argument('--depth', type=int, help='Max depth of subdirectories to look for when recursivity is on. Default depth is 3')

    args = parser.parse_args()
    return args

def main(args):
    fileManager = FileManager(args)
    fileManager.getFiles()
    SlideShow(fileManager.files, args)

if __name__ == "__main__":
    args = parse_arguments()
    main(args)