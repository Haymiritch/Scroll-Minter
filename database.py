import sqlite3
import os

class Database:
    def __init__(self, db_path=f"{os.getcwd()}/db/db.sqlite"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()
    
    
    def create_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    private_key VARCHAR(255),
                    line_id INTEGER
                )
            ''')
    
    
    def add_to_db(self, private_key, line_id):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO accounts (private_key, line_id) VALUES (?, ?)", (private_key, line_id,))
    
    
    def truncate_table(self):
        with self.conn:
            self.conn.execute("DELETE FROM accounts")
    
    
    def getLast_line_id(self):
        with self.conn:
            cursor = self.conn.execute("SELECT line_id FROM accounts ORDER BY line_id DESC LIMIT 1;")
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return 0
    
    
    def close(self):
        self.conn.close()
    
    
    
    
    
if __name__ == '__main__':
    db = Database()
    db.create_table()
    db.close()