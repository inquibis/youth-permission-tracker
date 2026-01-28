class DBSetup:
    def __init__(self, db_connection):
        self.conn = db_connection

    def create_tables(self):
        # Core tables
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interest_survey (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youth_id TEXT NOT NULL,
                interests TEXT NOT NULL,      -- JSON string
                org_group TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_interest_survey_group ON interest_survey(org_group);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_interest_survey_youth_id ON interest_survey(youth_id);")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS concern_survey (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concerns TEXT NOT NULL,       -- JSON string
                org_group TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_concern_survey_group ON concern_survey(org_group);")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                org_group TEXT NOT NULL,
                user_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username);")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # Stores the medical release submission payloads (JSON blobs)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youth_medical (
                youth_id TEXT PRIMARY KEY,
                permission_code TEXT NOT NULL,
                youth TEXT NOT NULL,
                parent_guardian TEXT NOT NULL,
                medical TEXT NOT NULL,
                emergency_contact TEXT NOT NULL,
                signature TEXT NOT NULL,
                signed_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT
                youth_id TEXT UNIQUE NOT NULL
            );
            """
        )

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_youth_medical_permission_code ON youth_medical(permission_code);")

        # Activities table (matches your create_activity insert pattern)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id TEXT UNIQUE,
                activity_name TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                budget TEXT,
                total_cost REAL,
                actual_cost REAL,
                participants_youth_ids TEXT,
                groups TEXT,
                drivers TEXT,
                date_start datetime NOT NULL,
                date_end datetime NOT NULL,
                is_overnight INTEGER,
                is_coed INTEGER,
                requires_permission INTEGER DEFAULT 0,
                thoughts TEXT,
                bishop_approval INTEGER,
                bishop_approval_date TEXT,
                stake_approval INTEGER,
                stake_approval_date TEXT,
                created_at TEXT DEFAULT (datetime('now'))

            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_activity_id ON activities(activity_id);")

        # Permission assignments table (matches your /activity-permissions endpoint)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_given (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youth_id TEXT,
                activity_id TEXT,
                permission_code TEXT,
                data JSON,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_activity_id ON permission_given(activity_id);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_youth_id ON permission_given(youth_id);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_permission_given_permission_code ON permission_given(permission_code);")

        # Personal goals table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT UNIQUE,
                youth_id TEXT NOT NULL,
                goal_area TEXT NOT NULL,
                goal_name TEXT NOT NULL,
                goal_description TEXT NOT NULL,
                target_date datetime NOT NULL,
                status TEXT NOT NULL DEFAULT 'Not Started',
                progress_notes TEXT,
                completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT
                visibility_level TEXT NOT NULL DEFAULT 'private'
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_personal_goals_youth_id ON personal_goals(youth_id);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_personal_goals_goal_area ON personal_goals(goal_area);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_personal_goals_status ON personal_goals(status);")

        # Keep updated_at current on updates (SQLite trigger)
        self.conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_youth_medical_updated_at
            AFTER UPDATE ON youth_medical
            FOR EACH ROW
            BEGIN
                UPDATE youth_medical SET updated_at = datetime('now') WHERE youth_id = NEW.youth_id;
            END;
            """
        )

        # Update trigger for personal goals
        self.conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_personal_goals_updated_at
            AFTER UPDATE ON personal_goals
            FOR EACH ROW
            BEGIN
                UPDATE personal_goals SET updated_at = datetime('now') WHERE id = NEW.id;
            END;
            """
        )

        # ADD AUDIT LOG TABLE
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL DEFAULT (datetime('now')),
                actor_username TEXT,
                actor_role TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                success INTEGER NOT NULL,
                details TEXT,
                client_ip TEXT,
                user_agent TEXT
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_username);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);")

        self.conn.commit()


    def load_admins(self)->None:
        cursor = self.conn.cursor()
        admins = [
            ('deacon_admin', 'password_d', 'president', 'deacons', 'some_user_id_1'),
            ('teacher_admin', 'password_t', 'president', 'teachers', 'some_user_id_2'),
            ('priest_admin', 'password_p', 'president', 'priest', 'some_user_id_3'),
            ('younger_yw_admin', 'password_yyw', 'president', 'younger young women', 'some_user_id_4'),
            ('older_yw_admin', 'password_oya', 'president', 'older young women', 'some_user_id_5'),
            ('bishop_admin', 'password_b', 'bishop', 'ecc_admin', 'some_user_id_6'),
            ('stake_president_admin', 'password_sp', 'president', 'ecc_admin', 'some_user_id_7'),
            ('admin', 'password_admin', 'admin', 'admin', 'some_user_id_8'),
            ('deacon_advisor', 'password_da', 'advisor', 'deacons', 'some_user_id_9'),
            ('teacher_advisor', 'password_ta', 'advisor', 'teachers', 'some_user_id_10'),
            ('priest_advisor', 'password_pa', 'advisor', 'priest', 'some_user_id_11'),
            ('younger_yw_advisor', 'password_yya', 'advisor', 'younger young women', 'some_user_id_12'),
            ('older_yw_advisor', 'password_oya', 'advisor', 'older young women', 'some_user_id_13')
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO admin_users (username, password, role, org_group, user_id)
            VALUES (?, ?, ?, ?, ?)
        ''', admins)
        self.conn.commit()