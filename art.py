from os import path
from os.path import isfile
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from config import config

ART_DIR = config.get('Artwork', 'art_path')

def index_art(song):
    ext = splitext(song['path'])[1]

    try:
        if ext == 'mp3':
            tags = MP3(song['path'])
        elif ext == 'flac':
            tags = FLAC(song['path'])
        else:
            return None
    except:
        return None

    data = ''
    kind = ''

    if tags.pictures:
        data = tags.pictures[0]
    else:
        for tag in tags:
            if tag.startswith('APIC'):
                data = tags[tag].data
                break

    if not data:
        path = find_art(song)
        if path:
            try:
                afile = open(path, 'r')
                data = afile.read()
                close(afile)
            except IOError:
                return None
        else:
            return None

    path = write_art(song, data)

def find_art(song):
    art_strings = ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png']
    path = dirname(song['path'])
    for s in art_strings:
        if isfile(join(path, s)):
            return join(path, s)

    for f in listdir(path):
        ext = splitext(f)[1]
        if ext == 'jpg' or ext == 'png':
            return join(path, f)

    return None


def write_art(song, data):
    if not data or not song['artist'] or not song['album']:
        return None

    image_type = imghdr.what(None, data)
    ext = ''

    if image_type == 'jpeg':
        ext = 'jpg'
    elif image_type == 'png':
        ext = 'png'

    filepath = "{0}/{1}-{2}.{3}".format(artist, album, ext)

    out = open(filepath, 'w')
    out.write(data)
    out.close()


def get_art(artist, album):
    if not album or not artist:
        return None

    ext = ['.jpg', '.png']
    name = artist + " - " + album;

    for e in ext:
        if isfile('.' + ART_DIR + name + e):
            return '.' + ART_DIR + name + e

    return None
