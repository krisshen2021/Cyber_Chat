import sqlite3
from datetime import datetime
import json

class SQLiteDB:
    def __init__(self):
        pass

    def create_table(self):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                UNIQUE_ID INTEGER PRIMARY KEY,
                Name TEXT UNIQUE,
                Nickname TEXT,
                Gender TEXT,
                Password TEXT,
                Email TEXT UNIQUE,
                Credits INTEGER,
                Avatar TEXT,
                Facelooks TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_records (
                Record_ID INTEGER PRIMARY KEY,
                UNIQUE_ID INTEGER,
                Timestamp DATETIME,
                Content TEXT,
                Character TEXT,
                FOREIGN KEY (UNIQUE_ID) REFERENCES users (UNIQUE_ID)
            )
        ''')
        self.conn.commit()
        self.conn.close()

    def create_new_user(self, username: str, nickname:str, gender: str, password: str, email: str, credits: int, avatar:str, facelooks:str):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        try:
            user_query = '''
                INSERT INTO users (Name, Nickname, Gender, Password, Email, Credits, Avatar, Facelooks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            self.cursor.execute(user_query, (username, nickname, gender, password, email, credits, avatar, facelooks))
        except sqlite3.IntegrityError as e:
            error_message = str(e)
            if "Name" in error_message:
                return "Username already exists"
            elif "Email" in error_message:
                return "Email already exists"
            else:
                return "Unknown_Errors"
        else:
            self.conn.commit()
            return True
        finally:
            self.conn.close()

    def get_user(self, username: str, password:str):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            user_query = "SELECT * FROM users WHERE Name = ? AND Password = ?"
            result = self.cursor.execute(user_query, (username,password)).fetchone()
            if result:
                keys = ["unique_id", "username", "nickname", "gender", "password", "email", "credits", "avatar", "facelooks"]
                user = dict(zip(keys, result))
                self.conn.close()
                return user
            else:
                self.conn.close()
                return "Password is not matched"
        else:
            print("没有找到用户")
            self.conn.close()
            return "User is not available"

    def save_chat_records(self, username: str, character: str, chat_data: list):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        content = json.dumps(chat_data)
        timestamp = datetime.now().replace(microsecond=0)
        unique_id = self.get_unique_id(username)
        if unique_id:
            if self.chat_history_exists(unique_id, character):
                self.cursor.execute("UPDATE chat_records SET Content = ?, Timestamp = ? WHERE UNIQUE_ID = ? AND Character = ?", (content, timestamp, unique_id, character))
            else:
                self.cursor.execute('''
                    INSERT INTO chat_records (UNIQUE_ID, Timestamp, Content, Character)
                    VALUES (?, ?, ?, ?)
                ''', (unique_id, timestamp, content, character))

            self.conn.commit()
            self.conn.close()
            return True
        else:
            print("没有找到用户")
            self.conn.close()
            return False
        
    def delete_chat_records(self, username: str, character: str):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            if self.chat_history_exists(unique_id, character):
                try:
                    self.cursor.execute("DELETE FROM chat_records WHERE UNIQUE_ID = ? AND Character = ?",(unique_id, character))
                except sqlite3.OperationalError as e:
                    print("删除出错: ", e)
                else:
                    self.conn.commit()
                    return True
                finally:
                    self.conn.close()
            else:
                print("没有此记录")
                self.conn.close()
                return False
        else:
            print("没有找到用户")
            self.conn.close()
            return False

    def get_chat_records(self, username: str, character: str):
        self.conn = sqlite3.connect("cyberchat.db")
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            query = "SELECT Content, Timestamp FROM chat_records WHERE UNIQUE_ID = ? AND Character = ? ORDER BY Timestamp DESC"
            result = self.cursor.execute(query, (unique_id, character)).fetchall()
            self.conn.close()     
            if result:
                chat_records = [{"content": json.loads(row[0]), "timestamp": row[1]} for row in result]
                return chat_records
            else:
                return False
        else:
            print("没有找到用户")
            self.conn.close()
            return False

    def get_unique_id(self, username: str):
        result = self.cursor.execute("SELECT UNIQUE_ID FROM users WHERE Name = ?", (username,)).fetchone()
        return result[0] if result else None

    def chat_history_exists(self, unique_id: int, character: str):
        result = self.cursor.execute("SELECT Character FROM chat_records WHERE UNIQUE_ID = ? AND Character = ?", (unique_id, character)).fetchone()
        return result is not None
