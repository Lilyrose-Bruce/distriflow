"""Settings for DistriFlow, read from environment variables / the .env file."""
import os

from dotenv import load_dotenv

# Reads the .env file (if there is one) into environment variables.
load_dotenv()

# If DATABASE_URL is missing we fall back to a local SQLite file (development).
DATABASE_URL = os.getenv("DATABASE_URL") 

# Used to sign login tokens. The default is ONLY for development.
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Minutes of inactivity before the session ends.
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES"))

BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS"))

# Name of the cookie that holds the login token in the browser.
COOKIE_NAME = "access_token"
COOKIE_SECURE = False

# The only two roles in the system.
ROLE_ADMIN = "Administrator"
ROLE_DISPATCHER = "Dispatcher"

# --- Depot: where every truck starts and finishes ---------------------------
# The report does not say where the depot is, so it is a setting. CHANGE THESE in .env.
DEPOT_NAME = os.getenv("DEPOT_NAME")
DEPOT_LATITUDE = float(os.getenv("DEPOT_LATITUDE"))
DEPOT_LONGITUDE = float(os.getenv("DEPOT_LONGITUDE"))

# --- Planning assumptions ---------------------------------------------------
DEPARTURE_TIME_MINUTES = int(os.getenv("DEPARTURE_TIME_MINUTES"))        # 420 = 07:00
SERVICE_MINUTES_PER_STOP = int(os.getenv("SERVICE_MINUTES_PER_STOP"))     # time spent offloading
MAX_STOPS = int(os.getenv("MAX_STOPS"))                                   # "up to 30 stops" (requirement)
OPTIMIZER_MAX_SECONDS = int(os.getenv("OPTIMIZER_MAX_SECONDS"))           # solver time limit

# --- OSRM (road distances and travel times) ---------------------------------
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL")
OSRM_TIMEOUT_SECONDS = int(os.getenv("OSRM_TIMEOUT_SECONDS"))

# --- Order file upload limits -----------------------------------------------
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB"))
MAX_UPLOAD_ROWS = int(os.getenv("MAX_UPLOAD_ROWS"))
