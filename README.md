# Traffic monitor

This is a school project for Image Processing, a course part of Electronics-ICT on Hogeschool PXL. The goal is to use traditional image processing techniques to solve a problem of our liking\. That's why we decided to create a traffic monitor. The idea is simple: use any video stream of traffic and the program will give you two metrics: A congestion level(No traffic, Light traffic, Normal traffic , Heavy traffic, Congested ) and traffic speed(Traffic jam, Slow moving, Normal). These metrics go hand in hand but we decided to split them up so we will be able to detect anomalies.

Everything is done in python, the repository is therefor very minimal as most of the heavy lifting is done by libraries

## Usage

**Make sure you have python installed**

**Make sure you have a working install of ffmpeg which is added to your PATH variable**

**Install the right packages**

```shell
pip install matplotlib numpy opencv_python
```

**Set streaming source**

Open `streamgrab.py` or `streamgrab-win.py` and on the top of the file you should be able to find global variables. By default it is set to grab a stream from the belgian verkeerscentrum. You can change the url but be sure to edit the width and height too. In some cases you might also need to change the referer and origin too. This is done to circumvent protection measures that only allow the website to stream video. But in order to perform image recognition tasks these http headers can be changed, it should work in most cases.

After these variables are changed you can save and close the script

**Run script**

Depending on your OS you can run either streamgrab.py using `python screengrab.py` if you are on linux or `python screengrab-win.py` if you are on windows. 

For the image processing you need to run `python complete_script.py`



The two version behave slightly different since linux has better pipelines. Windows needs extra settings to properly buffer and pipe video.

## Documentation

Our decisions are documented, both the streamgrabbing and image processing. Documentation is split between these files

[Streamgrabbing code](docs/streamgrab.md)

[Image processing -- morphology](tests/morphologyComparison.md)

[Image processing -- blurs](tests/blurComparison.md)

The image processing documentation is also accompanied with separate tests that have their own python scripts. 

## Extra scripts

For quick viewing there are some scripts inside the `pipelines` folder that will use ffplay to quickly view a screen

`pipelines/launch-player.sh` linux script to launch a quick view of a specific source

`pipelines/launch-winplayer.bat` windows script to launch a quick view of a specific source

`pipelines/streamgrabber.sh` linux script mostly for testing, it is meant to be the command example that can be piped into a script.

It is generally not recommended to use these scripts but they are there for debugging reasons.
