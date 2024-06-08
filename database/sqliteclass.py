import sqlite3
from datetime import datetime
import json


class SQLiteDB:
    def __init__(self, database: str):
        self.database = database

    @staticmethod
    def is_boolean_field(field_name):
        return field_name.startswith("is_") or field_name.startswith("has_")
    
    @staticmethod
    def is_json_field(field_name):
        return field_name.startswith("json_")

    @staticmethod
    def convert_to_pyType(data:dict):
        for key, value in data.items():
            if SQLiteDB.is_boolean_field(key):
                data[key] = bool(value)
            if SQLiteDB.is_json_field(key):
                data[key] = json.loads(data[key])
        return data

    def create_table(self):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
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
        """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS airoles (
                UNIQUE_ID INTEGER PRIMARY KEY,
                Name TEXT UNIQUE,
                Ai_name TEXT,
                Ai_speaker TEXT,
                Ai_speaker_en TEXT,
                is_Uncensored BOOLEAN,
                Prologue TEXT,
                Char_Persona TEXT,
                User_Persona TEXT,
                json_Chapters TEXT,
                Char_looks TEXT,
                json_Char_outfit TEXT,
                Char_avatar TEXT,
                Default_bg TEXT,
                Firstwords TEXT,
                is_Gen_DynaPic BOOLEAN,
                Prompt_to_load TEXT,
                Match_words_cata TEXT,
                json_Completions_data TEXT,
                Creator_ID INTEGER,
                Story_intro TEXT DEFAULT 'A fiction RolePlay unlease wild imagination',
                FOREIGN KEY (Creator_ID) REFERENCES users (UNIQUE_ID)
            )
        """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_records (
                Record_ID INTEGER PRIMARY KEY,
                UNIQUE_ID INTEGER,
                Timestamp DATETIME,
                Content TEXT,
                Character TEXT,
                FOREIGN KEY (UNIQUE_ID) REFERENCES users (UNIQUE_ID)
            )
        """
        )
        self.conn.commit()
        self.conn.close()

    def create_new_airole(
        self,
        airole: dict,
    ):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        try:
            user_query = """
            INSERT INTO airoles (Name, Ai_name, Ai_speaker, Ai_speaker_en, is_Uncensored, Prologue, Char_Persona, User_Persona, json_Chapters, Char_looks, json_Char_outfit, Char_avatar, Default_bg, Firstwords, is_Gen_DynaPic, Prompt_to_load, Match_words_cata, json_Completions_data, Creator_ID, Story_intro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            # self.cursor.execute(
            #     user_query,
            #     (
            #         airole["Name"],
            #         airole["Ai_name"],
            #         airole["Ai_speaker"],
            #         airole["Ai_speaker_en"],
            #         airole["is_Uncensored"],
            #         airole["Prologue"],
            #         airole["Char_Persona"],
            #         airole["User_Persona"],
            #         airole["json_Chapters"],
            #         airole["Char_looks"],
            #         airole["json_Char_outfit"],
            #         airole["Char_avatar"],
            #         airole["Default_bg"],
            #         airole["Firstwords"],
            #         airole["is_Gen_DynaPic"],
            #         airole["Prompt_to_load"],
            #         airole["Match_words_cata"],
            #         airole["json_Completions_data"],
            #         airole["Creator_ID"],
            #         airole["Story_intro"],
            #     ),
            # )
            values = tuple(airole.values())
            self.cursor.execute(user_query, values)
        except sqlite3.IntegrityError as e:
            error_message = str(e)
            if "Name" in error_message:
                return "airole already exists"
            else:
                return f"Database error: {error_message}"
        else:
            self.conn.commit()
            return True
        finally:
            self.conn.close()

    def edit_airole(self, airole):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        try:
            user_query = """
            UPDATE airoles SET Ai_name = ?, Ai_speaker = ?, Ai_speaker_en = ?, is_Uncensored = ?, Prologue = ?, Char_Persona = ?, User_Persona = ?, json_Chapters = ?, Char_looks = ?, json_Char_outfit = ?, Char_avatar = ?, Default_bg = ?, Firstwords = ?, is_Gen_DynaPic = ?, Prompt_to_load = ?, Match_words_cata = ?, json_Completions_data = ?, Creator_ID = ?, Story_intro = ? WHERE Name = ?
            """
            self.cursor.execute(
                user_query,
                (
                    airole["Ai_name"],
                    airole["Ai_speaker"],
                    airole["Ai_speaker_en"],
                    airole["is_Uncensored"],
                    airole["Prologue"],
                    airole["Char_Persona"],
                    airole["User_Persona"],
                    airole["json_Chapters"],
                    airole["Char_looks"],
                    airole["json_Char_outfit"],
                    airole["Char_avatar"],
                    airole["Default_bg"],
                    airole["Firstwords"],
                    airole["is_Gen_DynaPic"],
                    airole["Prompt_to_load"],
                    airole["Match_words_cata"],
                    airole["json_Completions_data"],
                    airole["Creator_ID"],
                    airole["Story_intro"],
                    airole["Name"],
                ),
            )
        except sqlite3.IntegrityError as e:
            error_message = str(e)
            if "Name" in error_message:
                return "airole already exists"
            else:
                return f"Database error: {error_message}"
        else:
            self.conn.commit()
            return True
        finally:
            self.conn.close()

    def get_airole(self, Name):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        user_query = "SELECT * FROM airoles WHERE Name = ?"
        result = self.cursor.execute(user_query, (Name,)).fetchone()
        if result:
            keys = [
                "UNIQUE_ID",
                "Name",
                "Ai_name",
                "Ai_speaker",
                "Ai_speaker_en",
                "is_Uncensored",
                "Prologue",
                "Char_Persona",
                "User_Persona",
                "json_Chapters",
                "Char_looks",
                "json_Char_outfit",
                "Char_avatar",
                "Default_bg",
                "Firstwords",
                "is_Gen_DynaPic",
                "Prompt_to_load",
                "Match_words_cata",
                "json_Completions_data",
                "Creator_ID",
                "Story_intro",
            ]
            airole_data = SQLiteDB.convert_to_pyType(dict(zip(keys, result)))
            self.conn.close()
            return airole_data
        else:
            self.conn.close()
            return "airole not found"
    
    def list_data_airole(self, data_list:list):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        data_to_select = ", ".join(data_list)
        user_query = f"SELECT {data_to_select} FROM airoles"
        result = self.cursor.execute(user_query).fetchall()
        if result:
            airole_data = []
            for row in result:
                airole_data.append(SQLiteDB.convert_to_pyType(dict(zip(data_list, row))))
            # airole_data = SQLiteDB.convert_to_pyType(dict(zip(keys, result)))
            self.conn.close()
            return airole_data
        else:
            self.conn.close()
            return "data not found"
        
    def del_airole(self, Name:str):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        try:
            user_query = "DELETE FROM airoles WHERE Name = ?"
            self.cursor.execute(user_query,(Name,))
        except sqlite3.IntegrityError as e:
            return(str(e))
        else:
            self.conn.commit()
            return True
        finally:
            self.conn.close()

    def create_new_user(
        self,
        username: str,
        nickname: str,
        gender: str,
        password: str,
        email: str,
        credits: int,
        avatar: str,
        facelooks: str,
    ):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        try:
            user_query = """
                INSERT INTO users (Name, Nickname, Gender, Password, Email, Credits, Avatar, Facelooks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(
                user_query,
                (
                    username,
                    nickname,
                    gender,
                    password,
                    email,
                    credits,
                    avatar,
                    facelooks,
                ),
            )
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

    def edit_user(
        self,
        username: str,
        nickname: str,
        gender: str,
        email: str,
        avatar: str,
        facelooks: str,
    ):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        try:
            user_query = """
                UPDATE users SET Nickname = ?, Gender = ?, Email = ?, Avatar = ?, Facelooks = ? WHERE Name = ?
            """
            self.cursor.execute(
                user_query, (nickname, gender, email, avatar, facelooks, username)
            )
        except sqlite3.IntegrityError as e:
            error_message = str(e)
            if "Email" in error_message:
                return "Email already exists"
            else:
                return "Unknown_Errors"
        else:
            self.conn.commit()
            return True
        finally:
            self.conn.close()

    def get_user(
        self, username: str = "admin", password: str = "admin", needpassword=True
    ):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            if needpassword:
                user_query = "SELECT * FROM users WHERE Name = ? AND Password = ?"
                result = self.cursor.execute(
                    user_query, (username, password)
                ).fetchone()
            else:
                user_query = f"SELECT * FROM users WHERE Name = ?"
                result = self.cursor.execute(user_query, (username,)).fetchone()
            if result:
                keys = [
                    "unique_id",
                    "username",
                    "nickname",
                    "gender",
                    "password",
                    "email",
                    "credits",
                    "avatar",
                    "facelooks",
                ]
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
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        content = json.dumps(chat_data)
        timestamp = datetime.now().replace(microsecond=0)
        unique_id = self.get_unique_id(username)
        if unique_id:
            if self.chat_history_exists(unique_id, character):
                self.cursor.execute(
                    "UPDATE chat_records SET Content = ?, Timestamp = ? WHERE UNIQUE_ID = ? AND Character = ?",
                    (content, timestamp, unique_id, character),
                )
            else:
                self.cursor.execute(
                    """
                    INSERT INTO chat_records (UNIQUE_ID, Timestamp, Content, Character)
                    VALUES (?, ?, ?, ?)
                """,
                    (unique_id, timestamp, content, character),
                )

            self.conn.commit()
            self.conn.close()
            return True
        else:
            print("没有找到用户")
            self.conn.close()
            return False

    def delete_chat_records(self, username: str, character: str):
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            if self.chat_history_exists(unique_id, character):
                try:
                    self.cursor.execute(
                        "DELETE FROM chat_records WHERE UNIQUE_ID = ? AND Character = ?",
                        (unique_id, character),
                    )
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
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        unique_id = self.get_unique_id(username)
        if unique_id:
            query = "SELECT Content, Timestamp FROM chat_records WHERE UNIQUE_ID = ? AND Character = ? ORDER BY Timestamp DESC"
            result = self.cursor.execute(query, (unique_id, character)).fetchall()
            self.conn.close()
            if result:
                chat_records = [
                    {"content": json.loads(row[0]), "timestamp": row[1]}
                    for row in result
                ]
                return chat_records
            else:
                return False
        else:
            print("没有找到用户")
            self.conn.close()
            return False

    def get_unique_id(self, username: str):
        result = self.cursor.execute(
            "SELECT UNIQUE_ID FROM users WHERE Name = ?", (username,)
        ).fetchone()
        return result[0] if result else None

    def chat_history_exists(self, unique_id: int, character: str):
        result = self.cursor.execute(
            "SELECT Character FROM chat_records WHERE UNIQUE_ID = ? AND Character = ?",
            (unique_id, character),
        ).fetchone()
        return result is not None
