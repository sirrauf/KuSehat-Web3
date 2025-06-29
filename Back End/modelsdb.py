# models.py
from pony.orm import Database, Required, Json, PrimaryKey, Set
from config import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)

class User(db.Entity):
    id = PrimaryKey(int, auto=True)
    username = Required(str, unique=True)
    password = Required(str)
    checklists = Set('Checklist')

class Checklist(db.Entity):
    id = PrimaryKey(int, auto=True)
    title = Required(str)
    user = Required(User)
    items = Set('Item')

class Item(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Required(str)
    completed = Required(bool, default=False)
    checklist = Required(Checklist)

db.generate_mapping(create_tables=True)