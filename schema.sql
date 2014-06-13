drop table if exists users;
create table users(
  uid integer primary key autoincrement,
  email text unique not null,
  pwhash text
);

drop table if exists entries;
create table entries(
  uid integer not null,
  date integer not null,
  distance real,
  time integer not null,
  foreign key(uid) references users(uid)
);
create index uid_date on entries (uid,date);

drop table if exists weekly;
create table weekly(
  uid integer not null,
  week_start integer not null,
  avg_speed real,
  total_distance real,
  foreign key(uid) references users(uid)
);
create unique index uid_week on weekly(uid,week_start);
