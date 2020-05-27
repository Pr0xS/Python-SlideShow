#!/usr/bin/env python3

import sys
import os
import argparse
import random
import time

import threading
import re

import tkinter
from PIL import Image, ImageTk

class FileManager:
    extensions = {'jpeg', 'jpg', 'png'}
    files = []

    def __init__(self, path, recursive = False, depth = 3):
        self.path = path
        self.recursive = recursive
        self. depth = depth

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

        self.imagesCache = ImagesCache(self.imageManager, self.imagesList)
        self.displayImage(self.imagesCache.getCurrentImage())

        self.updateTimer()
        self.root.mainloop()


    def setDisplay(self):
        self.root = tkinter.Tk()
        self.screen['width'] = self.root.winfo_screenwidth()
        self.screen['height'] = self.root.winfo_screenheight()

        self.imageManager = ImageManager(self.screen)

        self.root.overrideredirect(True)
        # To make it work on mac TODO PROPER FIX
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
        print(self.parameters)
        if self.parameters.random:
            random.shuffle(self.imagesList)

        if self.parameters.find:
            r = re.compile('.*%s.*' % (self.parameters.find))
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

    def showImage(self, filename):
        self.displayImage(filename)
        self.lastTimeView = time.time()


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

        imageTk = self.imagesCache.getNextImage()
        self.currentPosition += 1        
        if imageTk:
            self.displayImage(imageTk)

    def showPrevImage(self, e = None):
        if not self.parameters.loop and self.currentPosition - 1 < 0:
            self.lastTimeView = time.time()
            return

        imageTk = self.imagesCache.getPreviousImage()
        self.currentPosition -= 1
        if imageTk:
            self.displayImage(imageTk)


    def displayImage(self, imageTk):
        self.label.configure(image = imageTk)
        self.label.image = imageTk
        self.lastTimeView = time.time()

class ImagesCache():
    max = 5
    saved_next = 0
    seved_prev = 0

    def __init__(self, imageManager, imagesList):
        self.imageManager = imageManager
        self.imagesList = imagesList
        self.imagesListSize = len(self.imagesList)
        self.current_node = None
        self.start_node = None
        self.end_node = None
        self.loadFirst()
        self.e = threading.Event()
        self.updater = threading.Thread(target=self.updateImages, args=(self.e,), daemon=True)
        self.updater.start()

    def loadImages(self):
        for x in self.imagesList[:self.max]:
            self.insert_end(self.imageManager.loadImage(x))

        for x in self.imagesList[self.imagesListSize - self.max :]:
            self.insert_start(self.imageManager.loadImage(x))

    def loadFirst(self):
        self.insert_start(self.imageManager.loadImage(self.imagesList[0]))

    def updateImages(self, e):
        while True:
            print("Updating Images")
            while (self.end_node.position - self.current_node.position) < self.max:
                print("updateImages info: %s, %s, %s" % (self.end_node.position, self.end_node.position + 1, (self.end_node.position + 1) % self.imagesListSize))
                self.insert_end(self.imageManager.loadImage(self.imagesList[(self.end_node.position + 1) % self.imagesListSize]))

            while self.end_node.position - self.current_node.position > self.max:
                print('delete end')
                self.delete_end()

            while self.current_node.position - self.start_node.position < self.max:
                print("updateImages info: %s, %s, %s" % (self.start_node.position, self.start_node.position - 1, (self.start_node.position - 1) % self.imagesListSize))
                self.insert_start(self.imageManager.loadImage(self.imagesList[(self.start_node.position - 1) % self.imagesListSize]))

            while self.current_node.position - self.start_node.position > self.max:
                print('delete start')
                self.delete_start()

            e.wait()
            e.clear()

    def getCurrentImage(self):
        return self.current_node.imageTk

    def getNextImage(self):
        print('getNextImage')
        self.e.set()
        if self.current_node.next:
            self.current_node = self.current_node.next
            imageTk = self.current_node.imageTk
            return imageTk
        else:
            return None

    def getPreviousImage(self):
        print('getPreviousImage')
        self.e.set()
        if self.current_node.prev:
            self.current_node = self.current_node.prev
            imageTk = self.current_node.imageTk
            return imageTk
        else:
            return None

    def insert_start(self, imageTk):
        if self.start_node is None:
            self.start_node = ImageNode(imageTk)
            self.start_node.position = 0
            self.end_node = self.start_node
            self.current_node = self.start_node

        else:
            new_node = ImageNode(imageTk)
            new_node.position = self.start_node.position - 1
            new_node.next = self.start_node
            self.start_node.prev = new_node
            self.start_node = new_node

    def insert_end(self, imageTk):
        if self.start_node is None:
            self.start_node = ImageNode(imageTk)
            self.start_node.position = 0
            self.end_node = self.start_node
            self.current_node = self.start_node

        else:
            new_node = ImageNode(imageTk)
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


    def print(self):
        node = self.start_node
        while(node.next):
            print(node.imageTk)
            node = node.next

        print(node.imageTk)

class ImageNode():
    def __init__(self, imageTk):
        self.imageTk = imageTk
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

        return imageTk

    def resizeImage(self, image):
        img_width, img_height = image.size

        ratio = min(self.width / img_width, self.height / img_height)
        img_width = int(img_width * ratio)
        img_height = int(img_height * ratio)
        image = image.resize((img_width, img_height), Image.ANTIALIAS)

        return image

def parse_arguments():
    parser = argparse.ArgumentParser(description='Simple slideshow written in python')
    parser.add_argument('-r', '--random', action='store_true', help='The images will be displayed with random order')
    parser.add_argument('-t', '--time', type=int, help='It defines the time it will take to slide a image in seconds. The default time is 5 seconds')
    parser.add_argument('-p', '--path', help='the path to the folder to show in the slideshow. If no path is presented, the current folder will be displayed', default='.')
    parser.add_argument('-l', '--loop', action='store_true', help='Once reached the last image, start again from the begining')
    parser.add_argument('-f', '--find', help='Show only images that containg certaing word')
    # parser.add_argument('-R', '--recursive', action='store_true', help='Display images in subdirectories too')
    # parser.add_argument('--depth', type=int, help='Max depth of subdirectories to look for when recursivity is on. Default depth is 3')


    args = parser.parse_args()

    return args



def main(args):
    print(os.getcwd())
    fileManager = FileManager('')
    fileManager.getFiles()
    SlideShow(fileManager.files, args)

if __name__ == "__main__":
    args = parse_arguments()
    main(args)