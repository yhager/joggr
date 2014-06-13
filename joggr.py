import os
import sqlite3
from flask import Flask, g, session, render_template, jsonify, \
    request
from werkzeug import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'joggr.db'),
    DEBUG=True,
    SECRET_KEY='y\xc6\xfcb\x8f0=\xe8Nv\xafkb\xfd\x04!\xf5\x8bEsa\xd4\xa1*',
    ))
app.config.from_envvar('JOGGR_SETTINGS', silent=True)

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    rv.execute('pragma foreign_keys = on')
    return rv

def get_db():
    """Opens a new database connection, or uses an existing one"""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database at the end of the request"""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def get_uid(email):
    rv = query_db('select uid from users where email = ?',
                  [email], one=True)
    return rv[0] if rv else None

@app.before_request
def before_request():
    g.user = None
    if 'uid' in session:
        g.user = query_db('select * from users where uid=?',
                          [session['uid']], one=True)

@app.route('/')
def main_window():
    return render_template('layout.html')

@app.route('/api/v1/body')
def get_body():
    if g.user:
        body = render_template('entries.html')
    else:
        body = render_template('entry.html')
    return jsonify(message=None,
                   body=body)

@app.route('/api/v1/signup', methods=['GET', 'POST'])
def signup():
    if g.user:
        abort(401)
    if request.method == 'GET':
        return jsonify(body=render_template('signup.html'))

class JResponse:
    def __init__(self):
        self.error = None
        self.msg = None
        self.entries = []

    def jsonify(self):
        return jsonify(error = self.error,
                       msg = self.msg,
                       entries = self.entries)

@app.route('/api/v1/login', methods=['GET', 'POST'])
def login():
    r = JResponse()
    if g.user:
        return r.jsonify()
    if request.method == 'GET':
        return jsonify(body=render_template('login.html'))
    elif request.method == 'POST':
        user = query_db('select * from users where email=?',
                        [request.form['email']], one=True)
        if user is None or \
           not ceck_password_hash(user['pwhash'], request.form['password']):
            r.error = 'Invalid email or password'
        else:
            r.msg = 'Welcome, You logged in successfuly'
            session['uid'] = user.uid
            r.entries = get_entries(user.uid)
    return r.jsonify()

@app.route('/api/v1/logout', methods=['POST'])
def logout():
    if not g.user:
        abort(401)
    if g.user:
        session.pop('uid', None)
        r.msg = 'You were logged out'
        r.entries = []
    return r.jsonify()

@app.route('/api/v1/entries/add', methods=['POST'])
def add_entry():
    if not g.user:
        abort(401)
    r = JResponse()
    db = get_db()
    date = request.args.get('date') # convert to timestamp
    distance = request.args.get('distance', 0, type=float)
    time = request.args.get('time', 0, type=int)
    db.execute('insert into entries(uid,date,distance,time) values (?, ?, ?, ?)',
               [g.user.uid, date, distance, time])
    db.commit()
    update_weekly(uid, date, distance, time)
    r.entries = get_entries(g.user.uid)
    return jsonify(success=True)

@app.route('/api/v1/entries/filter')
def filter_entries():
    if not g.user:
        abort(401)
    db = get_db()
    from_date = request.args.get('from') # convert to timestamp
    to_date = request.args.get('to') # same
    cur = db.execute('select date,distance,time from entries where uid=? and date>=? and date<=?',
                     [uid, from_date, to_date])
    return jsonify(success=True, entries=cur.fetchall())

def update_weekly(uid, date, distance, time):
    '''Calculate weekly summary and store in db'''
    week = int(datetime(date).strftime('%W'))
    year = int(datetime(date).srtftime('%Y'))
    week_start = get_week_start(date)
    week_end = week_start + 7*24*3600
    cur = db.cursor()
    cur.execute('''select count(*) as count,
                          sum(distance) as distance,
                          sum(time) as time
                   from entries
                   where uid=? and date>=? and date<=?''',
                [uid,week_start, week_end])
    row = cur.fetchone()
    # insert/update duo
    cur.execute('insert or ignore into weekly(uid,week,year) values (?, ?, ?)',
                [uid,week,year])
    cur.execute('''update weekly set speed=?, distance=?
                   WHERE uid=? AND week=? AND year=?
                   values(?, ?, ?, ?, ?)''',
                   [row.distance/row.time, row.distance, uid, week, year])
    cur.commit()
    return jsonify(success=True)

app.run()
