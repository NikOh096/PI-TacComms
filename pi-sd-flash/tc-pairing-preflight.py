import socket,subprocess
assert subprocess.check_output(['hostname'],text=True).strip()=='halow-pi'
assert subprocess.check_output(['systemctl','is-active','mumble-server.service'],text=True).strip()=='active'
with socket.create_connection(('10.42.0.1',80),timeout=4):pass
print('Pi and gateway verification path ready.')
