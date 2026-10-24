module.exports = {
  apps: [{
    name: '24xs-hidden-daemon',
    script: './scripts/hidden/hidden_daemon.mjs',
    cwd: process.cwd(),
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_restarts: 9999,
    restart_delay: 10000,           // 10s delay between restarts
    kill_timeout: 5000,             // 5s graceful shutdown
    max_memory_restart: '1G',       // Restart if memory exceeds 1GB
    env: {
      NODE_ENV: 'production',
      HIDDEN_INT_MIN: '15'
    },
    // Log configuration
    error_file: './autoops/hidden/log/pm2-error.log',
    out_file: './autoops/hidden/log/pm2-out.log',
    log_file: './autoops/hidden/log/pm2-combined.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    // Process management
    listen_timeout: 30000,
    // Restart on crash
    min_uptime: '60s',              // Must stay up at least 60s to be considered stable
    // Post-deploy hook (optional)
    post_update: ['npm install --omit=dev', 'echo "Deploy completed"']
  }]
};