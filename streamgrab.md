# Streamgrabbing script

For our project we try to find public traffic cameras on the web, hook into the stream and perform our own image processing. The process of reading a internet stream requires some additional processing steps like format conversion, buffering and sometimes others types of processing to achieve a reliable stream to perform the actual image processing on.

There is however a difference in code for the linux and windows version. Linux has very optimized piping which reduces the number of processing steps when using ffmpeg to do the conversions and piping it into openCV. This version is also more optimized.

Keep in mind that in this document we explain our thought process behind each processing step so take note that not all steps are done in linux. For this reason we do not refer to actual lines in the code and only sometimes provide code snippets. The general idea will only be explained.
