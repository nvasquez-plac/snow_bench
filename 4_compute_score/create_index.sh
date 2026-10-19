#!/bin/bash
# Simple script to browse through a set of png images
# Written by ChatGPT
# start of the HTML code
echo "<html>" > index.html
echo "<body>" >> index.html
# loop through all PNG files in the directory
# and add a link to each file to the HTML page
for file in *.png; do
    echo "<a href='$file'><img src='$file' alt='$file' width='200' height='200'></a>" >> index.html
done
# end of the HTML code
echo "</body>" >> index.html
echo "</html>" >> index.html
