#!/bin/bash

cd ~/Desktop/Himmel\ Education

# Open each script in a new Terminal window and keep it running
osascript -e 'tell application "Terminal" to do script "cd ~/Desktop/Himmel\ Education/Himmel; python3 himmel.py"'
osascript -e 'tell application "Terminal" to do script "cd ~/Desktop/Himmel\ Education/Himmel; python3 exam_mode.py"'
osascript -e 'tell application "Terminal" to do script "cd ~/Desktop/Himmel\ Education/Practice\ Mode; python3 practice_mode.py"'
osascript -e 'tell application "Terminal" to do script "cd ~/Desktop/Himmel\ Education/Question\ Bank; python3 question_bank.py"'

# Wait for 7 seconds before opening homepage.html
sleep 7
open homepage.html
