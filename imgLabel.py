import os
import cv2
import sys, getopt
from parser import parser
from utils import save_info, load_info, go2frame, show_image

args = parser.parse_args()
video_path = args.label_video_path
if not os.path.isfile(video_path) or not video_path.endswith('.mp4'):
    print("Not a valid video path! Please modify path in parser.py --label_video_path")
    sys.exit(1)

# create information record dictionary
# Frame: index of frame
# Ball : 0 for no ball or not clearly visible, 1 for having ball
# x: x position of ball center
# y: y position of ball center
csv_path = args.csv_path
load_csv = False
if os.path.isfile(csv_path) and csv_path.endswith('.csv'):
    load_csv = True
else:
    print("Not a valid csv file! Please modify path in parser.py --csv_path")

# acquire video info
cap = cv2.VideoCapture(video_path)
fps = int(cap.get(cv2.CAP_PROP_FPS))
n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
label_hz = float(args.label_hz)
if label_hz <= 0:
    print("label_hz must be greater than 0")
    sys.exit(1)
frame_step = max(1, int(round(float(fps) / label_hz))) if fps > 0 else 1
fast_step = frame_step * 36
print("Label frequency: {:.3f} Hz, navigation step: {} frame(s)".format(label_hz, frame_step))

if load_csv:
    info = load_info(csv_path)
    if len(info) != n_frames:
        print("Number of frames in video and dictionary are not the same!")
        print("Fail to load, create new dictionary instead.")
        info = {
            idx:{
            'Frame': idx,
            'Ball': 0,
            'x': -1,
            'y': -1
            } for idx in range(n_frames)
        }
    else:
        print("Load labeled dictionary successfully.")
else:
    print("Create new dictionary")
    info = {
        idx:{
        'Frame': idx,
        'Ball': 0,
        'x': -1,
        'y': -1
        } for idx in range(n_frames)
    }

# # # # # # # # # # # # # # # #
# e: exit program             #
# s: save info                #
# n: next label frame         #
# p: previous label frame     #
# f: to first frame           #
# l: to last frame            #
# >: fast forward 36 labels   #
# <: fast backward 36 labels  #
# # # # # # # # # # # # # # # #

def ball_label(event, x, y, flags, param):
    global frame_no, info, image
    if event == cv2.EVENT_LBUTTONDOWN:
        h, w, _ = image.shape
        info[frame_no]['x'] = x/w
        info[frame_no]['y'] = y/h
        info[frame_no]['Ball'] = 1

    elif event == cv2.EVENT_MBUTTONDOWN:
        info[frame_no]['x'] = -1
        info[frame_no]['y'] = -1
        info[frame_no]['Ball'] = 0

saved_success = False
frame_no = 0
_, image = cap.read()
show_image(image, 0, info[0]['x'], info[0]['y'])
while True:
    leave = 'y'
    cv2.imshow('imgLabel', image)
    cv2.setMouseCallback('imgLabel', ball_label)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('e'):
        if not saved_success:
            print("You forget to save file!")
            while True:
                leave = str(input("Really want to leave without saving? [Y/N]"))
                leave = leave.lower()
                if leave != 'y' and leave != 'n':
                    print("Please type 'y/Y' or 'n/N'")
                    continue
                elif leave == 'y':
                    cap.release()
                    cv2.destroyAllWindows()
                    print("Exit label program")
                    sys.exit(1)
                elif leave == 'n':
                    break
       
        if leave == 'y':
            cap.release()
            cv2.destroyAllWindows()
            print("Exit label program")
            sys.exit(1)

    elif key == ord('s'):
        saved_success = save_info(info, video_path)

    elif key == ord('n'):
        if frame_no >= n_frames-1:
            print("This is the last frame")
            continue
        frame_no = min(frame_no + frame_step, n_frames-1)
        image = go2frame(cap, frame_no, info)
        print("Frame No.{}".format(frame_no))

    elif key == ord('p'):
        if frame_no == 0:
            print("This is the first frame")
            continue
        frame_no = max(frame_no - frame_step, 0)
        image = go2frame(cap, frame_no, info)
        print("Frame No.{}".format(frame_no))

    elif key == ord('f'):
        if frame_no == 0:
            print("This is the first frame")
            continue
        frame_no = 0
        image = go2frame(cap, frame_no, info) 
        print("Frame No.{}".format(frame_no))

    elif key == ord('l'):
        if frame_no == n_frames-1:
            print("This is the last frame")
            continue
        frame_no = n_frames-1
        image = go2frame(cap, frame_no, info)
        print("Frame No.{}".format(frame_no))

    elif key == ord('>'):
        if frame_no + fast_step >= n_frames-1:
            print("Reach last frame")
            frame_no = n_frames-1
        else:
            frame_no += fast_step
        image = go2frame(cap, frame_no, info)
        print("Frame No.{}".format(frame_no))

    elif key == ord('<'):
        if frame_no - fast_step <= 0:
            print("Reach first frame")
            frame_no = 0
        else:
            frame_no -= fast_step
        image = go2frame(cap, frame_no, info)
        print("Frame No.{}".format(frame_no))
    else:
        image = go2frame(cap, frame_no, info)
