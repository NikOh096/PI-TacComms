from pathlib import Path
import json
import subprocess
import time

for service in ['mumble-server.service','halow-console.service']:
    subprocess.run(['systemctl','is-enabled',service],check=True)
subprocess.run(['systemctl','restart','halow-console.service'],check=True)
subprocess.run(['systemctl','is-active','mumble-server.service'],check=True)
subprocess.run(['vcgencmd','get_throttled'],check=True)
report = {'mumble_installed':True,'mumble_autostart_verified_by_reboot':True,
          'pc_tls_login_and_udp_test_passed':True,'halow_phone_audio_tested':False,
          'pisugar_model':'S Plus','pisugar_auto_switch':'on (user confirmed)',
          'battery_percentage_supported':False,'actual_charging_state_supported':False,
          'gpio3_external_power_indicator_added':True,'backlight_sleep_working':False,
          'display_full_power_cycle_needed':True,'time':time.time()}
Path('/boot/firmware/halow-setup/repair-result.json').write_text(json.dumps(report,indent=2)+'\n')
subprocess.run(['sync'],check=True)
print('Saved repair results. Requesting clean power-off for the display reset.',flush=True)
subprocess.run(['systemctl','poweroff'],check=True)
