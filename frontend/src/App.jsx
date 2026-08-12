import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  Battery,
  CheckCircle2,
  Cpu,
  Database,
  Gauge,
  RefreshCw,
  Satellite,
  Server,
  Signal,
  Thermometer,
  TriangleAlert,
  Wifi,
  Zap,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";


// ============================================================
// CONFIGURATION
// ============================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SATELLITE_ID = "SAT-001";


// ============================================================
// API CLIENT
// ============================================================

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
});


// ============================================================
// HELPERS
// ============================================================

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }

  return Number(value).toFixed(digits);
}


function formatTime(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleTimeString();
}


function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}


function getStatusClass(status) {
  const normalized = String(status || "").toLowerCase();

  if (normalized === "warning") {
    return "status-warning";
  }

  if (
    normalized === "critical" ||
    normalized === "error"
  ) {
    return "status-critical";
  }

  if (normalized === "ok") {
    return "status-ok";
  }

  return "status-unknown";
}


function getAlertIcon(severity) {
  if (String(severity).toLowerCase() === "critical") {
    return <TriangleAlert size={18} />;
  }

  return <AlertTriangle size={18} />;
}


// ============================================================
// STAT CARD
// ============================================================

function StatCard({
  icon,
  label,
  value,
  unit,
  accent = "blue",
}) {
  return (
    <div className={`stat-card stat-${accent}`}>
      <div className="stat-icon">
        {icon}
      </div>

      <div className="stat-content">
        <div className="stat-label">
          {label}
        </div>

        <div className="stat-value">
          {value}
          {unit && (
            <span className="stat-unit">
              {unit}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}


// ============================================================
// APP
// ============================================================

function App() {
  const [health, setHealth] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [dependencies, setDependencies] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");


  // ==========================================================
  // LOAD DATA
  // ==========================================================

  const loadDashboard = useCallback(async () => {
    try {
      setRefreshing(true);
      setError("");

      const [
        healthResponse,
        telemetryResponse,
        alertsResponse,
        dependenciesResponse,
      ] = await Promise.all([
        api.get(
          `/api/v1/satellites/${SATELLITE_ID}/health`
        ),

        api.get(
          `/api/v1/satellites/${SATELLITE_ID}/telemetry?limit=20`
        ),

        api.get(
          "/api/v1/alerts"
        ),

        api.get(
          `/api/v1/satellites/${SATELLITE_ID}/dependencies`
        ),
      ]);


      // ------------------------------------------------------
      // HEALTH
      // ------------------------------------------------------

      setHealth(
        healthResponse.data?.health || null
      );


      // ------------------------------------------------------
      // TELEMETRY
      // ------------------------------------------------------

      const telemetryItems =
        telemetryResponse.data?.items || [];

      setTelemetry(
        telemetryItems
      );


      // ------------------------------------------------------
      // ALERTS
      // ------------------------------------------------------

      setAlerts(
        alertsResponse.data?.items || []
      );


      // ------------------------------------------------------
      // DEPENDENCIES
      // ------------------------------------------------------

      const dependencyItems =
        dependenciesResponse.data?.dependencies || [];

      setDependencies(
        dependencyItems
      );

    } catch (err) {
      console.error(
        "Dashboard API error:",
        err
      );

      setError(
        "Unable to connect to the telemetry API. Make sure the backend is running on port 8000."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);


  // ==========================================================
  // INITIAL LOAD + AUTO REFRESH
  // ==========================================================

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(
      loadDashboard,
      10000
    );

    return () => {
      clearInterval(interval);
    };
  }, [loadDashboard]);


  // ==========================================================
  // HEALTH VALUES
  // ==========================================================

  const temperature =
    health?.temperature_c ?? null;

  const battery =
    health?.battery_pct ?? null;

  const voltage =
    health?.voltage_v ?? null;

  const cpu =
    health?.cpu_pct ?? null;

  const signal =
    health?.signal_dbm ?? null;

  const status =
    health?.status || "UNKNOWN";


  // ==========================================================
  // CHART DATA
  // ==========================================================

  const chartData = [...telemetry]
    .reverse()
    .map((item, index) => ({
      index: index + 1,
      time: formatTime(item.timestamp),
      temperature: Number(item.temperature_c) || 0,
      battery: Number(item.battery_pct) || 0,
      cpu: Number(item.cpu_pct) || 0,
    }));


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="app-shell">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-logo">
            <Satellite size={26} />
          </div>

          <div>
            <div className="brand-title">
              MISSION CONTROL
            </div>

            <div className="brand-subtitle">
              Space Telemetry Data Platform
            </div>
          </div>

        </div>


        <div className="topbar-right">

          <div className="system-status">
            <span className="online-dot" />
            SYSTEM ONLINE
          </div>

          <button
            className="refresh-button"
            onClick={loadDashboard}
            disabled={refreshing}
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? "spin"
                  : ""
              }
            />

            Refresh
          </button>

        </div>

      </header>


      {/* ====================================================
          ERROR
      ==================================================== */}

      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}


      <main className="dashboard">

        {/* ==================================================
            LIVE TELEMETRY HEADER
        ================================================== */}

        <section className="section-header">

          <div>
            <div className="eyebrow">
              LIVE TELEMETRY
            </div>

            <h1>
              Satellite{" "}
              <span>{SATELLITE_ID}</span>
            </h1>

            <p>
              Real-time spacecraft telemetry and
              mission health monitoring.
            </p>
          </div>


          <div
            className={`large-status ${getStatusClass(status)}`}
          >
            <span className="status-dot" />
            {status}
          </div>

        </section>


        {/* ==================================================
            STAT CARDS
        ================================================== */}

        <section className="stats-grid">

          <StatCard
            icon={<Thermometer size={22} />}
            label="TEMPERATURE"
            value={
              temperature !== null
                ? formatNumber(
                    temperature
                  )
                : "--"
            }
            unit="°C"
            accent="orange"
          />

          <StatCard
            icon={<Battery size={22} />}
            label="BATTERY"
            value={
              battery !== null
                ? formatNumber(
                    battery
                  )
                : "--"
            }
            unit="%"
            accent="green"
          />

          <StatCard
            icon={<Zap size={22} />}
            label="VOLTAGE"
            value={
              voltage !== null
                ? formatNumber(
                    voltage
                  )
                : "--"
            }
            unit="V"
            accent="purple"
          />

          <StatCard
            icon={<Cpu size={22} />}
            label="CPU USAGE"
            value={
              cpu !== null
                ? formatNumber(cpu)
                : "--"
            }
            unit="%"
            accent="blue"
          />

          <StatCard
            icon={<Signal size={22} />}
            label="SIGNAL"
            value={
              signal !== null
                ? formatNumber(signal)
                : "--"
            }
            unit=" dBm"
            accent="cyan"
          />

          <StatCard
            icon={<Database size={22} />}
            label="TELEMETRY"
            value={telemetry.length}
            unit=" records"
            accent="indigo"
          />

        </section>


        {/* ==================================================
            MAIN GRID
        ================================================== */}

        <section className="main-grid">

          {/* =================================================
              TELEMETRY CHART
          ================================================= */}

          <div className="panel chart-panel">

            <div className="panel-header">

              <div>
                <div className="panel-title">
                  Telemetry Trends
                </div>

                <div className="panel-subtitle">
                  Latest telemetry measurements
                </div>
              </div>

              <Activity
                size={20}
                className="panel-icon"
              />

            </div>


            {chartData.length > 0 ? (

              <div className="chart-wrapper">

                <ResponsiveContainer
                  width="100%"
                  height={330}
                >

                  <LineChart
                    data={chartData}
                    margin={{
                      top: 10,
                      right: 20,
                      left: 0,
                      bottom: 10,
                    }}
                  >

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 11 }}
                      interval="preserveStartEnd"
                    />

                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 11 }}
                    />

                    <Tooltip />

                    <Legend />

                    <Line
                      type="monotone"
                      dataKey="temperature"
                      name="Temperature °C"
                      strokeWidth={2}
                      dot={false}
                    />

                    <Line
                      type="monotone"
                      dataKey="battery"
                      name="Battery %"
                      strokeWidth={2}
                      dot={false}
                    />

                    <Line
                      type="monotone"
                      dataKey="cpu"
                      name="CPU %"
                      strokeWidth={2}
                      dot={false}
                    />

                  </LineChart>

                </ResponsiveContainer>

              </div>

            ) : (

              <div className="empty-state">
                <Activity size={36} />
                <span>
                  No telemetry data available.
                </span>
              </div>

            )}

          </div>


          {/* =================================================
              MISSION HEALTH
          ================================================= */}

          <div className="panel health-panel">

            <div className="panel-header">

              <div>
                <div className="panel-title">
                  Mission Health
                </div>

                <div className="panel-subtitle">
                  Current spacecraft snapshot
                </div>
              </div>

              <Gauge
                size={20}
                className="panel-icon"
              />

            </div>


            <div className="health-list">

              <div className="health-row">
                <span>Satellite</span>
                <strong>
                  {SATELLITE_ID}
                </strong>
              </div>

              <div className="health-row">
                <span>Status</span>

                <span
                  className={`badge ${getStatusClass(
                    status
                  )}`}
                >
                  {status}
                </span>
              </div>

              <div className="health-row">
                <span>Last Seen</span>
                <strong>
                  {formatDateTime(
                    health?.last_seen
                  )}
                </strong>
              </div>

              <div className="health-row">
                <span>Temperature</span>
                <strong>
                  {temperature !== null
                    ? `${formatNumber(
                        temperature
                      )}°C`
                    : "--"}
                </strong>
              </div>

              <div className="health-row">
                <span>Battery</span>
                <strong>
                  {battery !== null
                    ? `${formatNumber(
                        battery
                      )}%`
                    : "--"}
                </strong>
              </div>

              <div className="health-row">
                <span>Signal</span>
                <strong>
                  {signal !== null
                    ? `${formatNumber(
                        signal
                      )} dBm`
                    : "--"}
                </strong>
              </div>

            </div>

          </div>

        </section>


        {/* ==================================================
            ALERTS
        ================================================== */}

        <section className="panel">

          <div className="panel-header">

            <div>
              <div className="panel-title">
                Active Alerts
              </div>

              <div className="panel-subtitle">
                Mission anomalies detected
              </div>
            </div>

            <div className="alert-count">
              {alerts.length}
            </div>

          </div>


          {alerts.length === 0 ? (

            <div className="success-state">

              <CheckCircle2 size={32} />

              <div>
                <strong>
                  No active alerts
                </strong>

                <p>
                  All monitored systems are
                  operating normally.
                </p>
              </div>

            </div>

          ) : (

            <div className="alerts-list">

              {alerts.map(
                (alert, index) => (

                  <div
                    className="alert-card"
                    key={
                      `${alert.timestamp}-${index}`
                    }
                  >

                    <div className="alert-icon">
                      {getAlertIcon(
                        alert.severity
                      )}
                    </div>


                    <div className="alert-content">

                      <div className="alert-top">

                        <strong>
                          {alert.type}
                        </strong>

                        <span
                          className={`severity-badge ${
                            String(
                              alert.severity
                            ).toLowerCase() ===
                            "critical"
                              ? "severity-critical"
                              : "severity-warning"
                          }`}
                        >
                          {alert.severity}
                        </span>

                      </div>


                      <div className="alert-details">

                        <span>
                          {alert.satellite_id}
                        </span>

                        <span>
                          Value:{" "}
                          {alert.value}
                        </span>

                        <span>
                          Threshold:{" "}
                          {alert.threshold}
                        </span>

                      </div>


                      <div className="alert-time">
                        {formatDateTime(
                          alert.timestamp
                        )}
                      </div>

                    </div>

                  </div>

                )
              )}

            </div>

          )}

        </section>


        {/* ==================================================
            SENSOR NETWORK
        ================================================== */}

        <section className="panel">

          <div className="panel-header">

            <div>
              <div className="panel-title">
                Sensor Network
              </div>

              <div className="panel-subtitle">
                Neo4j dependency graph
              </div>
            </div>

            <Server
              size={20}
              className="panel-icon"
            />

          </div>


          <div className="sensor-summary">

            <div className="sensor-count">
              {dependencies.length}
            </div>

            <div>
              <strong>
                Connected Sensors
              </strong>

              <p>
                Sensors connected to{" "}
                {SATELLITE_ID}
              </p>
            </div>

          </div>


          {dependencies.length > 0 ? (

            <div className="sensor-grid">

              {dependencies.map(
                (sensor, index) => {

                  const sensorId =
                    sensor.sensor_id ||
                    `SENSOR-${String(
                      index + 1
                    ).padStart(
                      3,
                      "0"
                    )}`;

                  return (

                    <div
                      className="sensor-card"
                      key={sensorId}
                    >

                      <div className="sensor-card-icon">
                        <Wifi size={18} />
                      </div>

                      <div className="sensor-info">

                        <strong>
                          {sensorId}
                        </strong>

                        <span>
                          {sensor.status ||
                            "UNKNOWN"}
                        </span>

                      </div>

                      <div
                        className={`sensor-status ${
                          getStatusClass(
                            sensor.status
                          )
                        }`}
                      >
                        <span className="status-dot" />
                      </div>

                    </div>

                  );
                }
              )}

            </div>

          ) : (

            <div className="empty-state">
              <Server size={36} />
              <span>
                No connected sensors found.
              </span>
            </div>

          )}

        </section>


        {/* ==================================================
            LATEST TELEMETRY
        ================================================== */}

        <section className="panel">

          <div className="panel-header">

            <div>
              <div className="panel-title">
                Latest Telemetry
              </div>

              <div className="panel-subtitle">
                {telemetry.length} records from
                Cassandra/MongoDB pipeline
              </div>
            </div>

            <Database
              size={20}
              className="panel-icon"
            />

          </div>


          {telemetry.length > 0 ? (

            <div className="table-wrapper">

              <table>

                <thead>

                  <tr>
                    <th>Time</th>
                    <th>Sensor</th>
                    <th>Temperature</th>
                    <th>Voltage</th>
                    <th>Battery</th>
                    <th>CPU</th>
                    <th>Signal</th>
                    <th>Status</th>
                  </tr>

                </thead>


                <tbody>

                  {telemetry.map(
                    (item, index) => (

                      <tr
                        key={
                          item.telemetry_id ||
                          index
                        }
                      >

                        <td>
                          {formatTime(
                            item.timestamp
                          )}
                        </td>

                        <td>
                          <span className="sensor-id">
                            {item.sensor_id}
                          </span>
                        </td>

                        <td>
                          {formatNumber(
                            item.temperature_c
                          )}°C
                        </td>

                        <td>
                          {formatNumber(
                            item.voltage_v
                          )}V
                        </td>

                        <td>
                          {formatNumber(
                            item.battery_pct
                          )}%
                        </td>

                        <td>
                          {formatNumber(
                            item.cpu_pct
                          )}%
                        </td>

                        <td>
                          {formatNumber(
                            item.signal_dbm
                          )} dBm
                        </td>

                        <td>

                          <span
                            className={`badge ${getStatusClass(
                              item.status
                            )}`}
                          >
                            {item.status}
                          </span>

                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          ) : (

            <div className="empty-state">
              <Database size={36} />

              <span>
                No telemetry records available.
              </span>
            </div>

          )}

        </section>


        {/* ==================================================
            FOOTER
        ================================================== */}

        <footer className="footer">

          <div>
            <span className="online-dot" />
            Telemetry platform operational
          </div>

          <div>
            Last updated:{" "}
            {new Date().toLocaleTimeString()}
          </div>

        </footer>

      </main>

    </div>
  );
}


export default App;
