# cron.py
import core
import traceback

# Create the panel instance, which opens a database connection
co = core.CandyPanel()

try:
    # Run the synchronization process
    print("Starting sync process...")
    co._sync()
    print("Sync process completed successfully.")
except Exception as e:
    # Log any errors that occur during the sync
    print(f"An error occurred during sync: {e}")
    traceback.print_exc()
finally:
    # This block will run whether the sync succeeds or fails
    if hasattr(co, 'db') and co.db.conn is not None:
        print("Closing database connection.")
        co.db.close()
    else:
        print("Database connection was not open or already closed.")
