ffmpeg \
-user_agent "Mozilla/5.0" \
-headers "Referer: https://players.media.verkeerscentrum.be/\r\nOrigin:https://players.media.verkeerscentrum.be\r\n" \
-i "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8" \
-f rawvideo -pix_fmt bgr24 -vf scale=1280:720 - | \
ffplay \
-f rawvideo \
-pix_fmt bgr24 \
-video_size 1280x720 -
