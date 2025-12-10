# Streamgrabbing script

For our project we try to find public traffic cameras on the web, hook into the stream and perform our own image processing. The process of reading a internet stream requires some additional processing steps like format conversion, buffering and sometimes others types of processing to achieve a reliable stream to perform the actual image processing on.

There is however a difference in code for the linux and windows version. Linux has very optimized piping which reduces the number of processing steps when using ffmpeg to do the conversions and piping it into openCV. This version is also more optimized.

Keep in mind that in this document we explain our thought process behind each processing step so take note that not all steps are done in linux. For this reason we do not refer to actual lines in the code and only sometimes provide code snippets. The general idea will only be explained.

## Getting video chunks

The program supports getting streams broadcast via HLS(HTTP live streaming) that utilize m3u8 files which store video chunks. OpenCv doesn't natively support hooking into these streams so a thid party is needed that handles the hooking into streams.

There are two options that were considered, either Gstreamer of FFMpeg. Gstreamer is beast of a software which is focussed on building pipelines. It could solve the issue of having cross platform quirks between linux and windows but it comes with massive overhead. Not to mention that the tool is fairly complex to use so ffmpeg mostly remained. 

FFMpeg is a swiss army knife of multimedia, it is the silent powertrain behind media worldwide. It is a tool that is very versitile and supports almost eveyr codec you can think of. It has a slightly worse pipeline approach which relies heavily on the underlying OS but it still has basic functionalily that remains very important. For our project FFMpeg is sufficient enough for our application since it has all capabilities needed of hooking into a stream and converting it to the right format to be used for further processing.

After having chosen FFMpeg, one thing still remained. FFMpeg needs the right flags set to build the pipeline. Here the general idea is the same and both linux and windows share the same flags. FFMpeg is a program that runs for the command line, it is configured using command line flags. 

`ffmpeg` execute ffmpeg
`-headers headers` passthrough of the HTTP headers used to circumvent protection (see below)
`-fflags nobuffer` Prevent ffmpeg from building a buffer in order to reduce latency, buffering can be handled internally by python
`-flags low_delay` Reduce latency even further by eliminating redundant steps inside the ffmpeg pipeline
`-i M3U8_URL` link to the m3u8 chunklist
`-vf "scale={WIDTH}:{HEIGHT}"` resizing filter (see below)
`-f rawvideo` output format set to raw, could've gone with a compressed format to improve pipeline performance but this would then tradeoff performance somehwere else because it introduces a redundant encoding and decoding step.
`-pix_fmt bgr24` format of the rawvideo data, openCV can read multiple formats, including bgr24 and the standard pixel format for your incomming stream is bgr24. Therefor bgr24 was only logical because this way extra processing isn't needed.
`-an` No audio, just to be safe
`-sn` No subtitles, just to be safe
`-` Output to the standard inout so that python can read the stream



There are also some differences between the two. Mainly options regaring timing and buffering, the following flags are added. 

### Windows

`-analyzeduration 1000000` Sets how long FFmpeg should analyze the input stream to detect codecs, streams, and formats. The value could be decreased but this value made sure the stream would load reliably
`-probesize 1000000` Increases how much data (in bytes) FFmpeg can probe before determining stream information. Increasing this helps FFmpeg correctly detect formats when headers are incomplete or streams start with noise. In the case of windows this was needed because it sometimes stuggled to reliably start the stream
`-fps_mode passthrough` Instructs FFmpeg to preserve the source frame rate as-is. No frame duplication or dropping is performed this was needed to implement a custom buffering system since the default resulted in very laggy streams.
`-bufsize 3M` This setting is a bit strange since a nobuffer flag was provided, this did however solve an issue where the custom buffering system would take very long to restabilize after getting a longer period of poor connection. The flag sets the encoder's rate-control buffer size.

### Linux

`-strict experimental` Allows the use of experimental or non-fully-standardized codec features. Required for certain codecs or profiles that FFmpeg considers unstable or still in development. This was used to perform comparisons between different codecs and file formats to find the best possible settings on linux. These settings where then used on windows too with some extra tweaks to fix the platform quirks.
`-analyzeduration 0` Linux had no issues with unreliable startup of the stream. This flag disables stream analysis time. This speeds up startup but risks incorrect stream detection if the input isn’t well-structured.
`-probesize 32` The linux version did not have issues with unreliable stream startup, reducing the provesize improved stream performance without sacrificing reliability
`-vsync 0` Disables video synchronization this way FFmpeg outputs frames exactly as they come without duplicating or dropping. We use it to achieve strict frame-for-frame matching which improves speed for openCV. 
`-copytb 0` Controls how timestamps are copied from the input. With `0`, FFmpeg generates new timestamps rather than copying input timebase values, in our case giving cleaner or more consistent output timing.
`-r 25` Forces the output frame rate to 25 fps. FFmpeg will duplicate or drop frames as needed to match this exact rate. Combined with the other setting this game a very smooth experience to perform image processing on.

## Circumventing protection

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
