import serial
import time
import mysql.connector
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

# ─── RULES (can be changed via web interface) ─────────────
TEMP_THRESHOLD = 30.0      # Celsius - trigger alert if above
HUMIDITY_THRESHOLD = 70.0  # % - trigger alert if above
LIGHT_THRESHOLD = 20       # % - trigger alert if below (too dark)

# ─── DATABASE SETUP ───────────────────────────────────────
def setup_database():
    conn = mysql.connector.connect(
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
            temperature FLOAT NOT NULL,
            humidity FLOAT NOT NULL,
            light_level INT NOT NULL,
            led_status BOOLEAN DEFAULT FALSE,
            buzzer_status BOOLEAN DEFAULT FALSE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            temp_threshold FLOAT DEFAULT 30.0,
            humidity_threshold FLOAT DEFAULT 70.0,
            light_threshold INT DEFAULT 20,
            updated_at DATETIME
        )
    """)
    # Insert default rule if not exists
    cursor.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("""
            INSERT INTO rules (temp_threshold, humidity_threshold, light_threshold, updated_at)
            VALUES (30.0, 70.0, 20, NOW())
        """)
    conn.commit()
    conn.close()
    print("✅ Database setup complete")

def get_rules():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rules ORDER BY id DESC LIMIT 1")
    rule = cursor.fetchone()
    conn.close()
    return rule

def save_to_db(temperature, humidity, light_level, led_on, buzzer_on):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_data (timestamp, temperature, humidity, light_level, led_status, buzzer_status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (datetime.now(), temperature, humidity, light_level, led_on, buzzer_on))
    conn.commit()
    conn.close()

# ─── ANALYTICS RULE ENGINE ────────────────────────────────
def apply_rules(ser, temperature, humidity, light_level):
    rules = get_rules()
    led_on = False
    buzzer_on = False

    # Rule 1: Temperature too high → LED + Buzzer alert
    if temperature > rules['temp_threshold']:
        print(f"🌡️  ALERT: Temp {temperature}°C > {rules['temp_threshold']}°C → Activating LED + Buzzer")
        ser.write(b"LED_ON\n")
        time.sleep(0.1)
        ser.write(b"BUZZER_ON\n")
        led_on = True
        buzzer_on = True

    # Rule 2: Humidity too high → LED alert only
    elif humidity > rules['humidity_threshold']:
        print(f"💧 ALERT: Humidity {humidity}% > {rules['humidity_threshold']}% → Activating LED")
        ser.write(b"LED_ON\n")
        led_on = True

    # Rule 3: Light too low (dark room) → LED on as night light
    elif light_level < rules['light_threshold']:
        print(f"💡 ALERT: Light {light_level}% < {rules['light_threshold']}% → Activating LED (night light)")
        ser.write(b"LED_ON\n")
        led_on = True

    # All normal → turn off
    else:
        print(f"✅ All readings normal → Actuators OFF")
        ser.write(b"ALL_OFF\n")

    return led_on, buzzer_on

# ─── MAIN LOOP ────────────────────────────────────────────
def main():
    print("🏠 Smart Home Edge Server Starting...")
    setup_database()

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"✅ Connected to Arduino on {SERIAL_PORT}")
        time.sleep(2)  # Wait for Arduino to initialize
    except Exception as e:
        print(f"❌ Cannot connect to Arduino: {e}")
        print("Check that Arduino is connected and port is correct")
        return

    print("📡 Reading sensor data... (Press Ctrl+C to stop)\n")

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()

            if not line or line.startswith('ERROR'):
                print(f"⚠️  Skipping: {line}")
                continue

            # Parse CSV: temperature,humidity,light
            parts = line.split(',')
            if len(parts) != 3:
                continue

            temperature = float(parts[0])
            humidity = float(parts[1])
            light_level = int(parts[2])

            print(f"📊 Temp: {temperature}°C | Humidity: {humidity}% | Light: {light_level}%")

            # Apply rules and control actuators
            led_on, buzzer_on = apply_rules(ser, temperature, humidity, light_level)

            # Save to database
            save_to_db(temperature, humidity, light_level, led_on, buzzer_on)
            print(f"💾 Saved to database\n")

        except KeyboardInterrupt:
            print("\n👋 Stopping edge server...")
            ser.write(b"ALL_OFF\n")
            ser.close()
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
