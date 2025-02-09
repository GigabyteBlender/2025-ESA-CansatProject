import sys
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
from PyQt5.QtWidgets import QPushButton
from graphs.graph_acceleration import graph_acceleration
from graphs.graph_altitude import graph_altitude
from graphs.graph_gyro import graph_gyro
from graphs.graph_pressure import graph_pressure
from graphs.graph_temperature import graph_temperature
from graphs.graph_time import graph_time
from graphs.graph_ppm import graph_ppm
from graphs.graph_humidity import graph_humidity
from dataBase import data_base
from communication import Communication

pg.setConfigOption('background', (33, 33, 33))
pg.setConfigOption('foreground', (197, 198, 199))
# Interface variables
app = QtWidgets.QApplication(sys.argv)
view = pg.GraphicsView()
Layout = pg.GraphicsLayout()
view.setCentralItem(Layout)
view.show()
view.setWindowTitle('Flight monitoring')
view.resize(1200, 700)

# declare object for serial Communication
ser = Communication()
# declare object for storage in CSV
data_base = data_base()
# Fonts for text items
font = QtGui.QFont()
font.setPixelSize(90)

# buttons style
style = "background-color:rgb(29, 185, 84);color:rgb(0,0,0);font-size:14px;"

# Declare graphs
# Button 1
proxy = QtWidgets.QGraphicsProxyWidget()
save_button = QtWidgets.QPushButton('Start storage')
save_button.setStyleSheet(style)
save_button.clicked.connect(data_base.start)
proxy.setWidget(save_button)

# Button 2
proxy2 = QtWidgets.QGraphicsProxyWidget()
end_save_button = QtWidgets.QPushButton('Stop storage')
end_save_button.setStyleSheet(style)
end_save_button.clicked.connect(data_base.stop)
proxy2.setWidget(end_save_button)

# Time graph
time = graph_time(font=font)
# Altitude graph
altitude = graph_altitude()
# Acceleration graph
acceleration = graph_acceleration()
# Gyro graph
gyro = graph_gyro()
# Pressure Graph
pressure = graph_pressure()
# Temperature graph
temperature = graph_temperature()
# Air quality graph
ppm = graph_ppm()
# Humidity graph
humidity = graph_humidity()


## Setting the graphs in the layout 
# Title at top
text = """
Cansat Monitoring interface
"""
Layout.addLabel(text, col=1, colspan=21)
Layout.nextRow()

# Put vertical label on left side
Layout.addLabel('ITS NOT ROCKET SCIENCE',
                angle=-90, rowspan=3)
                
Layout.nextRow()

lb = Layout.addLayout(colspan=21)
lb.addItem(proxy)
lb.nextCol()
lb.addItem(proxy2)

Layout.nextRow()

l1 = Layout.addLayout(colspan=20, rowspan=2)
l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))

# Altitude, speed
l11.addItem(altitude)
l1.nextRow()

# Acceleration, gyro, pressure, temperature
l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))
l12.addItem(acceleration)
l12.addItem(gyro)
l12.addItem(pressure)
l12.addItem(temperature)

# Time, battery and free fall graphs
l2 = Layout.addLayout(border=(83, 83, 83))

l2.addItem(time)
l2.nextRow()
l2.addItem(humidity)
l11.addItem(ppm)

# you have to put the position of the CSV stored in the value_chain list
# that represent the date you want to visualize
def update():
    try:
        value_chain = []
        value_chain = ser.getData()

        if value_chain[0] != '': 
            altitude.update(float(value_chain[4]))
            time.update(float(value_chain[0]))
            acceleration.update(float(value_chain[9]),float(value_chain[10]),float(value_chain[11]))
            gyro.update(float(value_chain[6]),float(value_chain[7]),float(value_chain[8]))
            pressure.update(float(value_chain[3]))
            temperature.update(float(value_chain[2]))
            ppm.update(float(value_chain[5]))
            humidity.update(float(value_chain[1]))

        data_base.guardar(value_chain)
    except IndexError as e:
        print('starting, please wait a moment: ', e)
    except ValueError:
        pass

if(ser.isOpen()) or (ser.dummyMode()):
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(500)
else:
    print("something is wrong with the update call")
# Start Qt event loop unless running in interactive mode.

if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
