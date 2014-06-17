import os
import sqlite3
from flask import Flask, g, session, render_template, jsonify, \
    request, flash, redirect, url_for, abort
from werkzeug import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from time import mktime, localtime
import re
from functools import wraps

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

def get_entries(from_date = None, to_date = None):
    if not g.user:
        return None
    where = 'uid=?'
    args = [g.user['uid']]
    if from_date and to_date:
        where = where + ' and date >=? and date <=?'
        args.append(mktime(from_date.timetuple()))
        args.append(mktime(to_date.timetuple()))
    return query_db('''select date(date, 'unixepoch', 'localtime') as date,
                              distance,
                              time(time, 'unixepoch') as time,
                              round(distance*3600/time, 1) as speed
                       from entries
                       where {where} order by date desc'''.format(where=where),
                    args)

def jsonify_template(t, **kwargs):
    return jsonify(body=render_template(t, **kwargs))

def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not g.user:
            abort(401)
        return func(*args, **kwargs)
    return decorated_view

def anon_only(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if g.user:
            abort(401)
        return func(*args, **kwargs)
    return decorated_view

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
def body():
    template = 'entries.html' if g.user else 'entry.html'
    return jsonify_template(template, entries=get_entries())

@app.route('/api/v1/signup', methods=['GET', 'POST'])
@anon_only
def signup():
    if request.method == 'GET':
        return jsonify_template('signup.html')
    error = None
    if request.method == 'POST':
        if not request.form['email'] or \
           '@' not in request.form['email']:
            error = 'Please enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_uid(request.form['email']) is not None:
            error = 'This email address is already registered'
        else:
            db = get_db()
            db.execute('INSERT INTO users(email, pwhash) VALUES(?, ?)',
                   [request.form['email'],
                    generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully signed up and can login now')
            return redirect(url_for('login'))
    return jsonify_template('signup.html', error=error)

@app.route('/api/v1/login', methods=['GET', 'POST'])
@anon_only
def login():
    if request.method == 'GET':
        return jsonify_template('login.html')
    error = None
    if request.method == 'POST':
        user = query_db('select * from users where email=?',
                        [request.form['email']], one=True)
        if user is None or \
           not check_password_hash(user['pwhash'], request.form['password']):
            error = 'Invalid email or password'
        else:
            flash('Welcome, You logged in successfuly')
            session['uid'] = user['uid']
            return redirect(url_for('body'))
    return jsonify_template('login.html', error=error)

@app.route('/api/v1/logout', methods=['POST'])
@login_required
def logout():
    if not g.user:
        abort(401)
    if g.user:
        session.pop('uid', None)
        flash('You were logged out')
    return redirect(url_for('body'))

@app.route('/api/v1/entries/add', methods=['POST'])
@login_required
def add_entry():
    db = get_db()
    error = None
    try:
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
    except ValueError:
        error = 'Please enter date in YYYY-MM-DD format'
    distance = request.form.get('distance', 0, type=float)
    time_input = re.findall('[0-9]+', request.form.get('time', '0:0'))
    if len(time_input) != 2:
        error = 'Please input time in hh:mm format'
    elif int(time_input[0]) == 0 and int(time_input[1]) == 0:
        error = 'Please enter the time you ran'
    elif distance == 0.0:
        error = 'Please enter the distance you ran, in miles'
    if error:
        return jsonify_template('entries.html', error=error, entries=get_entries())
    time = timedelta(minutes=int(time_input[0]), seconds=int(time_input[1]))
    db.execute('insert into entries(uid,date,distance,time) values (?, ?, ?, ?)',
               [g.user['uid'], mktime(date.timetuple()), distance, time.seconds])
    db.commit()
    update_weekly(date)
    flash('Entry added')
    return redirect(url_for('body'))

@app.route('/api/v1/weekly')
@login_required
def weekly():
    entries = query_db('''select date(week_start, 'unixepoch', 'localtime') as week_start,
                                 round(avg_speed,1) as avg_speed, total_distance
                          from weekly
                          where uid=?
                          order by week_start desc''',
                       [g.user['uid']])
    return jsonify_template('weekly.html', entries=entries)

@app.route('/api/v1/entries/filter', methods=['POST'])
@login_required
def filter():
    db = get_db()
    from_date = to_date = None
    error = None
    try:
        from_date = datetime.strptime(request.form.get('from'), '%Y-%m-%d')
        to_date = datetime.strptime(request.form.get('to'), '%Y-%m-%d')
    except ValueError:
        error = 'Please enter valid dates to filter on'
    if to_date < from_date:
        error = 'second date must be later than the first'
        from_date = to_date = None
    entries = get_entries(from_date, to_date)
    return jsonify_template('entries.html', entries=entries, filter_error=error)

def update_weekly(date):
    '''Calculate weekly summary and store in db'''
    day_of_week = date.weekday()
    week_start = date - timedelta(days=day_of_week)
    week_end = week_start + timedelta(days=7)
    db = get_db()
    db.execute('''insert or replace
                  into weekly(uid,week_start,avg_speed,total_distance)
                    select ?, ?,
                           3600*sum(distance)/sum(time),
                           sum(distance)
                    from entries
                    where uid=? and date>=? and date<?''',
               [g.user['uid'],
                mktime(week_start.timetuple()),
                g.user['uid'],
                mktime(week_start.timetuple()),
                mktime(week_end.timetuple())])
    db.commit()

app.run()
