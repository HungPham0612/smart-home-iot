import serial
import time
import pymysql
import pymysql.cursors
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
SERIAL_PORT = '/dev/ttyACM0'  # Change to /dev/ttyUSB0 if needed
BAUD_RATE = 9600
DB_CONFIG = {
    'host': 'localhost',
    'user': 'iotuser',
    'password': 'iotpassword',
    'database': 'smarthome'
}

# ─── DATABASE SETUP ───────────────────────────────────────
def setup_database():
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS smarthome")
    cursor.execute("USE smarthome")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            door_open BOOLEAN NOT NULL,
            light_level INT NOT NULL,
            led_status BOOLEAN DEFAULT FALSE,
            buzzer_status BOOLEAN DEFAULT FALSE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            light_threshold INT DEFAULT 30,
            updated_at DATETIME
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO rules (light_threshold, updated_at) VALUES (30, NOW())")
    conn.commit()
    conn.close()
    print("✅ Database setup complete")

def get_rules():
    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules ORDER BY id DESC LIMIT 1")
    rule = cursor.fetchone()
    conn.close()
    return rule

def save_to_db(door_open, light_level, led_on, buzzer_on):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_data (timestamp, door_open, light_level, led_status, buzzer_status)
        VALUES (%s, %s, %s, %s, %s)
    """, (datetime.now(), door_open, light_level, led_on, buzzer_on))
    conn.commit()
    conn.close()

def apply_rules(ser, door_open, light_level):
    rules = get_rules()
    led_on = False
    buzzer_on = False

    if door_open == 1:
        print(f"ALERT: Door OPEN -> LED + Buzzer ON")
        ser.write(b"LED_ON\n")
        time.sleep(0.1)
        ser.write(b"BUZZER_ON\n")
        led_on = True
        buzzer_on = True
    elif light_level < rules['light_threshold']:
        print(f"ALERT: Light {light_level}% low -> LED ON")
        ser.write(b"LED_ON\n")
        led_on = True
    else:
        print(f"Normal -> ALL OFF")
        ser.write(b"ALL_OFF\n")

    return led_on, buzzer_on

def main():
    print("Smart Home Edge Server Starting...")
    setup_database()

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"Connected to Arduino on {SERIAL_PORT}")
        time.sleep(2)
    except Exception as e:
        print(f"Cannot connect to Arduino: {e}")
        return

    print("Reading sensor data... (Ctrl+C to stop)\n")

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line or ',' not in line:
                continue

            parts = line.split(',')
            if len(parts) != 2:
                continue

            door_open = int(parts[0])
            light_level = int(parts[1])

            status = "OPEN" if door_open else "CLOSED"
            print(f"Door: {status} | Light: {light_level}%")

            led_on, buzzer_on = apply_rules(ser, door_open, light_level)
            save_to_db(door_open, light_level, led_on, buzzer_on)
            print(f"Saved to database\n")

        except KeyboardInterrupt:
            print("\nStopping...")
            ser.write(b"ALL_OFF\n")
            ser.close()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()