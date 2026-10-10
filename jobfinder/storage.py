"""SQLite cache: remembers descriptions (so they are fetched once), first-seen dates and LLM verdicts."""
import json
import sqlite3
from datetime import date


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            source TEXT, ext_id TEXT, url TEXT, title TEXT, company TEXT, location TEXT, city TEXT,
            posted TEXT, description TEXT, first_seen TEXT, last_seen TEXT, llm TEXT, status TEXT DEFAULT '',
            PRIMARY KEY (source, ext_id))""")
        self.db.commit()

    def upsert(self, job):
        today = date.today().isoformat()
        row = self.db.execute("SELECT description, first_seen, llm, status FROM jobs WHERE source=? AND ext_id=?",
                              (job["source"], job["ext_id"])).fetchone()
        if row:
            job.setdefault("description", row[0])
            job["first_seen"], job["status"] = row[1], row[3]
            job["llm"] = json.loads(row[2]) if row[2] else None
            self.db.execute("UPDATE jobs SET last_seen=?, title=?, company=?, location=?, city=?, posted=? "
                            "WHERE source=? AND ext_id=?",
                            (today, job["title"], job["company"], job["location"], job["city"], job["posted"],
                             job["source"], job["ext_id"]))
        else:
            job.update(first_seen=today, status="", llm=None)
            self.db.execute("INSERT INTO jobs (source, ext_id, url, title, company, location, city, posted, "
                            "description, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (job["source"], job["ext_id"], job["url"], job["title"], job["company"], job["location"],
                             job["city"], job["posted"], job.get("description"), today, today))
        self.db.commit()

    def set_description(self, job):
        self.db.execute("UPDATE jobs SET description=? WHERE source=? AND ext_id=?",
                        (job["description"], job["source"], job["ext_id"]))
        self.db.commit()

    def set_llm(self, job):
        self.db.execute("UPDATE jobs SET llm=? WHERE source=? AND ext_id=?",
                        (json.dumps(job["llm"]), job["source"], job["ext_id"]))
        self.db.commit()
