from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
tenv = StreamTableEnvironment.create(env, environment_settings=settings)

# Add required JARs (adjust paths if needed inside the container)
tenv.get_config().get_configuration().set_string(
    "pipeline.jars",
    "file:///opt/flink/lib/flink-connector-kafka-3.1.0-1.18.jar;"
    "file:///opt/flink/lib/flink-sql-connector-kafka-3.1.0-1.18.jar;"
    "file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar;"
    "file:///opt/flink/lib/postgresql-42.7.3.jar"
)

# Source DDL: read from Kafka
tenv.execute_sql("""
CREATE TABLE green_trips (
    lpep_pickup_datetime VARCHAR,
    lpep_dropoff_datetime VARCHAR,
    PULocationID INT,
    DOLocationID INT,
    passenger_count DOUBLE,
    trip_distance DOUBLE,
    tip_amount DOUBLE,
    total_amount DOUBLE,
    event_timestamp AS TO_TIMESTAMP(lpep_pickup_datetime, 'yyyy-MM-dd HH:mm:ss'),
    WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'green-trips',
    'properties.bootstrap.servers' = 'redpanda:29092',
    'properties.group.id' = 'flink-green-q4',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
)
""")

# Sink DDL: write to PostgreSQL
tenv.execute_sql("""
CREATE TABLE tumbling_window_trips (
    window_start TIMESTAMP(3),
    PULocationID INT,
    num_trips BIGINT
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/postgres',
    'table-name' = 'tumbling_window_trips',
    'username' = 'postgres',
    'password' = 'postgres'
)
""")

# Query: 5-minute tumbling window, count trips per PULocationID
tenv.execute_sql("""
INSERT INTO tumbling_window_trips
SELECT
    TUMBLE_START(event_timestamp, INTERVAL '5' MINUTE) AS window_start,
    PULocationID,
    COUNT(*) AS num_trips
FROM green_trips
GROUP BY
    TUMBLE(event_timestamp, INTERVAL '5' MINUTE),
    PULocationID
""").wait()
