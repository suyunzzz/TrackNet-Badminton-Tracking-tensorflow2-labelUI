import json
import mimetypes
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cv2

from parser import parser
from utils import load_info

# Extend the shared CLI parser for the web label tool.
parser.add_argument('--host', type=str, default='127.0.0.1',
                    help='host for web label server (default: 127.0.0.1)')
parser.add_argument('--port', type=int, default=8000,
                    help='port for web label server (default: 8000)')


def init_info(n_frames):
    return {
        idx: {
            'Frame': idx,
            'Ball': 0,
            'x': -1.0,
            'y': -1.0,
        }
        for idx in range(n_frames)
    }


def resolve_csv_path(video_path, csv_path):
    if csv_path:
        return os.path.abspath(csv_path)
    return os.path.splitext(os.path.abspath(video_path))[0] + '.csv'


def compute_label_step(fps, label_hz):
    if label_hz <= 0:
        raise ValueError('label_hz must be greater than 0')
    if fps <= 0:
        return 1
    return max(1, int(round(float(fps) / float(label_hz))))


class LabelSession:
    def __init__(self, video_path, csv_path, label_hz):
        self.video_path = os.path.abspath(video_path)
        self.video_name = os.path.basename(self.video_path)
        self.csv_path = resolve_csv_path(self.video_path, csv_path)
        self.meta_path = self.csv_path + '.weblabel.json'
        self.state_lock = threading.Lock()
        self.video_lock = threading.Lock()
        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            raise ValueError('Failed to open video: {}'.format(self.video_path))

        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS)) or 0.0
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.label_hz = float(label_hz)
        self.label_step = compute_label_step(self.fps, self.label_hz)
        self.target_frames = set(range(0, self.n_frames, self.label_step))
        self.info, csv_loaded = self._load_or_init_info()
        self.reviewed_frames = self._load_reviewed_frames(csv_loaded)
        self.dirty = False

    def _load_or_init_info(self):
        if os.path.isfile(self.csv_path) and self.csv_path.endswith('.csv'):
            info = load_info(self.csv_path)
            if len(info) == self.n_frames:
                print('Load labeled dictionary successfully from {}'.format(self.csv_path))
                return info, True
            print('CSV frame count mismatch, create new dictionary instead.')
        else:
            print('Create new dictionary')
        return init_info(self.n_frames), False

    def _load_reviewed_frames(self, csv_loaded):
        if os.path.isfile(self.meta_path):
            try:
                with open(self.meta_path, 'r') as file:
                    payload = json.load(file)
                reviewed = {
                    int(frame_no) for frame_no in payload.get('reviewed_frames', [])
                    if 0 <= int(frame_no) < self.n_frames
                }
                print('Load review progress from {}'.format(self.meta_path))
                return reviewed
            except Exception:
                print('Failed to load review progress, fallback to csv inference.')
        if csv_loaded:
            return set(range(self.n_frames))
        return set()

    def _frame_payload(self, frame_no):
        item = self.info[frame_no]
        reviewed = frame_no in self.reviewed_frames
        labeled = item['Ball'] == 1 and item['x'] >= 0 and item['y'] >= 0
        return {
            'frame': frame_no,
            'ball': item['Ball'],
            'x': item['x'],
            'y': item['y'],
            'reviewed': reviewed,
            'labeled': labeled,
        }

    def get_progress(self):
        reviewed = len(self.reviewed_frames & self.target_frames)
        positive = sum(
            1 for frame_no, item in self.info.items()
            if frame_no in self.target_frames and item['Ball'] == 1 and item['x'] >= 0 and item['y'] >= 0
        )
        total = len(self.target_frames)
        return {
            'labeled': reviewed,
            'positive': positive,
            'unlabeled': total - reviewed,
            'total': total,
            'percent': round((reviewed / total) * 100, 2) if total else 0.0,
        }

    def get_state(self):
        with self.state_lock:
            return {
                'video_path': self.video_path,
                'video_name': self.video_name,
                'csv_path': self.csv_path,
                'fps': self.fps,
                'label_hz': self.label_hz,
                'label_step': self.label_step,
                'frame_count': self.n_frames,
                'width': self.width,
                'height': self.height,
                'progress': self.get_progress(),
                'dirty': self.dirty,
            }

    def get_annotation(self, frame_no):
        with self.state_lock:
            self._check_frame_no(frame_no)
            return self._frame_payload(frame_no)

    def set_annotation(self, frame_no, x, y):
        with self.state_lock:
            self._check_frame_no(frame_no)
            x = min(max(float(x), 0.0), 1.0)
            y = min(max(float(y), 0.0), 1.0)
            self.info[frame_no]['Ball'] = 1
            self.info[frame_no]['x'] = x
            self.info[frame_no]['y'] = y
            self.reviewed_frames.add(frame_no)
            self.dirty = True
            return {
                'annotation': self._frame_payload(frame_no),
                'progress': self.get_progress(),
                'dirty': self.dirty,
            }

    def clear_annotation(self, frame_no):
        with self.state_lock:
            self._check_frame_no(frame_no)
            self.info[frame_no]['Ball'] = 0
            self.info[frame_no]['x'] = -1.0
            self.info[frame_no]['y'] = -1.0
            self.reviewed_frames.add(frame_no)
            self.dirty = True
            return {
                'annotation': self._frame_payload(frame_no),
                'progress': self.get_progress(),
                'dirty': self.dirty,
            }

    def save(self):
        with self.state_lock:
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            with open(self.csv_path, 'w') as file:
                file.write('Frame,Ball,x,y\n')
                for frame in range(self.n_frames):
                    item = self.info[frame]
                    data = '{},{},{:.3f},{:.3f}'.format(
                        item['Frame'], item['Ball'], item['x'], item['y']
                    )
                    file.write(data + '\n')
            with open(self.meta_path, 'w') as file:
                json.dump(
                    {'reviewed_frames': sorted(self.reviewed_frames)},
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
            self.dirty = False
            return {
                'saved': True,
                'csv_path': self.csv_path,
                'meta_path': self.meta_path,
                'progress': self.get_progress(),
                'dirty': self.dirty,
            }

    def next_unlabeled(self, current_frame, direction=1):
        with self.state_lock:
            self._check_frame_no(current_frame)
            current_target = self.align_frame(current_frame)
            step = self.label_step if direction >= 0 else -self.label_step
            iterator = range(current_target + step, self.n_frames if direction >= 0 else -1, step)

            for idx in iterator:
                if idx in self.target_frames and idx not in self.reviewed_frames:
                    return {'frame': idx, 'found': True}
            return {'frame': current_frame, 'found': False}

    def get_frame_bytes(self, frame_no):
        self._check_frame_no(frame_no)
        with self.video_lock:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, image = self.cap.read()
        if not ok or image is None:
            raise ValueError('Failed to read frame {}'.format(frame_no))
        ok, buffer = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise ValueError('Failed to encode frame {}'.format(frame_no))
        return buffer.tobytes()

    def _check_frame_no(self, frame_no):
        if frame_no < 0 or frame_no >= self.n_frames:
            raise ValueError('Frame {} out of range [0, {})'.format(frame_no, self.n_frames))

    def align_frame(self, frame_no):
        aligned = int(round(frame_no / self.label_step)) * self.label_step
        return max(0, min(aligned, self.n_frames - 1))


class LabelRequestHandler(BaseHTTPRequestHandler):
    session = None
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_label_static')

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == '/':
                return self._serve_static('index.html')
            if path.startswith('/static/'):
                rel_path = path[len('/static/'):]
                return self._serve_static(rel_path)
            if path == '/api/state':
                return self._send_json(self.session.get_state())
            if path == '/api/frame':
                frame_no = self._query_int(query, 'index')
                data = self.session.get_frame_bytes(frame_no)
                return self._send_bytes(data, 'image/jpeg')
            if path == '/api/annotation':
                frame_no = self._query_int(query, 'index')
                return self._send_json(self.session.get_annotation(frame_no))
            if path == '/api/next_unlabeled':
                frame_no = self._query_int(query, 'from')
                direction = int(query.get('direction', ['1'])[0])
                return self._send_json(self.session.next_unlabeled(frame_no, direction))
            self._send_error(HTTPStatus.NOT_FOUND, 'Not found')
        except Exception as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json_body()
            if path == '/api/annotate':
                frame_no = int(payload['frame'])
                x = float(payload['x'])
                y = float(payload['y'])
                return self._send_json(self.session.set_annotation(frame_no, x, y))
            if path == '/api/clear':
                frame_no = int(payload['frame'])
                return self._send_json(self.session.clear_annotation(frame_no))
            if path == '/api/save':
                return self._send_json(self.session.save())
            self._send_error(HTTPStatus.NOT_FOUND, 'Not found')
        except Exception as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

    def log_message(self, format_str, *args):
        return

    def _read_json_body(self):
        content_length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(content_length) if content_length else b'{}'
        return json.loads(raw.decode('utf-8'))

    def _serve_static(self, rel_path):
        rel_path = rel_path.lstrip('/')
        file_path = os.path.abspath(os.path.join(self.static_dir, rel_path))
        if not file_path.startswith(self.static_dir):
            return self._send_error(HTTPStatus.FORBIDDEN, 'Forbidden')
        if not os.path.isfile(file_path):
            return self._send_error(HTTPStatus.NOT_FOUND, 'Static file not found')
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as file:
            return self._send_bytes(file.read(), mime_type or 'application/octet-stream')

    def _query_int(self, query, key):
        if key not in query or not query[key]:
            raise ValueError('Missing query parameter: {}'.format(key))
        return int(query[key][0])

    def _send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, payload, content_type, status=HTTPStatus.OK):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def _send_error(self, status, message):
        self._send_json({'error': message}, status=status)


def main():
    args = parser.parse_args()
    video_path = args.label_video_path
    if not os.path.isfile(video_path) or not video_path.endswith('.mp4'):
        raise ValueError('Not a valid video path! Please modify --label_video_path.')

    session = LabelSession(video_path, args.csv_path, args.label_hz)
    LabelRequestHandler.session = session
    server = ThreadingHTTPServer((args.host, args.port), LabelRequestHandler)
    url = 'http://{}:{}/'.format(args.host, args.port)
    print('Web label server is running at {}'.format(url))
    print('Video: {}'.format(session.video_path))
    print('CSV  : {}'.format(session.csv_path))
    print('Label: {:.3f} Hz, step {} frame(s)'.format(session.label_hz, session.label_step))
    print('Keyboard shortcuts are available inside the page.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStop web label server.')
    finally:
        server.server_close()
        session.cap.release()


if __name__ == '__main__':
    main()
