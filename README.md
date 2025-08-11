# airMouse
Sticky fingers? Not to worry.

##
Control your mouse using hand gesture recognition and, of course, your webcam (only macOS for now).

## Installation
Clone this repository:

```bash
git clone https://github.com/niCodeLine/airMouse.git
```
And intall the requirements.

### Requirements
I've noticed that installations of modules and packages needed work better with lower versions of python.

The latest that had worked for me is 3.11.13, so to create a virtual environment is recomended. My favorite way is with ```pyenv```.
You can do it by doing:

### Virtual Environment
```bash
pyenv install 3.11.13
pyenv virtualenv 3.11.13 opencv-venv
```

where ```opencv-venv``` is just the name I chose. Name it as you like it better.

Then activate the environment and install the requirements:

```bash
pyenv activate opencv-venv
pip install -r requirements.txt
```

## Usage

Just run ```airMouse.py```. A little window will pop-up showing the cameras view with the hand recognition when a hand is detected.
If you dont want to have the window poping up, go to lines 180 and change:

```python
cam = True # show video of camera
demarcar = cam # show dots and lines of the hand recognition in the video
```

To ```False```.

### Functions

So, how do we use this?

We have:
- **Left Click**: Tap your thumb with your middle finger (the FU one).
- **Right Click**: Tap your thumb with your ring finger.
- **Drag**: Tap and hold your thumb and middle finger together while moving to desired position.
- **Scroll**: Tap and hold your thumb with your index finger, keep the other fingers up, and tilt your hand to scroll up or down.
- **Brightness**: Put your little, ring, and middle fingers down while changing the distance between your thumb and index finger.
- **Volume**: Put your ring and middle fingers down while changing the distance between your thumb and index finger.
- **Mission Control**: Move the cursor to the top right corner of the screen to open Mission Control (show all windows).
- **De-activate**: Show your fist closed to stop the recognition, while keeping the program running.
- **Re-activate**: Do a 2 or peace sign to re-activate the recognition.
- **Terminate**: Do an american 3 (watch Inglorious Basterds) with your fingers to terminate the program.