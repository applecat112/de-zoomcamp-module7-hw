## HOMEWORK SETUP & RUN GUIDE

### 1. Start services
cd 07-streaming/workshop/
docker compose up -d

### 2. Q1 - Check Redpanda version
docker exec -it workshop-redpanda-1 rpk version

### 3. Q2 - Create topic and run producer
docker exec -it workshop-redpanda-1 rpk topic create green-trips
pip install kafka-python pandas pyarrow
python producer.py
# Expected: ~10 seconds

### 4. Q3 - Run consumer
python consumer.py
# Expected: 8506 trips with distance > 5

### 5. Create PostgreSQL tables
docker exec -it workshop-postgres-1 psql -U postgres -c "
CREATE TABLE IF NOT EXISTS tumbling_window_trips (
    window_start TIMESTAMP, PULocationID INT, num_trips BIGINT
);
CREATE TABLE IF NOT EXISTS session_window_trips (
    window_start TIMESTAMP, window_end TIMESTAMP,
    PULocationID INT, num_trips BIGINT
);
CREATE TABLE IF NOT EXISTS hourly_tips (
    window_start TIMESTAMP, total_tip DOUBLE PRECISION
);
"

### 6. Copy Flink job files into the mounted directory
cp job_q4_tumbling_pickup.py 07-streaming/workshop/src/job/
cp job_q5_session_window.py  07-streaming/workshop/src/job/
cp job_q6_hourly_tips.py     07-streaming/workshop/src/job/

### 7. Q4 - Submit tumbling window job
docker exec -it workshop-jobmanager-1 flink run -py /opt/src/job/job_q4_tumbling_pickup.py
# Let run 1-2 minutes, then query:
docker exec -it workshop-postgres-1 psql -U postgres -c "
SELECT PULocationID, num_trips FROM tumbling_window_trips ORDER BY num_trips DESC LIMIT 3;"
# Answer: 74

### 8. Q5 - Submit session window job
docker exec -it workshop-jobmanager-1 flink run -py /opt/src/job/job_q5_session_window.py
docker exec -it workshop-postgres-1 psql -U postgres -c "
SELECT PULocationID, num_trips FROM session_window_trips ORDER BY num_trips DESC LIMIT 3;"
# Answer: 51 trips in longest session

### 9. Q6 - Submit hourly tips job
docker exec -it workshop-jobmanager-1 flink run -py /opt/src/job/job_q6_hourly_tips.py
docker exec -it workshop-postgres-1 psql -U postgres -c "
SELECT window_start, total_tip FROM hourly_tips ORDER BY total_tip DESC LIMIT 3;"
# Answer: 2025-10-01 18:00:00

### Notes:
# - If topic has duplicate data: docker exec -it workshop-redpanda-1 rpk topic delete green-trips
# - Monitor Flink jobs at: http://localhost:8081
# - Cancel jobs from Flink UI after results appear in PostgreSQL