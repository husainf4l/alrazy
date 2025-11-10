module.exports = {
  apps: [{
    name: 'razzv4-backend',
    script: '.venv/bin/python',
    args: '-m uvicorn main:app --host 0.0.0.0 --port 8003',
    cwd: '/home/husain/alrazy/razzv4/RAZZv4-backend',
    instances: 1,
    exec_mode: 'fork',
    interpreter: 'none',
    autorestart: true,
    watch: false,
    max_memory_restart: '2G',
    env: {
      PYTHONUNBUFFERED: '1'
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }]
}
