<<<<<<< HEAD
from os.path import join, splitext, isfile
=======
from os import listdir
from os.path import join, splitext, dirname, isfile
>>>>>>> album_art
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from config import config
from mimetypes import guess_type

ART_DIR = config.get('Artwork', 'art_path')


def index_art(song):
    ext = splitext(song['path'])[1]

    art_uri = ''
    if ext == '.mp3':
        art_uri = index_mp3_art(song)
    elif ext == '.flac':
        art_uri = index_flac_art(song)



def index_mp3_art(song):
    try:
        tags = MP3(song['path'])
    except:
        return False
    data = ''
    mime = ''
    for tag in tags:
        if tag.startswith('APIC'):
            data = tags[tag].data
            mime = tags[tag].mime
            break
    if not data:
        path = find_art(song)
        if path:
            afile = open(path, 'r')
            data = afile.read()
            mime = guess_type(path)

    path = write_art(song, data, mime)

    return path


def index_flac_art(song):
    try:
        tags = FLAC(song['path'])
    except:
        return False
    data = ''
    mime = ''
    if tags.pictures:
        data = tags.pictures[0].data
        mime = tags.pictures[0].mime
    else:
        path = find_art(song)
        if path:
            afile = open(path, 'r')
            data = afile.read()
            mime = guess_type(path)

    path = write_art(song, data, mime)

    return path

<<<<<<< HEAD

def write_art(song, data):
=======
def find_art(song):
    art_strings = ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png']
    path = dirname(song['path'])
    for s in art_strings:
        if isfile(join(path, s)):
            return join(path, s)

    for f in listdir(path):
        if f.endswith(".jpg") or f.endswith(".png"):
            return join(path, f)

    return ""


def write_art(song, data, mime):
>>>>>>> album_art
    if not data:
        return None
    ext = ''
    if mime == 'image/png':
        ext = 'png'
    elif mime == 'image/jpeg':
        ext = 'jpg'
    else:
        ext = 'jpg'

<<<<<<< HEAD
    filepath = get_art(song['checksum'])
=======
    filepath = join('.' + ART_DIR + song['checksum'] + "." + ext)
>>>>>>> album_art

    out = open(filepath, 'w')
    out.write(data)
    out.close()


def get_art(checksum):
    if not checksum:
        return None
<<<<<<< HEAD
    filepath = join('.' + ART_DIR + checksum + ".jpg")

    return filepath


def find_art(checksum):
    path = get_art(checksum)

    if isfile(path):
        return path
    return None
=======
    filepath = join(checksum)
    for f in listdir('.' + ART_DIR):
        if f.startswith(filepath):
            return '.' + ART_DIR + f;

    return ""
>>>>>>> album_art