import subprocess,time
expected=1790662139.2922406
difference=expected-time.time()
print('Clock correction seconds:',round(difference,1))
if abs(difference)>30:
 subprocess.run(['date','--set','@'+str(expected)],check=True)
 subprocess.run(['fake-hwclock','save'],check=True)
