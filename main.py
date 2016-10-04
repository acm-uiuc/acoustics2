from flask import Flask, request, jsonify, Response
from gevent.wsgi import WSGIServer
from functools import wraps
from crossdomain import crossdomain
from scheduler import Scheduler
from config import config
import song
import chroma
import player
import user
import audit_log
from db import BannedUser

AUTHENTICATION_ENABLED = config.getboolean('Authentication', 'enabled')
if not AUTHENTICATION_ENABLED:
    TEST_USERNAME = config.get('Authentication', 'test_username')

app = Flask(__name__)
#app.debug = True

scheduler = Scheduler()
scheduler.start()


def login_required(f):
    if not AUTHENTICATION_ENABLED:
        return f

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.form.get('token')
        if token is None:
            return jsonify({'message': 'No SSO token provided'}), 401
        if not user.valid_session(token):
            return jsonify({'message': 'Invalid SSO token: ' + token}), 401
        return f(*args, **kwargs)

    return decorated_function


def get_username(token):
    if not AUTHENTICATION_ENABLED:
        return TEST_USERNAME
    else:
        session = user.get_session(token)
        return session.json()['user']['name']


def check_eq_support(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not player.equalizer_supported:
            return jsonify({'message': 'Equalizer not supported'}), 400
        return f(*args, **kwargs)

    return decorated_function


@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': str(error)}), 404


@app.errorhandler(500)
def not_found(error):
    return jsonify({'message': str(error)}), 500


@app.route('/v1/player/play_next', methods=['POST'])
@login_required
@crossdomain(origin='*')
def play_next():
    audit_log.log(
        get_username(request.form.get('token')),
        'Skipped song'
    )
    return jsonify(scheduler.play_next(skip=True) or {})


@app.route('/v1/player/pause', methods=['POST'])
@login_required
@crossdomain(origin='*')
def pause():
    audit_log.log(
        get_username(request.form.get('token')),
        'Paused/resumed song'
    )
    return jsonify(player.pause())


@app.route('/v1/player/volume', methods=['POST'])
@login_required
@crossdomain(origin='*')
def player_set_volume():
    if request.form.get('volume'):
        vol = int(request.form.get('volume'))
        if 0 <= vol <= 100:
            audit_log.log(
                get_username(request.form.get('token')),
                'Changed volume to %d' % vol
            )
            return jsonify(player.set_volume(vol))
        else:
            return jsonify({
                'message': 'Volume must be between 0 and 100',
            }), 400
    return jsonify({'message': 'No volume parameter'}), 400


@app.route('/v1/player/equalizer', methods=['GET'])
@crossdomain(origin='*')
def player_get_equalizer_info():
    return jsonify(player.get_static_equalizer_info())


@app.route('/v1/player/equalizer/enable', methods=['POST'])
@check_eq_support
@login_required
@crossdomain(origin='*')
def player_enable_eq():
    if request.form.get('enabled'):
        enabled = request.form.get('enabled') in ('True', 'true')
        audit_log.log(
            get_username(request.form.get('token')),
            '%s equalizer' % ('Enabled' if enabled else 'Disabled')
        )
        return jsonify(player.set_equalizer_enabled(enabled))
    return jsonify({'message': 'No equalizer enablement parameter'}), 400


@app.route('/v1/player/equalizer/adjust_preset', methods=['POST'])
@check_eq_support
@login_required
@crossdomain(origin='*')
def player_adjust_eq_preset():
    if request.form.get('index'):
        idx = int(request.form.get('index'))
        if 0 <= idx < player.num_equalizer_presets:
            return jsonify(player.set_equalizer_preset(idx))
        else:
            return jsonify({
                'message': 'Equalizer preset index must be between 0 and %d'%(
                    player.num_equalizer_presets - 1)
            }), 400
    return jsonify({'message': 'No equalizer preset index parameter'}), 400


@app.route('/v1/player/equalizer/adjust_preamp', methods=['POST'])
@check_eq_support
@login_required
@crossdomain(origin='*')
def player_adjust_eq_preamp():
    if request.form.get('level'):
        lvl = float(request.form.get('level'))
        if -20.0 <= lvl <= 20.0:
            return jsonify(player.set_equalizer_preamp(lvl))
        else:
            return jsonify({'message':
                'Equalizer preamp level must be between -20 dB and +20 dB'
            }), 400
    return jsonify({'message': 'No equalizer preamp level parameter'}), 400


@app.route('/v1/player/equalizer/adjust_band', methods=['POST'])
@check_eq_support
@login_required
@crossdomain(origin='*')
def player_adjust_eq_band():
    if not request.form.get('band'):
        return jsonify({'message': 'No band index parameter'}), 400
    if not request.form.get('level'):
        return jsonify({'message': 'No band level parameter'}), 400
    idx = int(request.form.get('band'))
    lvl = float(request.form.get('level'))
    if idx < 0 or idx >= player.num_equalizer_bands:
        return jsonify({
            'message': 'Equalizer band index must be between 0 and %d'%(
                player.num_equalizer_bands - 1)
        }), 400
    if lvl < -20.0 or lvl > 20.0:
        return jsonify({
            'message': 'Equalizer band level must be between -20 dB and +20 dB'
        }), 400
    return jsonify(player.set_equalizer_band(idx, lvl))


@app.route('/v1/songs/<song_id>', methods=['GET'])
@crossdomain(origin='*')
def show_song(song_id):
    try:
        return jsonify(song.Song(song_id).dictify())
    except Exception, e:
        return jsonify({'message': str(e)}), 404


@app.route('/v1/songs/search', methods=['GET'])
@crossdomain(origin='*')
def search():
    query = request.args.get('q')
    if query.startswith('album:'):
        return jsonify(song.get_album(query[6:].lstrip()))
    elif query.startswith('artist:'):
        return jsonify(song.get_albums_for_artist(query[7:].lstrip()))
    elif query.startswith('play-history'):
        try:
            limit = int(query[13:])
            return jsonify(song.get_history(limit=limit))
        except ValueError:
            return jsonify(song.get_history())
    elif query.startswith('top-songs'):
        try:
            limit = int(query[10:])
            return jsonify(song.top_songs(limit=limit))
        except ValueError:
            return jsonify(song.top_songs())
    else:
        limit = request.args.get('limit')
        if limit and int(limit) != 0:
            return jsonify(song.search_songs(query, limit=int(limit)))
        return jsonify(song.search_songs(query))


@app.route('/v1/songs/random', methods=['GET'])
@crossdomain(origin='*')
def random_songs():
    limit = request.args.get('limit')
    if limit and int(limit) != 0:
        return jsonify(song.random_songs(limit=int(limit)))
    return jsonify(song.random_songs())


@app.route('/v1/songs/history', methods=['GET'])
@crossdomain(origin='*')
def get_history():
    limit = request.args.get('limit')
    if limit and int(limit) != 0:
        return jsonify(song.get_history(limit=int(limit)))
    return jsonify(song.get_history())


@app.route('/v1/songs/top_songs', methods=['GET'])
@crossdomain(origin='*')
def top_songs():
    limit = request.args.get('limit')
    if limit and int(limit) != 0:
        return jsonify(song.top_songs(limit=int(limit)))
    return jsonify(song.top_songs())


@app.route('/v1/songs/top_artists', methods=['GET'])
@crossdomain(origin='*')
def top_artists():
    limit = request.args.get('limit')
    if limit and int(limit) != 0:
        return jsonify(song.top_artists(limit=int(limit)))
    return jsonify(song.top_artists())


@app.route('/v1/queue', methods=['GET'])
@crossdomain(origin='*')
def show_queue():
    queue_user = request.args.get('user')
    if queue_user:
        return jsonify(scheduler.get_queue(user=queue_user))
    return jsonify(scheduler.get_queue())


@app.route('/v1/queue/<int:song_id>', methods=['DELETE'])
@login_required
@crossdomain(origin='*')
def queue_remove(song_id):
    audit_log.log(
        get_username(request.form.get('token')),
        'Removed song with id %d' % song_id
    )
    return jsonify(scheduler.remove_song(song_id))


@app.route('/v1/queue', methods=['DELETE'])
@login_required
@crossdomain(origin='*')
def queue_clear():
    audit_log.log(
        get_username(request.form.get('token')),
        'Cleared queue'
    )
    return jsonify(scheduler.clear())


@app.route('/v1/queue/add', methods=['POST'])
@login_required
@crossdomain(origin='*')
def queue_add():
    username = get_username(request.form.get('token'))
    if request.form.get('id'):
        try:
            song_id = int(request.form.get('id'))
        except ValueError:
            return jsonify({'message': 'Invalid id'}), 400
        audit_log.log(username, 'Added/voted for song with id %d' % song_id)
        try:
            return jsonify(scheduler.vote_song(username, song_id=song_id))
        except Exception, e:
            return jsonify({'message': str(e)}), 400
    elif request.form.get('url'):  # youtube and soundcloud
        url = request.form.get('url')
        audit_log.log(username, 'Added/voted for stream with url %s' % url)
        try:
            return jsonify(scheduler.vote_song(username, stream_url=url))
        except Exception, e:
            return jsonify({'message': str(e)}), 400
    return jsonify({'message': 'No id or url parameter'}), 400


@app.route('/v1/now_playing', methods=['GET'])
@crossdomain(origin='*')
def now_playing():
    return jsonify(player.get_now_playing() or {})


@app.route('/v1/chroma/switch', methods=['POST'])
@login_required
@crossdomain(origin='*')
def switch_animation():
    if request.form.get('anim'):
        anim = int(request.form.get('anim'))
        return jsonify(chroma.switch_animation(anim))
    return jsonify({'message': 'No anim parameter'}), 400


@app.route('/v1/session', methods=['POST'])
@crossdomain(origin='*')
def create_session():
    """Login.

    For Crowd SSO support, save the token in a cookie with name
    'crowd.token_key'.
    """
    username = request.form.get('username')
    password = request.form.get('password')
    r = user.create_session(username, password)
    if isinstance(r, BannedUser):
        reason = r.reason or 'Not specified'
        message = (
            'You are banned. Please contact a Beats admin to be unbanned. '
            'Reason: ' + reason
        )
        return jsonify({'message': message}), 403
    elif r.status_code == 403:
        return jsonify(
            {'message': 'You must be an ACM member to use Beats.'}), 403
    return jsonify(r.json()), r.status_code


@app.route('/v1/session/<token>', methods=['GET'])
@crossdomain(origin='*')
def get_session(token):
    r = user.get_session(token)
    return jsonify(r.json()), r.status_code


@app.route('/v1/session/<token>', methods=['DELETE'])
@crossdomain(origin='*')
def delete_session(token):
    r = user.delete_session(token)
    return Response(status=r.status_code)


@app.route('/', methods=['GET'])
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    print 'Beats by ACM'
    print 'VLC version: ' + player.get_vlc_version()
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
