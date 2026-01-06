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

A lot of streaming sites want their streaming server to only be utilized by users using a browser. An automated system like this is generally unwanted. A lot of sites implement a very rudamentary check to see who is requesting the resource. It simply checks the refferer and sometimes origin of the request to see if it comes from their own site. There are other more complex methods but many sites implement this basic condition check before serving content.

Of course this poses an issue for our programming. If we try to play a HLS stream without circumventing the protection you will get something like this

![](media/No_Header_Error.JPG)

That is also one of the reasons we use ffmpeg, it is easy to pass custom HTTP headers, looking at the traffic camera we are using we can use developper tools to see what headers it expects. We simply copy that and put it in our python script. After that we can see that the video stream gets received.

![](media/correct_function_of_players.JPG)

## Stream Format conversion

This was briefly discussed already when breaking down the ffmpeg command, there are however a lot more options that were considered before settling on the current formats.

Rawvideo and bgr24 were chosen because they eliminate unnecessary decoding steps in Python. Rawvideo outputs uncompressed pixel data, meaning every frame arrives as a fixed-size block of bytes. This avoids having to decode video again in OpenCV or use a container format. It also guarantees predictable frame size (width × height × 3), which makes converting the incoming byte stream into a NumPy array straightforward.

bgr24 is used because OpenCV internally uses BGR byte ordering. If the output were RGB or YUV, OpenCV would need either a channel swap or a full color-space conversion. bgr24 directly matches what OpenCV expects, so it removes another unnecessary processing step.

HLS streams work by listing short MPEG-TS (.ts) video segments inside a .m3u8 chunklist. FFmpeg downloads these segments sequentially. Because MPEG-TS often contains H.264 with P-frames and B-frames, the decoder typically buffers frames for reordering. The flags used in the command are chosen to reduce both buffering and probing to bring latency down as much as possible.

Overall, rawvideo + bgr24 is the most direct and latency-minimal way to get decoded frames from FFmpeg into OpenCV. It maximizes performance at the cost of higher bandwidth between FFmpeg and the Python process, which is usually acceptable for local interprocess communication.

## Scaling

The scaling step is included to ensure that every frame delivered to OpenCV has a consistent and predictable resolution. HLS sources can vary in quality depending on network conditions or the variant playlist being served. By forcing a fixed width and height, the processing pipeline avoids situations where frames suddenly change size, which would break downstream algorithms that assume a stable input shape. Consistent dimensions also simplify buffer handling, since rawvideo output depends entirely on knowing the exact number of bytes per frame.

Another practical reason for scaling is performance. High-resolution HLS streams can be expensive to process in real time, especially if each frame is used for computer vision tasks like detection or tracking. Downscaling to a more manageable resolution reduces the computational load while still retaining enough detail for analysis. In many cases, a slightly lower resolution provides a good balance between clarity and speed.

The scaling step also allows you to define a resolution that matches the needs of the system rather than the source. Cameras may output at 1080p or higher, but your model or algorithm might be designed for 720p or a custom dimension. Performing the scaling in FFmpeg takes advantage of FFmpeg’s optimized pixel operations, which are faster and more reliable than resizing frames later inside Python.

The specific dimensions aren't important we opted for the user to be able to decide themselves what width and height they want to use.

Overall, including a scaling step ensures stable frame sizes, reduces processing overhead, and aligns the incoming stream with the requirements of the computer vision pipeline.

## (Windows) adaptive FPS

The built in buffers from windows aren't good, even after trying to force a framerate in ffmpeg, windows pipes were unable to keep up with the stream of data. Therefor a custom system had to be made that would just accept every data that would be comming through the windows pipe and keep track of how many frames have arrived. The program would then try to play the stream at a stable FPS, slowing down when it sees that there aren't many frames left in the buffer and speeding up when it sees that the buffer is getting full and frames will have to get dropped. This results in the stream being played back at 3 different speeds which can look very odd. For windows this does seem to be the quickest fix for the issue at hand. 

This does introduce a seperate thread that is responsible for populating this buffer with frames received from ffmpeg. Tweaking the framerates of these 3 playback speeds can yield better results, finding the optimal framerates for playback. There is still an issue where poor network connection can destabilize this system but the buffering paramets should ensure this time is at an absolute minimum.

