from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "bdds")

# Use sync engine for schema changes
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def sync_db():
    with engine.connect() as conn:
        print("Detecting column types for compatibility...")
        
        # 1. Check type of bdds_dashboard_form_data.id
        res_form = conn.execute(text("SHOW COLUMNS FROM bdds_dashboard_form_data LIKE 'id'")).fetchone()
        form_id_type = res_form[1] if res_form else "INT"
        print(f"Detected form_data.id type: {form_id_type}")

        # 2. Add is_public column if missing
        print("Checking for is_public column...")
        try:
            conn.execute(text("SELECT is_public FROM bdds_dashboard_form_data LIMIT 1"))
            print("Column 'is_public' already exists.")
        except Exception:
            print("Adding 'is_public' column to bdds_dashboard_form_data...")
            conn.execute(text("ALTER TABLE bdds_dashboard_form_data ADD COLUMN is_public INT DEFAULT 0"))
            conn.commit()

        # 3. Create dossier table
        print("Creating bdds_investigation_dossier table...")
        # We use a standard BIGINT for primary keys of new tables to be safe
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bdds_investigation_dossier (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(200),
                alias VARCHAR(200),
                description TEXT,
                photo_path VARCHAR(255),
                status VARCHAR(50) DEFAULT 'Active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX (name)
            )
        """))
        conn.commit()

        # 4. Check type of bdds_investigation_dossier.id for linking
        res_dossier = conn.execute(text("SHOW COLUMNS FROM bdds_investigation_dossier LIKE 'id'")).fetchone()
        dossier_id_type = res_dossier[1] if res_dossier else "INT"
        print(f"Detected dossier.id type: {dossier_id_type}")

        # 5. Create linkage table with EXACT MATCHING TYPES
        print(f"Creating bdds_investigation_link table with types: form_id({form_id_type}), criminal_id({dossier_id_type})")
        
        # We drop if exists to ensure we get the right types this time (only if empty)
        # But safest is to just try creating it with the right types.
        # Since it failed previously, it likely wasn't created.
        
        create_link_query = f"""
            CREATE TABLE IF NOT EXISTS bdds_investigation_link (
                id INT AUTO_INCREMENT PRIMARY KEY,
                form_id {form_id_type},
                criminal_id {dossier_id_type},
                role VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (form_id) REFERENCES bdds_dashboard_form_data(id),
                FOREIGN KEY (criminal_id) REFERENCES bdds_investigation_dossier(id)
            )
        """
        
        try:
            conn.execute(text(create_link_query))
            conn.commit()
            print("Table bdds_investigation_link created successfully.")
        except Exception as e:
            print(f"Error creating link table: {e}")
            print("Attempting to fix by dropping and recreating (if no data exists)...")
            conn.execute(text("DROP TABLE IF EXISTS bdds_investigation_link")) # In case it's half-baked
            conn.commit()
            conn.execute(text(create_link_query))
            conn.commit()
            print("Table bdds_investigation_link recovered and created.")

        print("Database sync complete.")

if __name__ == "__main__":
    sync_db()
