import os
import joggr
import unittest
import tempfile

class JoggrTestCase(unittest.TestCase):

    api_base = '/api/v1/'
    email = 'me@example.com'
    passwd = 'passw0rd'

    entries = [
        {'date': '2014-06-17', 'distance': '10', 'time': '30:00'},
        {'date': '2014-06-19', 'distance': '10', 'time': '45:00'},
        ]
    def setUp(self):
        self.db_fd, joggr.app.config['DATABASE'] = tempfile.mkstemp()
        joggr.app.config['TESTING'] = True
        self.app = joggr.app.test_client()
        joggr.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(joggr.app.config['DATABASE'])

    def api(self, cmd):
        return self.app.get(self.api_base + cmd)

    def test_main(self):
        rv = self.app.get('/')
        assert 'Loading' in rv.data

    def test_empty_list(self):
        rv = self.api('entries/list')
        assert 'Welcome to the Joggr' in rv.data

    def register(self, email, password, password2=None):
        return self.app.post(self.api_base + 'users/register',
                             data=dict(
                                 email=email,
                                 password=password,
                                 password2=password2 or password
                             ), follow_redirects=True)
    def login(self, email, password):
        return self.app.post(self.api_base + 'users/login',
                             data=dict(
                                 email=email,
                                 password=password
                             ), follow_redirects=True)
    def logout(self):
        return self.app.post(self.api_base + 'users/logout',
                             follow_redirects=True)

    def setup_user(self):
        self.register(self.email, self.passwd)
        self.login(self.email, self.passwd)

    def test_signup(self):
        rv = self.register(self.email, self.passwd, self.passwd + 'x')
        assert 'two passwords do not match' in rv.data
        rv = self.register('email', self.passwd)
        assert 'valid email address' in rv.data
        rv = self.register(self.email, '')
        assert 'enter a password' in rv.data
        rv = self.register(self.email, self.passwd)
        assert 'successfully signed up' in rv.data
        rv = self.register(self.email, self.passwd)
        assert 'already registered' in rv.data

    def test_login(self):
        rv = self.register(self.email, self.passwd)
        assert 'successfully signed up' in rv.data
        rv = self.login(self.email, self.passwd)
        assert 'logged in success' in rv.data
        rv = self.logout()
        assert 'logged out' in rv.data
        rv = self.login(self.email + 'x', self.passwd)
        assert 'Invalid email' in rv.data
        rv = self.login(self.email, self.passwd + 'x')
        assert 'Invalid email' in rv.data

    def setup_entries(self):
        self.setup_user()
        for entry in self.entries:
            self.app.post(self.api_base + 'entries/add',
                          data=entry, follow_redirects=True)

    def test_add_entry(self):
        self.setup_user()
        rv = self.app.post(self.api_base + 'entries/add',
                           data=self.entries[0], follow_redirects=True)
        assert 'Entry added' in rv.data
        assert '20.0' in rv.data # avg speed

    def test_weekly(self):
        self.setup_entries()
        rv = self.api('entries/weekly')
        assert '2014-06-16' in rv.data # week start
        assert '20.0' in rv.data # total distance
        assert '16.0' in rv.data # avg speed

    def test_filter(self):
        self.setup_entries()
        rv = self.app.post(self.api_base + 'entries/filter',
                           data={'from': '2014-06-17', 'to': '2014-06-18'})
        assert '2014-06-19' not in rv.data
        assert '2014-06-17' in rv.data
if __name__ == '__main__':
    unittest.main()
