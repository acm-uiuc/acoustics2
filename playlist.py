from db import Playlist, PlaylistItem, Song, Session, engine
from sqlalchemy.sql import select
from sqlalchemy import desc

def create_playlist(user, name):
    session = Session()
    playlist = Playlist(user=user, name=name)
    session.add(playlist)
    session.commit()
    return get_playlist(playlist.id)

def get_playlists_for_user(user):
    playlists = Playlist.__table__
    conn = engine.connect()
    s = select([playlists.c.id, playlists.c.name]) \
            .where(playlists.c.user == user) \
            .order_by(playlists.c.name)
    res = [{'id': row[0], 'name': row[1]} for row in conn.execute(s)]
    conn.close()
    return {'user': user, 'playlists': res}

def get_playlist(playlist_id):
    session = Session()
    playlist = session.query(Playlist).get(playlist_id)

    songs = session.query(Song) \
            .join(PlaylistItem) \
            .filter(PlaylistItem.playlist_id == playlist_id) \
            .order_by(PlaylistItem.index).all()
    session.commit()
    songs_list = [song.dictify() for song in songs]
    return {'id': playlist_id, 'user': playlist.user, 'name': playlist.name, 'songs': songs_list}

def delete_playlist(user, playlist_id):
    session = Session()
    playlist = session.query(Playlist).get(playlist_id)
    if user != playlist.user:
        raise Exception("User is not the owner of this playlist")
    session.delete(playlist)
    session.commit()
    return get_playlists_for_user(user);

def rename_playlist(user, playlist_id, new_name):
    session = Session()
    playlist = session.query(Playlist).get(playlist_id)
    if user != playlist.user:
        raise Exception("User is not the owner of this playlist")
    playlist.name = new_name
    session.commit()
    return get_playlist(playlist_id)

def add_song_to_playlist(user, playlist_id, song_id):
    items = PlaylistItem.__table__
    session = Session()
    append_index = session.query(PlaylistItem) \
            .filter_by(playlist_id=playlist_id) \
            .order_by(desc(items.c.index)) \
            .first()
    index = 0
    if append_index:
        index = append_index.index + 1

    playlist = session.query(Playlist).get(playlist_id)
    if user != playlist.user:
        raise Exception("User is not the owner of this playlist")

    dup = session.query(PlaylistItem).filter_by(song_id=song_id, playlist_id=playlist_id).first()
    if not dup: # no bike in DB
        item = PlaylistItem(playlist_id=playlist_id, song_id=song_id, index=index)
        session.add(item)

    session.commit()
    return get_playlist(playlist_id)

def remove_song_from_playlist(user, playlist_id, song_id):
    session = Session()
    item = session.query(PlaylistItem).filter_by(playlist_id=playlist_id, song_id=song_id).first()
    playlist = session.query(Playlist).get(playlist_id)
    if user != playlist.user:
        raise Exception("User is not the owner of this playlist")
    session.delete(item)
    session.commit()
    return get_playlist(playlist_id)

def swap_song_indices(user, playlist_id, a, b):
    session = Session()
    first = session.query(PlaylistItem).filter_by(playlist_id=playlist_id, song_id=a).first()
    second = session.query(PlaylistItem).filter_by(playlist_id=playlist_id, song_id=b).first()
    atmp = first.index
    btmp = second.index
    first.index = -1
    second.index = -2
    session.commit()
    second.index = atmp
    first.index = btmp
    session.commit()
    return get_playlist(playlist_id)
