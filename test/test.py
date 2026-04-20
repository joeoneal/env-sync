from halo import Halo
import time

# Replace 'earth' with any name from the list above
spinner = Halo(text='Testing spinner...', spinner='flip', color='green')
spinner.start()
time.sleep(3)
spinner.stop()

print('done')