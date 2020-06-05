# Python-SlideShow

Simple slideshow written in pyhton3 with a buffer that allow to preload images for a smoother transition.
  
  Some of the features are:
  
* Randomize order
* Set custom time between images
* Loop the images
* Select a folder for the images to show (if not, the current folder will be used)
* Find option for showing only the images that contain certain word in the filename

The buffer

The buffer will preload images in advance in for a smoother transition, especially if the files are big

It will load X following images and X previous images. The default size of the buffer is 3 in both directions, which mean that 6 images will be loaded in memory at the same time

## Requirements

```markdown
Python3
Pillow 'pip install pillow' (7.0 or greater)
```

## Default Settings

* Time: 5 seconds
* Loop: No
* Path: Current working directory
* Random: No
* Filter images: Show all

## Keyboard Controls

```markdown
    <Escape> <q>                Exit
    <space>                     Pause/Unpause
    <Return> <Right> <Down>     Next image
    <Left>   <Up>               Previous image
```

## Help

```markdown
  -h, --help            show this help message and exit
  -r, --random          The images will be displayed in random order
  -t TIME, --time TIME  It defines the time it will take to slide an image in
                        seconds. The default time is 5 seconds
  -p PATH, --path PATH  the path to the folder to show in the slideshow. If no
                        path is presented, the current folder will be
                        displayed
  -l, --loop            Once reached the last image, start again from the
                        beginning
  -f FIND, --find FIND  Show only images that contain certain word in their
                        filename
  --cache CACHE         It allow you to modify how many images are loaded in
                        advance, this is specially useful when working with
                        big images that take some time to load and resize. The
                        default value is 3
  -v, --verbosity       (-v) Show the name of the image currently being
                        displayed on the console. (-vv) Show what images are
                        being loaded and deleted
```

## Examples

```markdown
    python3 slideshow.py -r
        This command will show all the images in the current folder with a random order

    python3 slideshow.py -t 3 -l
        This command will show all the images in the current folder with 3 seconds between them (-t 3) and once it reaches the last image it will start from the beginning (-l)

    python3 slideshow.py -p /home/user/pictures
        This command will show all the images in the folder "pictures" situated at "/home/user/pictures/"

    python3 slideshow.py -r -f moon
        This command will show all the images in the current folder that has "moon" in their name in a random order
```
