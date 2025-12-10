# Streamgrabbing script

For our project we try to find public traffic cameras on the web, hook into the stream and perform our own image processing. The process of reading a internet stream requires some additional processing steps like format conversion, buffering and sometimes others types of processing to achieve a reliable stream to perform the actual image processing on.

There is however a difference in code for the linux and windows version. Linux has very optimized piping which reduces the number of processing steps when using ffmpeg to do the conversions and piping it into openCV. This version is also more optimized.

Keep in mind that in this document we explain our thought process behind each processing step so take note that not all steps are done in linux. For this reason we do not refer to actual lines in the code and only sometimes provide code snippets. The general idea will only be explained.

## Getting video chunks

### Circumventing protection

## Stream Format conversion

## Scaling

## (Windows) adaptive FPS

## (Windows) frame buffering & flushing

## OpenCV format conversion

OpenCV requires a numpy array while the stdin stream is currently receiving raw BGR data, a type conversion has to be done in order for OpenCv to be able to process the frames, 

```python
frame = np.frombuffer(raw_frame, dtype=np.uint8)
```



# Recap (windows)

The streamgrabbing process on windows starts by launching two threads aside from the main thread. It starts a thread that will launch an ffmpeg process that will make the connection to the stream and perform the first few file processing steps, it will convert everything to raw bytes that will be outputted to the output stream where another process can grab the frames.

Another thread is responsible for reading that stream and performing the queueing for the main rendering thread to read from. It also does the step of converting the raw stream to a numpy array and reshapring that array to the correct format.

The main thread will keep an eye on the buffer and perform tight timing in order to dynamically speed up or slow down playback in order for the background processes to fill up the buffer or to clear the buffer to make room for more frames. 

It performs processing on a frame per frame basis so when frames are skipped no procesisng is done on the frame.

# Recap (linux)

Linux is simpler in the aspect that it only has a main thread and ffmpeg thread. Windows needed an extra frame reader thread because windows piping doesn't handle buffering real well. Linux only need a seperate thread to open the stream using ffmpeg, converts it to raw video and directly outputs raw frames to the standard output stream. Here extra flas are provided to ffmpeg to handle timing, because piping is handled so much better we can fully trust the operating systems to handle the buffering.

The main thead will read these raw frames and convert them to numpy arrays, here all frames will have processing applied to them unless the expected frame size doesn't match, in that scenario it wil discard the frame because it assumed there was an error during transmission.

## 
