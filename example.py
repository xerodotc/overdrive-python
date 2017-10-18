from overdrive import Overdrive

def locationChangeCallback(addr, location, piece, speed, clockwise):
    # Print out addr, piece ID, location ID of the vehicle
    print("Location from " + addr + " : " + "Piece=" + str(piece) + " Location=" + str(location) + " Clockwise=" + str(clockwise))


car = Overdrive("xx:xx:xx:xx:xx:xx")
car.setLocationChangeCallback(locationChangeCallback) # Set location change callback to function above
car.changeSpeed(500, 1000) # Set car speed
car.changeLaneRight(1000, 1000) # Switch to next right lane
input() # Hold the program so it won't end abruptly