```python
def get_adaptive_fps(buffer_size):
    """Adjust FPS based on buffer fullness"""
    if buffer_size < BUFFER_LOW:
        return MIN_FPS  # Buffer low - slow down playback
    elif buffer_size < BUFFER_OPTIMAL:
        return BASE_FPS  # Building buffer
    elif buffer_size > BUFFER_HIGH:
        return MAX_FPS  # Buffer high - speed up to drain excess
    else:
        return BASE_FPS + 2  # Optimal rangeopped. Read {frame_count} frames.")
```

## (Windows) frame buffering & flushing

This was the hardest to implement since it is a tweaking dance in order to get it right. Manual buffers have to be managed to be filled and emptied in a dynamic way which collaborates with the adaptive FPS methods to maintain a stable as possible framerate.

The buffering and flushing logic exists to compensate for the way data arrives from FFmpeg. Because the stream is being read as raw bytes, the pipe does not align its reads to exact frame boundaries. A single `stdout.read()` call may return part of a frame, multiple frames, or even an uneven slice that spans across frame edges. The internal `buffer` variable acts as a temporary holding area so that incomplete data can accumulate until there is enough to assemble a full frame. Once a complete frame’s worth of bytes (`frame_size`) is available, it is extracted and processed while the leftover bytes remain in the buffer to be combined with the next chunk read from the pipe.

Reading data in larger chunks also helps reduce overhead on platforms like Windows, where many small pipe reads can become a bottleneck. By using `CHUNK_SIZE = frame_size * 6`, the code retrieves multiple frames’ worth of data in one read operation, which smooths out I/O performance and prevents the decoder from starving the processing loop.

The queue serves as a lightweight frame buffer between the reader thread and the display/processing loop. Frames are timestamped on arrival, allowing you to track latency or implement adaptive playback logic. If the queue grows too large, older frames can be dropped to avoid latency buildup. This is important because real-time processing favors fresher frames over perfect completeness.

In situations where frames arrive faster than they can be displayed, the queue naturally grows. Conversely, if the stream experiences network delays or slow segment delivery, the queue shrinks. The system uses adaptive FPS control to react to buffer size fluctuations. This helps prevent visual stuttering and gives the main loop time to catch up or slow down accordingly.

This approach of buffering, chunked reading, and controlled flushing ensures that even though the incoming data is a continuous byte stream with no frame boundaries, the system can reliably reconstruct exact frames, maintain smooth playback, and avoid blocking the pipeline. The separation between the reader thread and the main loop also prevents decoding hiccups from affecting display timing.

```python
def frame_reader(process, frame_size):
    """Producer: Read frames from ffmpeg and put them in the queue"""
    buffer = b""
    frame_count = 0

    # Read multiple frames at once for better Windows performance
    CHUNK_SIZE = frame_size * 6  # Read 6 frames worth of data at a time

    try:
        while not stop_flag.is_set():
            # Read larger chunks to reduce Windows pipe overhead
            chunk = process.stdout.read(CHUNK_SIZE)
            if not chunk:
                print("Stream ended")
                break

            buffer += chunk

            # Process complete frames
            while len(buffer) >= frame_size:
                raw_frame = buffer[:frame_size]
                buffer = buffer[frame_size:]

                # Convert to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8).copy()
                frame = frame.reshape((HEIGHT, WIDTH, 3))

                # Add to queue (will drop oldest if full)
                frame_queue.append((frame, time.time()))
                frame_count += 1

    except Exception as e:
        print(f"Reader error: {e}")
    finally:
        stop_flag.set()
        print(f"Reader thread st
```

## (Windows) Cleaning stderr

Windows also has a quirk where it will block other standard streams if one of them is congested. If you do not clean the stderr stream it can pile up until the stdout stream is congested and it will halt python processing. While there is a system in place to clean this up, this method introduces lag spikes which is unwanted behaviour when aiming for a smooth stream. 

After creating the ffmpeg stream another thread is started who's job it is to clean the stderr steam

```python
def drain_stderr(pipe):
    """Continuously drain stderr so ffmpeg won't block on Windows."""
    for line in iter(pipe.readline, b''):
        try:
            sys.stderr.write(line.decode(errors="replace"))
        except:
            pass
```

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
