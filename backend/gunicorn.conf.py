bind = "0.0.0.0:8000"
workers = 3
timeout = 120

# Disable control socket (fixes error)
control_socket = None
control_socket_disable = True

accesslog = "-"
errorlog = "-"
loglevel = "info"
